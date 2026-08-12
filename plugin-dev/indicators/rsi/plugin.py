"""RSI — Relative Strength Index indicator plugin"""
import pandas as pd
from plugin_sdk import BaseIndicator


class RSIIndicator(BaseIndicator):
    name = "RSI"
    label = "RSI({period})"
    description = "Relative Strength Index — momentum oscillator measuring speed and magnitude of price changes"
    category = "momentum"
    overlay = False  # renders as its own sub-chart panel, below the volume bars
    default_params = {"period": 14}
    param_schema = [
        {"name": "period", "type": "int", "min": 2, "max": 100, "label": "Period"},
    ]

    def compute(self, df: pd.DataFrame, **params) -> pd.DataFrame:
        period = int(params.get("period", self.default_params["period"]))
        df = df.copy()
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, float("inf"))
        df[f"RSI_{period}"] = (100 - 100 / (1 + rs)).round(2)
        return df
