"""
TICKR — NSE Bhav Copy Service
Parses manually uploaded NSE Bhav Copy CSV/ZIP files and ingests them into the DB.
Also detects missing trading days (gaps) that need to be filled via Kite Connect.

Supported Bhav Copy formats:
  1. New format (CSV):  sec_bhavdata_full_YYYYMMDD.csv
  2. Old format (ZIP):  cmDDMONYYYYbhav.csv.zip  (contains cmDDMONYYYYbhav.csv)

Bhav Copy files can be downloaded from:
  - https://nsearchives.nseindia.com/products/content/  (new format)
  - https://www.nseindia.com/market-data/live-equity-market  (old format)
"""
import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional, Dict

import pandas as pd


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class BhavIngestResult:
    trading_date: Optional[date]
    symbols_updated: int = 0
    symbols_skipped: int = 0
    errors: List[str] = field(default_factory=list)
    success: bool = False
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "trading_date": self.trading_date.isoformat() if self.trading_date else None,
            "symbols_updated": self.symbols_updated,
            "symbols_skipped": self.symbols_skipped,
            "errors": self.errors[:20],
            "success": self.success,
            "message": self.message,
        }


# ── NSE trading calendar helper ───────────────────────────────────────────────

# Known NSE holidays for 2024-2026 (add more as needed)
NSE_HOLIDAYS = {
    # 2024
    date(2024, 1, 26), date(2024, 3, 25), date(2024, 3, 29), date(2024, 4, 14),
    date(2024, 4, 17), date(2024, 5, 23), date(2024, 6, 17), date(2024, 7, 17),
    date(2024, 8, 15), date(2024, 10, 2), date(2024, 10, 24), date(2024, 11, 1),
    date(2024, 11, 15), date(2024, 12, 25),
    # 2025
    date(2025, 1, 26), date(2025, 2, 26), date(2025, 3, 14), date(2025, 3, 31),
    date(2025, 4, 10), date(2025, 4, 14), date(2025, 4, 18), date(2025, 5, 1),
    date(2025, 8, 15), date(2025, 8, 27), date(2025, 10, 2), date(2025, 10, 2),
    date(2025, 10, 20), date(2025, 10, 23), date(2025, 11, 5), date(2025, 12, 25),
    # 2026
    date(2026, 1, 26), date(2026, 3, 20), date(2026, 4, 3), date(2026, 4, 6),
    date(2026, 4, 14), date(2026, 8, 15), date(2026, 10, 2),
}


def is_trading_day(d: date) -> bool:
    """Returns True if the given date is a weekday and not an NSE holiday."""
    return d.weekday() < 5 and d not in NSE_HOLIDAYS


def get_trading_days_between(start: date, end: date) -> List[date]:
    """Returns all NSE trading days in [start, end] inclusive."""
    days = []
    current = start
    while current <= end:
        if is_trading_day(current):
            days.append(current)
        current += timedelta(days=1)
    return days


# ── Bhav Copy column mappings ─────────────────────────────────────────────────

# New format (sec_bhavdata_full_YYYYMMDD.csv)
NEW_FORMAT_COLS = {
    "TckrSymb": "symbol",
    "SctySrs": "series",
    "OpnPric": "open",
    "HghPric": "high",
    "LwPric": "low",
    "ClsgPric": "close",
    "TtlTradgVol": "volume",
}

# Old format (cmDDMONYYYYbhav.csv)
OLD_FORMAT_COLS = {
    "SYMBOL": "symbol",
    "SERIES": "series",
    "OPEN": "open",
    "HIGH": "high",
    "LOW": "low",
    "CLOSE": "close",
    "TOTTRDQTY": "volume",
}


# ── Main service class ─────────────────────────────────────────────────────────

