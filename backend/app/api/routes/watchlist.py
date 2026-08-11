"""TICKR — Watchlist API routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.models.watchlist import Watchlist, WatchlistStock
from app.auth.jwt import get_current_user

router = APIRouter(prefix="/api/watchlists", tags=["watchlists"])


class CreateWatchlistReq(BaseModel):
    name: str


class AddStockReq(BaseModel):
    symbol: str
    exchange: str = "NSE"


@router.get("")
def list_watchlists(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wls = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).all()
    return [{"id": w.id, "name": w.name, "stocks": [
        {"symbol": s.symbol, "exchange": s.exchange} for s in w.stocks
    ]} for w in wls]


@router.post("", status_code=201)
def create_watchlist(req: CreateWatchlistReq, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wl = Watchlist(name=req.name, user_id=current_user.id)
    db.add(wl)
    db.commit()
    db.refresh(wl)
    return {"id": wl.id, "name": wl.name, "stocks": []}


@router.delete("/{wl_id}")
def delete_watchlist(wl_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wl = db.query(Watchlist).filter(Watchlist.id == wl_id, Watchlist.user_id == current_user.id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    db.delete(wl)
    db.commit()
    return {"ok": True}


@router.post("/{wl_id}/stocks", status_code=201)
def add_stock(wl_id: int, req: AddStockReq, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wl = db.query(Watchlist).filter(Watchlist.id == wl_id, Watchlist.user_id == current_user.id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    existing = db.query(WatchlistStock).filter_by(watchlist_id=wl_id, symbol=req.symbol).first()
    if existing:
        raise HTTPException(status_code=409, detail="Stock already in watchlist")
    stock = WatchlistStock(watchlist_id=wl_id, symbol=req.symbol, exchange=req.exchange)
    db.add(stock)
    db.commit()
    return {"ok": True, "symbol": req.symbol}


@router.delete("/{wl_id}/stocks/{symbol}")
def remove_stock(wl_id: int, symbol: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stock = db.query(WatchlistStock).filter_by(watchlist_id=wl_id, symbol=symbol).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found in watchlist")
    db.delete(stock)
    db.commit()
    return {"ok": True}
