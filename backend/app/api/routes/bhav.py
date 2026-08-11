"""
TICKR — Bhav Copy API routes

Endpoints:
  POST /api/bhav/upload      — upload NSE Bhav Copy CSV/ZIP file
  GET  /api/bhav/gaps        — list of missing trading days in the last 30 days
  POST /api/bhav/fill-gaps   — fill all detected gaps using Kite Connect
  GET  /api/bhav/history     — recent upload dates with symbol counts
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from app.auth.jwt import get_current_user
from app.models.user import User
from app.database import get_db
from app.services.bhav_copy_service import bhav_copy_service
from app.services.kite_service import kite_service

router = APIRouter(prefix="/api/bhav", tags=["bhav"])

ALLOWED_EXTENSIONS = {".csv", ".zip"}
MAX_FILE_SIZE_MB = 50


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_bhav_copy(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Accept a manually uploaded NSE Bhav Copy file (CSV or ZIP).
    Parses EQ-series records and upserts OHLCV data into the DB.
    After ingestion, returns a list of any detected missing trading days.
    """
    # Validate extension
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Upload a .csv or .zip file."
        )

    # Read file bytes
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum is {MAX_FILE_SIZE_MB} MB.")

    # Parse & ingest
    result = bhav_copy_service.parse_and_ingest(file_bytes, filename, db)
    if not result.success:
        raise HTTPException(status_code=422, detail=result.message)

    # Auto-detect gaps after ingestion
    missing_days = bhav_copy_service.detect_missing_days(db)

    return {
        **result.to_dict(),
        "gaps_detected": len(missing_days),
        "gap_dates": [d.isoformat() for d in missing_days],
    }


# ── Gap detection ─────────────────────────────────────────────────────────────

@router.get("/gaps")
def get_gaps(
    lookback_days: int = Query(30, ge=1, le=365, description="How many days back to check for gaps"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns a list of trading days with no data in the DB within the last N days.
    Use this to see which dates need to be filled (via Bhav Copy upload or Kite fallback).
    """
    missing_days = bhav_copy_service.detect_missing_days(db, lookback_days=lookback_days)
    return {
        "lookback_days": lookback_days,
        "missing_count": len(missing_days),
        "missing_dates": [d.isoformat() for d in missing_days],
    }


# ── Gap fill via Kite Connect ─────────────────────────────────────────────────

@router.post("/fill-gaps")
def fill_gaps(
    lookback_days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Detects missing trading days in the DB and fills them using Kite Connect.
    For each missing day, fetches EOD data for all distinct symbols already in the DB.
    Falls back gracefully if Kite is not connected.
    """
    if not kite_service.is_connected():
        raise HTTPException(
            status_code=400,
            detail=(
                "Kite Connect is not connected. "
                "Complete the OAuth login at Profile → Data Sources first, "
                "then retry."
            )
        )

    missing_days = bhav_copy_service.detect_missing_days(db, lookback_days=lookback_days)
    if not missing_days:
        return {"ok": True, "message": "No gaps detected. DB is up to date.", "days_filled": 0}

    # Collect all distinct symbols currently in DB (filled by bhav copy or bulk download)
    from app.models.candle import Candle
    symbol_rows = db.query(Candle.symbol).distinct().all()
    symbols = [r.symbol for r in symbol_rows]

    if not symbols:
        return {
            "ok": False,
            "message": "No symbols found in DB yet. Run the bulk historical download first.",
            "days_filled": 0,
        }

    print(f"[BhavRoute] Filling {len(missing_days)} missing days for {len(symbols)} symbols via Kite Connect")
    summary = kite_service.fill_gaps(db, symbols, missing_days)

    return {
        "ok": True,
        "message": f"Gap fill complete. {summary['days_processed']} days processed for {len(symbols)} symbols.",
        **summary,
        "gap_dates_filled": [d.isoformat() for d in missing_days],
    }


# ── Upload history ─────────────────────────────────────────────────────────────

@router.get("/history")
def get_bhav_history(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns the most recently ingested trading dates with symbol counts."""
    history = bhav_copy_service.get_last_uploaded_dates(db, limit=limit)
    return {"history": history, "count": len(history)}
