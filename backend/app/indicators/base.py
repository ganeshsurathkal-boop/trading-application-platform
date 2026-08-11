"""
TICKR — BaseIndicator Abstract Class
All indicator plugins must inherit from this class.

To add a new indicator:
1. Create a file in app/indicators/plugins/
2. Define a class that inherits BaseIndicator
3. Implement the compute() method
4. The registry will auto-discover it — no other changes needed.
"""
from abc import ABC, abstractmethod
import pandas as pd


class BaseIndicator(ABC):
    # ── Required class-level attributes ───────────────────────────────────────
    name: str           # Short name, e.g. "SMA"
    label: str          # Display label template, e.g. "MA({period})"
    description: str    # Human-readable description
    category: str       # "trend" | "momentum" | "volatility" | "volume"
    overlay: bool       # True = overlaid on price chart; False = sub-chart panel
    default_params: dict  # Default parameter values, e.g. {"period": 20}
    param_schema: list  # List of param defs for UI, e.g. [{"name": "period", "type": "int", "min": 2, "max": 200}]

    @abstractmethod
    def compute(self, df: pd.DataFrame, **params) -> pd.DataFrame:
        """
        Compute indicator values.

        Args:
            df: DataFrame with columns [date, open, high, low, close, volume]
            **params: Indicator parameters (override default_params)

        Returns:
            DataFrame with one or more result columns added.
            Column names should be descriptive, e.g. "SMA_20", "BB_upper_20_2"
        """
        ...

    def get_label(self, **params) -> str:
        """Return formatted label string with actual param values."""
        merged = {**self.default_params, **params}
        try:
            return self.label.format(**merged)
        except (KeyError, AttributeError):
            return self.name

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "category": self.category,
            "overlay": self.overlay,
            "default_params": self.default_params,
            "param_schema": self.param_schema,
        }
