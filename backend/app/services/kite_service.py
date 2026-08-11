"""
TICKR — Zerodha Kite Connect Service
Wraps the kiteconnect Python library for:
  - OAuth authentication (login URL + session exchange)
  - One-time bulk historical OHLCV download for all NSE equity symbols
  - On-demand / fallback single-symbol historical fetch
  - Gap-fill: fetch specific missing trading dates from Kite

Falls back to realistic mock data when KITE_API_KEY is not set.
"""
import os
import random
import threading
from datetime import date, timedelta, datetime
from typing import List, Dict, Any, Optional, Callable
from app.config import settings

# ── Mock data generator ────────────────────────────────────────────────────────

MOCK_SYMBOLS_BASE_PRICE = {
    "RELIANCE": 2940, "TCS": 4120, "HDFCBANK": 1680, "INFY": 1890,
    "WIPRO": 512, "ICICIBANK": 1240, "KOTAKBANK": 1780, "LT": 3450,
    "BAJFINANCE": 7200, "HINDUNILVR": 2680, "SBIN": 820, "AXISBANK": 1150,
    "MARUTI": 12400, "ASIANPAINT": 3100, "TITAN": 3680, "NESTLEIND": 2280,
    "ULTRACEMCO": 10800, "TECHM": 1620, "POWERGRID": 340, "NTPC": 390,
}


def generate_mock_candles(symbol: str, from_date: date, to_date: date) -> List[Dict[str, Any]]:
    """Generate realistic-looking OHLCV data for testing."""
    base_price = MOCK_SYMBOLS_BASE_PRICE.get(symbol.upper().replace(".NS", ""), 1000)
    candles = []
    current = from_date
    price = base_price

    random.seed(hash(symbol))  # Deterministic per symbol

    while current <= to_date:
        if current.weekday() < 5:  # Skip weekends
            daily_return = random.gauss(0.0003, 0.015)
            price = price * (1 + daily_return)

            open_p = round(price * random.uniform(0.995, 1.005), 2)
            close_p = round(price, 2)
            high_p = round(max(open_p, close_p) * random.uniform(1.001, 1.02), 2)
            low_p = round(min(open_p, close_p) * random.uniform(0.98, 0.999), 2)
            volume = round(random.uniform(500000, 5000000))

            candles.append({
                "symbol": symbol,
                "exchange": "NSE",
                "date": current.isoformat(),
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": volume,
            })
        current += timedelta(days=1)

    return candles


# ── Kite Connect wrapper ───────────────────────────────────────────────────────

class BulkDownloadProgress:
    """Thread-safe progress tracker for the bulk historical download."""
    def __init__(self):
        self.running = False
        self.done = 0
        self.total = 0
        self.current_symbol = ""
        self.errors: List[str] = []

    @property
    def pct(self) -> int:
        return round((self.done / self.total) * 100) if self.total else 0

    def to_dict(self) -> dict:
        return {
            "running": self.running,
            "done": self.done,
            "total": self.total,
            "current_symbol": self.current_symbol,
            "pct": self.pct,
            "errors": self.errors[-10:],  # Last 10 errors only
        }