class BhavCopyService:

    # ── File parsing ──────────────────────────────────────────────────────────

    def _extract_date_from_filename(self, filename: str) -> Optional[date]:
        """
        Extract the trading date from the Bhav Copy filename.
        Supports:
          - sec_bhavdata_full_20260811.csv   → 2026-08-11
          - BhavCopy_NSE_CM_0_0_0_20260811_F_0000.csv → 2026-08-11
          - cm11AUG2026bhav.csv              → 2026-08-11
          - cm11AUG2026bhav.csv.zip          → 2026-08-11
        """
        filename = filename.upper()

        # New format: 8-digit date YYYYMMDD
        m = re.search(r"(\d{8})", filename)
        if m:
            try:
                return datetime_strptime(m.group(1), "%Y%m%d").date()
            except Exception:
                pass

        # Old format: DDMONyyyy e.g. 11AUG2026
        m = re.search(r"(\d{2})([A-Z]{3})(\d{4})", filename)
        if m:
            try:
                return datetime_strptime(f"{m.group(1)}{m.group(2)}{m.group(3)}", "%d%b%Y").date()
            except Exception:
                pass

        return None

    def _read_csv_bytes(self, file_bytes: bytes, filename: str) -> Optional[pd.DataFrame]:
        """
        Reads the CSV from bytes, handling ZIP archives transparently.
        Returns a DataFrame or None on failure.
        """
        fname_lower = filename.lower()
        try:
            if fname_lower.endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                    # Find the CSV inside the ZIP
                    csv_names = [n for n in z.namelist() if n.endswith(".csv")]
                    if not csv_names:
                        return None
                    with z.open(csv_names[0]) as f:
                        return pd.read_csv(f)
            else:
                return pd.read_csv(io.BytesIO(file_bytes))
        except Exception as e:
            print(f"[BhavCopyService] Could not read file: {e}")
            return None

    def _normalise_df(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Detect format (new / old) and normalise column names.
        Returns a DataFrame with columns: symbol, series, open, high, low, close, volume
        or None if format is unrecognised.
        """
        cols = set(df.columns.str.strip())

        if "TckrSymb" in cols:
            mapping = {k: v for k, v in NEW_FORMAT_COLS.items() if k in cols}
        elif "SYMBOL" in cols:
            mapping = {k: v for k, v in OLD_FORMAT_COLS.items() if k in cols}
        else:
            print(f"[BhavCopyService] Unrecognised columns: {list(df.columns)[:10]}")
            return None

        df = df.rename(columns={k: v for k, v in mapping.items()})
        df.columns = df.columns.str.strip()
        required = {"symbol", "open", "high", "low", "close", "volume"}
        if not required.issubset(set(df.columns)):
            print(f"[BhavCopyService] Missing required columns after normalisation")
            return None

        return df

    # ── Ingest ────────────────────────────────────────────────────────────────

    def parse_and_ingest(self, file_bytes: bytes, filename: str, db) -> BhavIngestResult:
        """
        Parse an uploaded NSE Bhav Copy CSV/ZIP and upsert OHLCV records into DB.
        Only EQ series records are ingested (filters out FO, BE, etc.).
        """
        from app.models.candle import Candle

        result = BhavIngestResult(trading_date=None)

        # 1. Determine trading date from filename
        trading_date = self._extract_date_from_filename(filename)
        if trading_date is None:
            result.message = (
                f"Could not determine trading date from filename '{filename}'. "
                "Expected formats: sec_bhavdata_full_YYYYMMDD.csv or cmDDMONYYYYbhav.csv.zip"
            )
            return result
        result.trading_date = trading_date

        # 2. Read file
        df = self._read_csv_bytes(file_bytes, filename)
        if df is None:
            result.message = "Failed to read file. Make sure it is a valid CSV or ZIP."
            return result

        # 3. Normalise columns
        df = self._normalise_df(df)
        if df is None:
            result.message = "Unrecognised Bhav Copy format. See supported formats in the docs."
            return result

        # 4. Filter to EQ series only
        if "series" in df.columns:
            df = df[df["series"].str.strip().str.upper() == "EQ"]

        # 5. Clean data
        df["symbol"] = df["symbol"].str.strip().str.upper()
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["symbol", "open", "high", "low", "close", "volume"])

        # 6. Upsert to DB
        updated = 0
        skipped = 0
        errors = []

        for _, row in df.iterrows():
            try:
                symbol = row["symbol"]
                existing = db.query(Candle).filter_by(
                    symbol=symbol, exchange="NSE", date=trading_date
                ).first()

                if existing:
                    existing.open = float(row["open"])
                    existing.high = float(row["high"])
                    existing.low = float(row["low"])
                    existing.close = float(row["close"])
                    existing.volume = float(row["volume"])
                else:
                    db.add(Candle(
                        symbol=symbol,
                        exchange="NSE",
                        date=trading_date,
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]),
                    ))
                updated += 1
            except Exception as e:
                errors.append(f"{row.get('symbol', '?')}: {e}")
                skipped += 1

        db.commit()

        result.symbols_updated = updated
        result.symbols_skipped = skipped
        result.errors = errors[:20]
        result.success = True
        result.message = (
            f"Bhav Copy for {trading_date.isoformat()} ingested: "
            f"{updated} symbols updated, {skipped} skipped."
        )
        print(f"[BhavCopyService] {result.message}")
        return result

    # ── Gap detection ─────────────────────────────────────────────────────────

    def detect_missing_days(self, db, lookback_days: int = 30) -> List[date]:
        """
        Find trading days that have no data in the DB within the last `lookback_days`.
        Returns a sorted list of missing dates (excluding today — market may still be open).
        """
        from app.models.candle import Candle

        today = date.today()
        start = today - timedelta(days=lookback_days)
        yesterday = today - timedelta(days=1)

        expected = get_trading_days_between(start, yesterday)
        if not expected:
            return []

        # Get distinct dates that exist in DB within the window
        rows = (
            db.query(Candle.date)
            .filter(Candle.date >= start, Candle.date <= yesterday)
            .distinct()
            .all()
        )
        existing_dates = {r.date for r in rows}

        missing = [d for d in expected if d not in existing_dates]
        missing.sort()
        print(f"[BhavCopyService] Detected {len(missing)} missing trading days in last {lookback_days} days")
        return missing

    # ── Upload history ────────────────────────────────────────────────────────

    def get_last_uploaded_dates(self, db, limit: int = 10) -> List[Dict]:
        """Return the most recently ingested Bhav Copy dates with symbol counts."""
        from app.models.candle import Candle
        from sqlalchemy import func

        rows = (
            db.query(Candle.date, func.count(Candle.symbol).label("count"))
            .group_by(Candle.date)
            .order_by(Candle.date.desc())
            .limit(limit)
            .all()
        )
        return [{"date": r.date.isoformat(), "symbol_count": r.count} for r in rows]


# Singleton
bhav_copy_service = BhavCopyService()


# ── datetime helper ────────────────────────────────────────────────────────────

def datetime_strptime(s: str, fmt: str):
    """Thin wrapper to avoid importing datetime in multiple places."""
    from datetime import datetime
    return datetime.strptime(s, fmt)
