"""EMA — Exponential Moving Average indicator plugin"""
import pandas as pd
from app.indicators.base import BaseIndicator


class EMAIndicator(BaseIndicator):
    name = "EMA"
    label = "EMA({period})"
    description = "Exponential Moving Average — weighted average that reacts faster to recent prices"
    category = "trend"
    overlay = True
    default_params = {"period": 20}
    param_schema = [
        {"name": "period", "type": "int", "min": 2, "max": 500, "label": "Period"},
    ]

    def compute(self, df: pd.DataFrame, **params) -> pd.DataFrame:
        period = int(params.get("period", self.default_params["period"]))
        col = f"EMA_{period}"
        df = df.copy()
        df[col] = df["close"].ewm(span=period, adjust=False).mean().round(2)
        return df
