"""BBands — Bollinger Bands indicator plugin"""
import pandas as pd
from app.indicators.base import BaseIndicator


class BollingerBandsIndicator(BaseIndicator):
    name = "BBands"
    label = "BBands({period},{std})"
    description = "Bollinger Bands — price envelope based on standard deviation"
    category = "volatility"
    overlay = True
    default_params = {"period": 20, "std": 2}
    param_schema = [
        {"name": "period", "type": "int", "min": 2, "max": 500, "label": "Period"},
        {"name": "std", "type": "float", "min": 0.5, "max": 5, "step": 0.5, "label": "Std Dev"},
    ]

    def compute(self, df: pd.DataFrame, **params) -> pd.DataFrame:
        period = int(params.get("period", self.default_params["period"]))
        std = float(params.get("std", self.default_params["std"]))
        df = df.copy()
        sma = df["close"].rolling(window=period).mean()
        sd = df["close"].rolling(window=period).std()
        df[f"BB_middle_{period}_{std}"] = sma.round(2)
        df[f"BB_upper_{period}_{std}"] = (sma + std * sd).round(2)
        df[f"BB_lower_{period}_{std}"] = (sma - std * sd).round(2)
        return df
