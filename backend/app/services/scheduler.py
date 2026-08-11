"""
TICKR — Scheduler (no-op)
All data ingestion is now manually triggered via the API:
  - One-time bulk historical download:  POST /api/kite/bulk-download
  - Daily EOD via Bhav Copy upload:     POST /api/bhav/upload
  - Gap fill via Kite Connect:          POST /api/bhav/fill-gaps

No background cron jobs are registered.
"""


def start_scheduler():
    """No-op — data ingestion is fully manual."""
    print("[Scheduler] Manual mode — no background jobs registered.")


def stop_scheduler():
    """No-op."""
    pass
