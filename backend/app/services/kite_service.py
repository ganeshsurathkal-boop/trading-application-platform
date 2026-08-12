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
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta, datetime
from typing import List, Dict, Any, Optional, Tuple
from app.config import settings

# Kite API rate limit: 3 requests/second across all connections.
# We use a token-bucket style lock to stay safely within that limit.
_RATE_LIMIT_LOCK = threading.Lock()
_RATE_LIMIT_INTERVAL = 0.38  # seconds between requests → ~2.6 req/s (safe margin)
_last_request_time: float = 0.0


def _rate_limited_sleep():
    """Block the calling thread until it is safe to make another Kite API call."""
    global _last_request_time
    with _RATE_LIMIT_LOCK:
        now = time.monotonic()
        wait = _RATE_LIMIT_INTERVAL - (now - _last_request_time)
        if wait > 0:
            time.sleep(wait)
        _last_request_time = time.monotonic()

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
        self.stop_requested = False
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
            "stop_requested": self.stop_requested,
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
        # Set once a request fails with an expired/invalid token, so we stop
        # pretending we're connected until a fresh access_token is issued.
        self._token_invalid = False
        self._invalid_token_value: Optional[str] = None
        # instrument_token cache: "NSE:RELIANCE" -> 738561
        self._token_cache: Dict[str, int] = {}
        # All NSE instruments cache (list of dicts)
        self._instruments_cache: Optional[List[Dict]] = None
        # Bulk download progress (singleton per process)
        self.bulk_progress = BulkDownloadProgress()

    # ── Connection ────────────────────────────────────────────────────────────

    def _connect(self) -> bool:
        """Initialise KiteConnect with the stored access token and verify it actually works."""
        if self._connected and self._kite is not None:
            return True
        if not settings.KITE_API_KEY or not settings.KITE_ACCESS_TOKEN:
            return False
        # We've already confirmed this exact token is dead (e.g. daily expiry) —
        # don't keep hitting Kite's API with it until a fresh login updates it.
        if self._token_invalid and self._invalid_token_value == settings.KITE_ACCESS_TOKEN:
            return False
        try:
            from kiteconnect import KiteConnect  # type: ignore
            kite = KiteConnect(api_key=settings.KITE_API_KEY)
            kite.set_access_token(settings.KITE_ACCESS_TOKEN)
            _rate_limited_sleep()  # this can run concurrently from bulk-download worker threads
            kite.profile()  # cheap authenticated call — confirms the token is actually live
            self._kite = kite
            self._connected = True
            self._token_invalid = False
            print("[KiteService] Connected to Zerodha Kite Connect API")
            return True
        except Exception as e:
            if self._is_token_error(e):
                print("[KiteService] Access token is expired or invalid — not connected.")
                self._token_invalid = True
                self._invalid_token_value = settings.KITE_ACCESS_TOKEN
            else:
                print(f"[KiteService] Connection failed: {e}")
            self._kite = None
            self._connected = False
            return False

    @staticmethod
    def _is_token_error(e: Exception) -> bool:
        """True if the exception represents an expired/invalid Kite access token."""
        try:
            from kiteconnect.exceptions import TokenException  # type: ignore
            if isinstance(e, TokenException):
                return True
        except Exception:
            pass
        msg = str(e).lower()
        return "access_token" in msg or "api_key" in msg or "token" in msg

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
            self._token_invalid = False  # New token — give it a fresh chance
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
        self._token_cache.clear()
        self._instruments_cache = None
        self._token_invalid = True
        self._invalid_token_value = settings.KITE_ACCESS_TOKEN

    def disconnect(self):
        """Fully disconnect: clear session and wipe the access token from .env."""
        self.invalidate_session()
        settings.KITE_ACCESS_TOKEN = ""
        self._write_token_to_env("")  # Clear token in .env on disk
        print("[KiteService] Disconnected from Zerodha Kite Connect.")

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
            # Strict filter for NSE mainboard equity stocks:
            #   segment="NSE"         → mainboard only (excludes NFO, etc.)
            #   instrument_type="EQ"  → equity only (excludes GB, NCD, MF, etc.)
            #   lot_size == 1         → standard equity lot (excludes some structured products)
            #   no digits in symbol   → excludes bonds (SGB202628), NCDs, rights (XYZ-RE), etc.
            symbols = [
                inst["tradingsymbol"]
                for inst in instruments
                if inst.get("segment") == "NSE"
                and inst.get("instrument_type") == "EQ"
                and inst.get("lot_size") == 1
                and not any(ch.isdigit() for ch in inst.get("tradingsymbol", ""))
            ]
            print(f"[KiteService] Found {len(symbols)} NSE mainboard equity symbols")
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
                        and inst.get("segment") == exchange
                        and inst.get("instrument_type") == "EQ"):
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
            _rate_limited_sleep()  # Respect Kite 3 req/s rate limit
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
            return candles
        except Exception as e:
            if self._is_token_error(e):
                print(f"[KiteService] Token expired, invalidating session.")
                self.invalidate_session()
            else:
                print(f"[KiteService] API error for {symbol}: {e}")
            return []

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
        """
        Concurrent bulk download using a thread pool.
        - Fetches data from Kite in parallel (up to MAX_WORKERS concurrent requests)
        - All threads share the global rate limiter (_rate_limited_sleep)
        - DB writes are serialised on the main worker thread to avoid SQLite conflicts
        """
        from app.models.candle import Candle
        from app.database import SessionLocal

        MAX_WORKERS = 5  # 5 threads × rate-limited → safe throughput near 3 req/s
        BATCH_COMMIT = 5  # commit every 5 symbols to keep SQLite write locks very short

        progress = self.bulk_progress
        progress.running = True
        progress.stop_requested = False
        progress.done = 0
        progress.errors = []

        try:
            symbols = self.get_all_nse_symbols()
            if not symbols:
                reason = (
                    "Kite access token is expired or invalid — reconnect and retry."
                    if self._token_invalid else
                    "No NSE symbols were returned by Kite — aborting bulk download."
                )
                progress.errors.append(reason)
                print(f"[KiteService] {reason}")
                return

            progress.total = len(symbols)
            to_date = date.today()
            from_date = date(to_date.year - years, to_date.month, to_date.day)
            print(f"[KiteService] Bulk download: {len(symbols)} symbols, "
                  f"{from_date} → {to_date}, workers={MAX_WORKERS}")

            # ── Resume support: skip symbols already fully downloaded ───────
            # Use a short-lived session to inspect existing data without holding locks.
            from sqlalchemy import func as sql_func
            threshold = from_date + timedelta(days=30)
            with SessionLocal() as inspect_db:
                min_date_rows = (
                    inspect_db.query(Candle.symbol, sql_func.min(Candle.date).label("min_date"))
                    .group_by(Candle.symbol)
                    .all()
                )
            already_done = {r.symbol for r in min_date_rows if r.min_date <= threshold}
            skipped_count = sum(1 for s in symbols if s in already_done)
            symbols = [s for s in symbols if s not in already_done]
            # Offset progress so the % correctly reflects remaining work
            progress.done = skipped_count
            if skipped_count:
                print(f"[KiteService] Resume: skipping {skipped_count} already-complete symbols, "
                      f"{len(symbols)} remaining.")
            else:
                print("[KiteService] Fresh download — no existing data found.")
            # ─────────────────────────────────────────────────────────────────

            def fetch_one(symbol: str) -> Tuple[str, List[Dict]]:
                """Fetch candles for a single symbol. Runs inside a worker thread."""
                candles = self.fetch_historical_data(symbol, from_date, to_date, "NSE")
                return symbol, candles

            done_count = skipped_count  # start counter from already-completed offset
            write_db = SessionLocal()
            try:
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = {executor.submit(fetch_one, sym): sym for sym in symbols}
                    for future in as_completed(futures):
                        # Check if user requested cancellation
                        if progress.stop_requested:
                            print("[KiteService] Bulk download cancelled by user.")
                            executor.shutdown(wait=False, cancel_futures=True)
                            break

                        # Abort once the access token is confirmed dead — otherwise every
                        # remaining in-flight/queued symbol keeps hitting a doomed API call
                        # and silently returns empty results instead of real history.
                        if self._token_invalid:
                            progress.errors.append(
                                "Kite access token expired mid-download — aborting. "
                                "Reconnect and retry to fetch the remaining symbols."
                            )
                            print(f"[KiteService] Bulk download aborted: token invalid after {done_count} symbols.")
                            executor.shutdown(wait=False, cancel_futures=True)
                            break

                        sym = futures[future]
                        progress.current_symbol = sym
                        try:
                            symbol, candles = future.result()
                            # Atomic upsert — avoids IntegrityError from the
                            # select-then-insert race when autoflush=False causes
                            # the session identity map to miss pending rows.
                            from sqlalchemy.dialects.sqlite import insert as sqlite_insert
                            for c in candles:
                                candle_date = (
                                    date.fromisoformat(c["date"])
                                    if isinstance(c["date"], str) else c["date"]
                                )
                                stmt = sqlite_insert(Candle).values(
                                    symbol=symbol, exchange="NSE", date=candle_date,
                                    open=c["open"], high=c["high"], low=c["low"],
                                    close=c["close"], volume=c["volume"],
                                ).on_conflict_do_update(
                                    index_elements=["symbol", "exchange", "date"],
                                    set_=dict(
                                        open=c["open"], high=c["high"], low=c["low"],
                                        close=c["close"], volume=c["volume"],
                                    )
                                )
                                write_db.execute(stmt)
                        except Exception as e:
                            err_msg = f"{sym}: {e}"
                            print(f"[KiteService] Bulk download error — {err_msg}")
                            progress.errors.append(err_msg)

                        done_count += 1
                        progress.done = done_count

                        if done_count % BATCH_COMMIT == 0:
                            write_db.commit()

                write_db.commit()
                if progress.stop_requested:
                    status = "cancelled"
                elif self._token_invalid:
                    status = "aborted (token expired)"
                else:
                    status = "complete"
                print(f"[KiteService] Bulk download {status}. {done_count} symbols processed.")
            finally:
                write_db.close()

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
