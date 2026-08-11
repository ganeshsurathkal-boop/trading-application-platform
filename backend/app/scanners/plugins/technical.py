"""52-Week High Scanner Plugin"""
from datetime import date, timedelta
from typing import List, Dict, Any
import random
from app.scanners.base import BaseScanner


class Week52HighScanner(BaseScanner):
    name = "52-week high"
    description = "Stocks trading at or near their 52-week high price"
    category = "technical"
    param_schema = [
        {"name": "threshold_pct", "type": "float", "min": 0, "max": 5, "step": 0.5,
         "label": "Within % of 52W High", "default": 1.0},
    ]

    def run(self, symbols: List[str], exchange: str = "NSE",
            as_of_date: date = None, **params) -> List[Dict[str, Any]]:
        from app.services.breeze_service import breeze_service
        threshold = float(params.get("threshold_pct", 1.0))
        as_of = as_of_date or date.today()
        from_date = as_of - timedelta(days=365)
        results = []

        for symbol in symbols:
            try:
                candles = breeze_service.fetch_historical_data(symbol, from_date, as_of, exchange)
                if not candles:
                    continue
                high_52w = max(c["high"] for c in candles)
                latest = candles[-1]
                current_price = latest["close"]
                prev_close = candles[-2]["close"] if len(candles) >= 2 else current_price
                change_pct = round((current_price - prev_close) / prev_close * 100, 2)

                if current_price >= high_52w * (1 - threshold / 100):
                    results.append({
                        "symbol": f"{symbol}.NS",
                        "exchange": exchange,
                        "price": current_price,
                        "change_pct": change_pct,
                        "week52_high": high_52w,
                    })
            except Exception as e:
                continue

        return sorted(results, key=lambda x: x["change_pct"], reverse=True)


class MACrossoverScanner(BaseScanner):
    name = "MA Crossover"
    description = "Stocks where fast MA has crossed above slow MA (Golden Cross)"
    category = "technical"
    param_schema = [
        {"name": "fast_period", "type": "int", "min": 5, "max": 50, "label": "Fast MA Period", "default": 20},
        {"name": "slow_period", "type": "int", "min": 20, "max": 200, "label": "Slow MA Period", "default": 50},
    ]

    def run(self, symbols: List[str], exchange: str = "NSE",
            as_of_date: date = None, **params) -> List[Dict[str, Any]]:
        from app.services.breeze_service import breeze_service
        fast = int(params.get("fast_period", 20))
        slow = int(params.get("slow_period", 50))
        as_of = as_of_date or date.today()
        from_date = as_of - timedelta(days=slow * 3)
        results = []

        for symbol in symbols:
            try:
                candles = breeze_service.fetch_historical_data(symbol, from_date, as_of, exchange)
                if len(candles) < slow + 2:
                    continue
                closes = [c["close"] for c in candles]

                def sma(data, period):
                    return sum(data[-period:]) / period

                fast_now = sma(closes, fast)
                fast_prev = sma(closes[:-1], fast)
                slow_now = sma(closes, slow)
                slow_prev = sma(closes[:-1], slow)

                if fast_prev <= slow_prev and fast_now > slow_now:
                    latest = candles[-1]
                    prev_close = candles[-2]["close"]
                    change_pct = round((latest["close"] - prev_close) / prev_close * 100, 2)
                    results.append({
                        "symbol": f"{symbol}.NS",
                        "exchange": exchange,
                        "price": latest["close"],
                        "change_pct": change_pct,
                        "fast_ma": round(fast_now, 2),
                        "slow_ma": round(slow_now, 2),
                    })
            except Exception:
                continue

        return results
