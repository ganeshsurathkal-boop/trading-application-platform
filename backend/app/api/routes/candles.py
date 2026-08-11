"""TICKR — Candles API routes"""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import pandas as pd
from app.database import get_db
from app.models.candle import Candle
from app.models.user import User
from app.auth.jwt import get_current_user
from app.services.kite_service import kite_service
from app.indicators.registry import get_indicator, list_indicators
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["candles"])

DURATION_MAP = {
    "1M": 30, "3M": 90, "6M": 180, "1Y": 365, "2Y": 730, "5Y": 1825,
}


def _aggregate_weekly(candles: list[dict]) -> list[dict]:
    df = pd.DataFrame(candles)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").resample("W").agg({
        "open": "first", "high": "max", "low": "min", "close": "last",
        "volume": "sum", "symbol": "first", "exchange": "first",
    }).dropna().reset_index()
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df.to_dict("records")


def _aggregate_monthly(candles: list[dict]) -> list[dict]:
    df = pd.DataFrame(candles)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").resample("ME").agg({
        "open": "first", "high": "max", "low": "min", "close": "last",
        "volume": "sum", "symbol": "first", "exchange": "first",
    }).dropna().reset_index()
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df.to_dict("records")


@router.get("/candles/{symbol}")
def get_candles(
    symbol: str,
    duration: str = Query("6M", description="1M | 3M | 6M | 1Y | 2Y | 5Y"),
    interval: str = Query("1D", description="1D | 1W | 1M"),
    exchange: str = Query("NSE"),
    from_date: str = Query(None, description="ISO date override e.g. 2023-01-01"),
    to_date: str = Query(None, description="ISO date override e.g. 2024-01-01"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if from_date and to_date:
        from_date = date.fromisoformat(from_date)
        to_date = date.fromisoformat(to_date)
    else:
        days = DURATION_MAP.get(duration, 180)
        to_date = date.today()
        from_date = to_date - timedelta(days=days)

    # Try DB first
    rows = (
        db.query(Candle)
        .filter(
            Candle.symbol == symbol,
            Candle.exchange == exchange,
            Candle.date >= from_date,
            Candle.date <= to_date,
        )
        .order_by(Candle.date)
        .all()
    )

    if rows:
        # Check if DB covers the full requested range
        oldest_date = rows[0].date
        if oldest_date > from_date:
            # DB is missing earlier history — fetch only the missing range from Kite
            missing = kite_service.fetch_historical_data(
                symbol, from_date, oldest_date - timedelta(days=1), exchange
            )
            for c in missing:
                existing = db.query(Candle).filter_by(symbol=symbol, exchange=exchange, date=c["date"]).first()
                if not existing:
                    db.add(Candle(**{k: v for k, v in c.items() if k != "date"},
                                  date=date.fromisoformat(c["date"])))
            db.commit()
            rows = (
                db.query(Candle)
                .filter(
                    Candle.symbol == symbol,
                    Candle.exchange == exchange,
                    Candle.date >= from_date,
                    Candle.date <= to_date,
                )
                .order_by(Candle.date)
                .all()
            )
        candles = [r.to_dict() for r in rows]
    else:
        # DB empty for this symbol/range — fetch from Kite and store
        candles = kite_service.fetch_historical_data(symbol, from_date, to_date, exchange)
        for c in candles:
            existing = db.query(Candle).filter_by(symbol=symbol, exchange=exchange, date=c["date"]).first()
            if not existing:
                db.add(Candle(**{k: v for k, v in c.items() if k != "date"},
                              date=date.fromisoformat(c["date"])))
        db.commit()

    # Aggregate to weekly / monthly if requested
    if interval == "1W":
        candles = _aggregate_weekly(candles)
    elif interval == "1M":
        candles = _aggregate_monthly(candles)

    return {"symbol": symbol, "exchange": exchange, "interval": interval, "candles": candles}


@router.get("/indicators")
def get_indicators(current_user: User = Depends(get_current_user)):
    return {"indicators": list_indicators()}


class ComputeRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"
    duration: str = "6M"
    indicator: str
    params: dict = {}


@router.post("/indicators/compute")
def compute_indicator(req: ComputeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ind = get_indicator(req.indicator)
    if not ind:
        raise HTTPException(status_code=404, detail=f"Indicator '{req.indicator}' not found")

    days = DURATION_MAP.get(req.duration, 180)
    from_date = date.today() - timedelta(days=days)
    rows = db.query(Candle).filter(
        Candle.symbol == req.symbol, Candle.exchange == req.exchange, Candle.date >= from_date
    ).order_by(Candle.date).all()

    if not rows:
        candles = kite_service.fetch_historical_data(req.symbol, from_date, date.today(), req.exchange)
    else:
        candles = [r.to_dict() for r in rows]

    df = pd.DataFrame(candles)
    result_df = ind.compute(df, **req.params)
    indicator_cols = [c for c in result_df.columns if c not in ["symbol", "exchange", "date", "open", "high", "low", "close", "volume"]]
    result = result_df[["date"] + indicator_cols].to_dict("records")
    return {
        "indicator": req.indicator,
        "overlay": ind.overlay,
        "label": ind.get_label(**req.params),
        "data": result,
    }