class KiteService:
    """
    Zerodha Kite Connect data service.

    Instrument tokens are resolved lazily and cached in memory so we only
    call kite.instruments("NSE") once per process lifetime.
    """

    def __init__(self):
        self._kite = None
        self._connected = False
        # instrument_token cache: "NSE:RELIANCE" -> 738561
        self._token_cache: Dict[str, int] = {}
        # All NSE instruments cache (list of dicts)
        self._instruments_cache: Optional[List[Dict]] = None
        # Bulk download progress (singleton per process)
        self.bulk_progress = BulkDownloadProgress()

    # ── Connection ────────────────────────────────────────────────────────────

    def _connect(self) -> bool:
        """Initialise KiteConnect with the stored access token."""
        if self._connected and self._kite is not None:
            return True
        if not settings.KITE_API_KEY or not settings.KITE_ACCESS_TOKEN:
            return False
        try:
            from kiteconnect import KiteConnect  # type: ignore
            self._kite = KiteConnect(api_key=settings.KITE_API_KEY)
            self._kite.set_access_token(settings.KITE_ACCESS_TOKEN)
            self._connected = True
            print("[KiteService] Connected to Zerodha Kite Connect API")
            return True
        except Exception as e:
            print(f"[KiteService] Connection failed: {e}")
            self._connected = False
            return False

    def get_login_url(self) -> str:
        """Return the Kite OAuth login URL. User must navigate to this URL to authenticate."""
        try:
            from kiteconnect import KiteConnect  # type: ignore
            kite = KiteConnect(api_key=settings.KITE_API_KEY)
            return kite.login_url()
        except Exception as e:
            print(f"[KiteService] get_login_url failed: {e}")
            return ""

    def generate_session(self, request_token: str) -> Optional[str]:
        """
        Exchange a request_token for an access_token.
        Persists the token to .env on disk so restarts don't require re-login.
        Returns the access_token on success, None on failure.
        """
        try:
            from kiteconnect import KiteConnect  # type: ignore
            kite = KiteConnect(api_key=settings.KITE_API_KEY)
            data = kite.generate_session(request_token, api_secret=settings.KITE_API_SECRET)
            access_token: str = data["access_token"]
            # Persist in memory
            settings.KITE_ACCESS_TOKEN = access_token
            self._connected = False  # Force reconnect with new token
            self._connect()
            # Persist to .env on disk
            self._write_token_to_env(access_token)
            print("[KiteService] Session generated. Access token stored.")
            return access_token
        except Exception as e:
            print(f"[KiteService] generate_session failed: {e}")
            return None

    def _write_token_to_env(self, token: str):
        """Update KITE_ACCESS_TOKEN in the .env file on disk."""
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        env_path = os.path.normpath(env_path)
        try:
            if os.path.exists(env_path):
                with open(env_path, "r") as f:
                    lines = f.readlines()
                updated = []
                found = False
                for line in lines:
                    if line.startswith("KITE_ACCESS_TOKEN="):
                        updated.append(f"KITE_ACCESS_TOKEN={token}\n")
                        found = True
                    else:
                        updated.append(line)
                if not found:
                    updated.append(f"KITE_ACCESS_TOKEN={token}\n")
                with open(env_path, "w") as f:
                    f.writelines(updated)
                print("[KiteService] Access token written to .env")
        except Exception as e:
            print(f"[KiteService] Could not write token to .env: {e}")

    def invalidate_session(self):
        """Clear the in-memory session (call when token expires)."""
        self._kite = None
        self._connected = False

    def is_connected(self) -> bool:
        return self._connect()

    # ── Instrument / symbol resolution ───────────────────────────────────────

    def get_all_nse_symbols(self) -> List[str]:
        """
        Return list of all NSE equity trading symbols.
        Result is cached for the lifetime of the process.
        """
        if not self._connect():
            return []
        try:
            instruments = self._kite.instruments("NSE")
            self._instruments_cache = instruments
            symbols = [
                inst["tradingsymbol"]
                for inst in instruments
                if inst.get("segment") == "NSE-EQ" and inst.get("instrument_type") == "EQ"
            ]
            print(f"[KiteService] Found {len(symbols)} NSE equity symbols")
            return symbols
        except Exception as e:
            print(f"[KiteService] get_all_nse_symbols failed: {e}")
            return []

    def _get_instrument_token(self, symbol: str, exchange: str = "NSE") -> Optional[int]:
        """
        Resolve a trading symbol to its Kite instrument token.
        Results are cached for the lifetime of the process.
        """
        cache_key = f"{exchange}:{symbol}"
        if cache_key in self._token_cache:
            return self._token_cache[cache_key]

        try:
            # Use cached instruments list if available, else fetch
            if self._instruments_cache is None:
                self._instruments_cache = self._kite.instruments(exchange)

            for inst in self._instruments_cache:
                if (inst.get("tradingsymbol") == symbol
                        and inst.get("segment") == f"{exchange}-EQ"):
                    token = inst["instrument_token"]
                    self._token_cache[cache_key] = token
                    return token

            print(f"[KiteService] Instrument token not found for {exchange}:{symbol}")
            return None
        except Exception as e:
            print(f"[KiteService] instruments() failed: {e}")
            return None

    # ── Historical data — single symbol ──────────────────────────────────────

    def fetch_historical_data(
        self,
        symbol: str,
        from_date: date,
        to_date: date,
        exchange: str = "NSE",
    ) -> List[Dict[str, Any]]:
        """
        Fetch daily OHLCV candles from Kite Connect for a single symbol.
        Falls back to mock data when credentials are absent or an error occurs.
        """
        if settings.USE_MOCK_DATA:
            print(f"[KiteService] MOCK mode — generating data for {symbol}")
            return generate_mock_candles(symbol, from_date, to_date)

        if not self._connect():
            print(f"[KiteService] Not connected — falling back to mock for {symbol}")
            return generate_mock_candles(symbol, from_date, to_date)

        token = self._get_instrument_token(symbol, exchange)
        if token is None:
            print(f"[KiteService] No token — falling back to mock for {symbol}")
            return generate_mock_candles(symbol, from_date, to_date)

        try:
            records = self._kite.historical_data(
                instrument_token=token,
                from_date=datetime.combine(from_date, datetime.min.time()),
                to_date=datetime.combine(to_date, datetime.min.time()),
                interval="day",
            )
            candles = [
                {
                    "symbol": symbol,
                    "exchange": exchange,
                    "date": r["date"].strftime("%Y-%m-%d") if hasattr(r["date"], "strftime") else str(r["date"])[:10],
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "volume": float(r.get("volume", 0)),
                }
                for r in records
            ]
            print(f"[KiteService] Fetched {len(candles)} candles for {symbol}")
            return candles
        except Exception as e:
            err = str(e)
            if "TokenException" in err or "Invalid" in err:
                print(f"[KiteService] Token expired, invalidating session.")
                self.invalidate_session()
            else:
                print(f"[KiteService] API error for {symbol}: {e}")
            return generate_mock_candles(symbol, from_date, to_date)

    # ── Bulk historical download — all NSE symbols ────────────────────────────

    def bulk_download(self, db, years: Optional[int] = None) -> bool:
        """
        One-time bulk download of OHLCV history for ALL NSE equity symbols.
        Runs in a background thread. Monitor progress via self.bulk_progress.
        Returns True if the background thread was started successfully.
        """
        if self.bulk_progress.running:
            print("[KiteService] Bulk download already in progress")
            return False

        if not self._connect():
            print("[KiteService] Cannot start bulk download — not connected")
            return False

        years = years or settings.KITE_BULK_DOWNLOAD_YEARS
        thread = threading.Thread(
            target=self._bulk_download_worker,
            args=(db, years),
            daemon=True,
        )
        thread.start()
        return True

    def _bulk_download_worker(self, db, years: int):
        """Worker function executed in a background thread for bulk download."""
        from app.models.candle import Candle

        progress = self.bulk_progress
        progress.running = True
        progress.done = 0
        progress.errors = []

        try:
            symbols = self.get_all_nse_symbols()
            if not symbols:
                print("[KiteService] No symbols found — aborting bulk download")
                return

            progress.total = len(symbols)
            to_date = date.today()
            from_date = date(to_date.year - years, to_date.month, to_date.day)
            print(f"[KiteService] Bulk download: {len(symbols)} symbols, {from_date} → {to_date}")

            BATCH_COMMIT = 50  # Commit every N symbols to avoid huge transactions

            for i, symbol in enumerate(symbols):
                progress.current_symbol = symbol
                try:
                    candles = self.fetch_historical_data(symbol, from_date, to_date, "NSE")
                    for c in candles:
                        candle_date = date.fromisoformat(c["date"]) if isinstance(c["date"], str) else c["date"]
                        existing = db.query(Candle).filter_by(
                            symbol=symbol, exchange="NSE", date=candle_date
                        ).first()
                        if existing:
                            existing.open = c["open"]
                            existing.high = c["high"]
                            existing.low = c["low"]
                            existing.close = c["close"]
                            existing.volume = c["volume"]
                        else:
                            db.add(Candle(
                                symbol=symbol, exchange="NSE", date=candle_date,
                                open=c["open"], high=c["high"], low=c["low"],
                                close=c["close"], volume=c["volume"],
                            ))

                    if (i + 1) % BATCH_COMMIT == 0:
                        db.commit()

                except Exception as e:
                    err_msg = f"{symbol}: {e}"
                    print(f"[KiteService] Bulk download error — {err_msg}")
                    progress.errors.append(err_msg)

                progress.done = i + 1

            db.commit()
            print(f"[KiteService] Bulk download complete. {progress.done} symbols processed.")

        except Exception as e:
            print(f"[KiteService] Bulk download worker crashed: {e}")
            progress.errors.append(str(e))
        finally:
            progress.running = False
            progress.current_symbol = ""

    # ── Gap fill — specific missing dates from Kite ───────────────────────────

    def fill_gaps(self, db, symbols: List[str], missing_dates: List[date], exchange: str = "NSE") -> Dict:
        """
        Fetch EOD data from Kite for specific missing trading dates and upsert into DB.
        Used when Bhav Copy files are unavailable for some days.
        Returns summary dict.
        """
        from app.models.candle import Candle

        filled = 0
        skipped = 0
        errors = []

        for missing_date in missing_dates:
            print(f"[KiteService] Gap fill: fetching {missing_date} for {len(symbols)} symbols")
            for symbol in symbols:
                try:
                    candles = self.fetch_historical_data(symbol, missing_date, missing_date, exchange)
                    for c in candles:
                        candle_date = date.fromisoformat(c["date"]) if isinstance(c["date"], str) else c["date"]
                        existing = db.query(Candle).filter_by(
                            symbol=symbol, exchange=exchange, date=candle_date
                        ).first()
                        if existing:
                            existing.open = c["open"]
                            existing.high = c["high"]
                            existing.low = c["low"]
                            existing.close = c["close"]
                            existing.volume = c["volume"]
                        else:
                            db.add(Candle(
                                symbol=symbol, exchange=exchange, date=candle_date,
                                open=c["open"], high=c["high"], low=c["low"],
                                close=c["close"], volume=c["volume"],
                            ))
                    filled += 1
                except Exception as e:
                    err = f"{missing_date}/{symbol}: {e}"
                    errors.append(err)
                    skipped += 1

            db.commit()

        return {
            "days_processed": len(missing_dates),
            "symbols_filled": filled,
            "symbols_skipped": skipped,
            "errors": errors[:20],
        }


# Singleton used throughout the app
kite_service = KiteService()
