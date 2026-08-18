"""
TICKR — FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db, SessionLocal
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services import plugin_manager
from app.api.routes import auth, candles, watchlist, scanner, profile, kite, bhav, admin, scan_combos

app = FastAPI(
    title="TICKR Trading API",
    description="Backend API for the TICKR trading terminal",
    version="2.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(candles.router)
app.include_router(watchlist.router)
app.include_router(scanner.router)
app.include_router(profile.router)
app.include_router(kite.router)
app.include_router(bhav.router)
app.include_router(admin.router)
app.include_router(scan_combos.router)


# ── Startup / Shutdown ────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    print("[TICKR] Initializing database...")
    init_db()
    mode = "MOCK DATA" if settings.USE_MOCK_DATA else "LIVE — KITE CONNECT"
    print(f"[TICKR] Mode: {mode}")
    start_scheduler()

    db = SessionLocal()
    try:
        plugin_manager.seed_default_plugins(db)
        plugin_manager.load_all_installed(db)
    finally:
        db.close()


@app.on_event("shutdown")
async def shutdown():
    stop_scheduler()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": "mock" if settings.USE_MOCK_DATA else "live",
        "version": "2.0.0",
        "data_sources": {
            "historical": "Kite Connect (one-time bulk download)",
            "eod_update": "NSE Bhav Copy (manual upload) → Kite Connect (gap fill)",
        },
    }
