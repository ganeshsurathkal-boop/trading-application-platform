"""SMA — Simple Moving Average indicator plugin"""
import pandas as pd
from app.indicators.base import BaseIndicator


class SMAIndicator(BaseIndicator):
    name = "SMA"
    label = "MA({period})"
    description = "Simple Moving Average — average closing price over N periods"
    category = "trend"
    overlay = True
    default_params = {"period": 20}
    param_schema = [
        {"name": "period", "type": "int", "min": 2, "max": 500, "label": "Period"},
    ]

    def compute(self, df: pd.DataFrame, **params) -> pd.DataFrame:
        period = int(params.get("period", self.default_params["period"]))
        col = f"SMA_{period}"
        df = df.copy()
        df[col] = df["close"].rolling(window=period).mean().round(2)
        return df
