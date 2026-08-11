"""
TICKR — Kite Connect API routes

Endpoints:
  GET  /api/kite/status              — connection status
  GET  /api/kite/login-url           — Kite OAuth login URL
  POST /api/kite/session             — exchange request_token for access_token
  POST /api/kite/bulk-download       — start one-time historical download (all NSE symbols)
  GET  /api/kite/bulk-download/status — progress of ongoing bulk download
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.auth.jwt import get_current_user
from app.models.user import User
from app.database import get_db
from app.config import settings
from app.services.kite_service import kite_service

router = APIRouter(prefix="/api/kite", tags=["kite"])


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/status")
def get_kite_status(current_user: User = Depends(get_current_user)):
    """Returns current Kite Connect connection state."""
    has_key = bool(settings.KITE_API_KEY)
    has_token = bool(settings.KITE_ACCESS_TOKEN)
    connected = has_key and has_token and kite_service.is_connected()
    return {
        "connected": connected,
        "has_api_key": has_key,
        "has_access_token": has_token,
        "mode": "mock" if settings.USE_MOCK_DATA else ("live" if connected else "disconnected"),
        "bulk_download": kite_service.bulk_progress.to_dict(),
    }


# ── OAuth ─────────────────────────────────────────────────────────────────────

@router.get("/login-url")
def get_login_url(current_user: User = Depends(get_current_user)):
    """
    Returns the Kite OAuth login URL.
    The frontend should redirect the user to this URL.
    After login, Kite redirects back with ?request_token=... in the URL.
    """
    if not settings.KITE_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="KITE_API_KEY is not configured. Add it to your .env file."
        )
    url = kite_service.get_login_url()
    if not url:
        raise HTTPException(status_code=500, detail="Failed to generate Kite login URL.")
    return {"login_url": url}


class SessionRequest(BaseModel):
    request_token: str


@router.post("/session")
def create_session(req: SessionRequest, current_user: User = Depends(get_current_user)):
    """
    Exchange a Kite request_token for an access_token.
    The access_token is stored in memory and persisted to .env for this trading day.
    """
    if not settings.KITE_API_KEY or not settings.KITE_API_SECRET:
        raise HTTPException(
            status_code=400,
            detail="KITE_API_KEY and KITE_API_SECRET must be set in .env before creating a session."
        )
    access_token = kite_service.generate_session(req.request_token)
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Failed to generate Kite session. The request_token may be expired or invalid."
        )
    return {
        "ok": True,
        "message": "Kite Connect session established successfully.",
        "access_token_hint": access_token[:8] + "…",  # Never expose full token in response
    }


# ── Bulk Historical Download ───────────────────────────────────────────────────

@router.post("/bulk-download")
def start_bulk_download(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Triggers a one-time bulk download of OHLCV history for ALL NSE equity symbols.
    Downloads {KITE_BULK_DOWNLOAD_YEARS} years of daily data.
    This runs in a background thread — poll /api/kite/bulk-download/status for progress.
    """
    if not kite_service.is_connected():
        raise HTTPException(
            status_code=400,
            detail="Kite Connect is not connected. Complete the OAuth login first."
        )
    if kite_service.bulk_progress.running:
        raise HTTPException(
            status_code=409,
            detail="A bulk download is already in progress."
        )
    started = kite_service.bulk_download(db, years=settings.KITE_BULK_DOWNLOAD_YEARS)
    if not started:
        raise HTTPException(status_code=500, detail="Failed to start bulk download.")
    return {
        "ok": True,
        "message": f"Bulk download started. Downloading {settings.KITE_BULK_DOWNLOAD_YEARS} years of history for all NSE equity symbols.",
        "poll_url": "/api/kite/bulk-download/status",
    }


@router.get("/bulk-download/status")
def get_bulk_download_status(current_user: User = Depends(get_current_user)):
    """Returns progress of the ongoing (or last completed) bulk download."""
    return kite_service.bulk_progress.to_dict()
