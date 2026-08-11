"""
TICKR — Application Configuration
Reads all settings from .env file via pydantic-settings pattern.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_SECRET_KEY: str = os.getenv("APP_SECRET_KEY", "dev-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./tickr.db")

    # ── Zerodha Kite Connect ─────────────────────────────────────────────────
    # Obtain API key & secret from: https://developers.kite.trade/
    KITE_API_KEY: str = os.getenv("KITE_API_KEY", "")
    KITE_API_SECRET: str = os.getenv("KITE_API_SECRET", "")
    # Access token is obtained via Kite OAuth login — valid until next trading day.
    # The app writes this automatically after you log in; no manual entry needed.
    KITE_ACCESS_TOKEN: str = os.getenv("KITE_ACCESS_TOKEN", "")

    # How many years of history to download during the one-time bulk load
    KITE_BULK_DOWNLOAD_YEARS: int = int(os.getenv("KITE_BULK_DOWNLOAD_YEARS", "5"))

    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")

    # Use mock data only when no Kite credentials are configured
    USE_MOCK_DATA: bool = not bool(os.getenv("KITE_API_KEY", ""))


settings = Settings()
