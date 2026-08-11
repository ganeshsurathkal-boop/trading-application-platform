"""TICKR — Scanner API routes"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from app.auth.jwt import get_current_user
from app.models.user import User
from app.scanners.registry import list_scanners, list_by_category, get_scanner
from app.scanners.universes import get_universe, list_universes
from app.models.watchlist import Watchlist, WatchlistStock
from app.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/scanners", tags=["scanners"])


class RunScanRequest(BaseModel):
    universe: str = "NIFTY 50"
    exchange: str = "NSE"
    params: dict = {}


class SaveScanAsWatchlistReq(BaseModel):
    name: str
    symbols: List[str]
    exchange: str = "NSE"


@router.get("")
def get_scanners(current_user: User = Depends(get_current_user)):
    return {"scanners": list_by_category(), "universes": list_universes()}


@router.post("/{scanner_name}/run")
def run_scanner(
    scanner_name: str,
    req: RunScanRequest,
    current_user: User = Depends(get_current_user),
):
    scanner = get_scanner(scanner_name)
    if not scanner:
        raise HTTPException(status_code=404, detail=f"Scanner '{scanner_name}' not found")

    symbols = get_universe(req.universe)
    results = scanner.run(symbols, exchange=req.exchange, **req.params)
    return {
        "scanner": scanner_name,
        "universe": req.universe,
        "run_at": date.today().isoformat(),
        "match_count": len(results),
        "results": results,
    }


@router.post("/save-as-watchlist", status_code=201)
def save_scan_as_watchlist(
    req: SaveScanAsWatchlistReq,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wl = Watchlist(name=req.name, user_id=current_user.id)
    db.add(wl)
    db.flush()
    for sym in req.symbols:
        db.add(WatchlistStock(watchlist_id=wl.id, symbol=sym, exchange=req.exchange))
    db.commit()
    return {"id": wl.id, "name": wl.name, "stock_count": len(req.symbols)}
