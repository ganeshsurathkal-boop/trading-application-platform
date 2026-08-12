"""
Local dev-time stub for `plugin_sdk` — mirrors the interface the running
TICKR app exposes (backend/app/plugin_sdk.py), so your editor/linter can
resolve `from plugin_sdk import BaseIndicator` while you write a plugin here.

This file is NOT packaged into your plugin's .zip and is NOT what your
plugin actually runs against. When TICKR loads an installed plugin, it
binds the top-level `plugin_sdk` module name to its own real
BaseIndicator/BaseScanner classes (see backend/app/plugin_sdk.py) — that's
the only thing that matters for correctness. This stub exists purely so
plugin-dev/ is pleasant to work in on its own (imports resolve, type
checkers don't complain) without needing the backend installed alongside it.
"""
from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Dict, List

import pandas as pd


class BaseIndicator(ABC):
    name: str
    label: str
    description: str
    category: str        # "trend" | "momentum" | "volatility" | "volume"
    overlay: bool         # True = drawn on the price chart; False = its own sub-chart panel
    default_params: dict
    param_schema: list

    @abstractmethod
    def compute(self, df: pd.DataFrame, **params) -> pd.DataFrame:
        """df has columns [date, open, high, low, close, volume]; return df with result column(s) added."""
        ...

    def get_label(self, **params) -> str:
        merged = {**self.default_params, **params}
        try:
            return self.label.format(**merged)
        except (KeyError, AttributeError):
            return self.name

    def to_dict(self) -> dict:
        return {
            "name": self.name, "label": self.label, "description": self.description,
            "category": self.category, "overlay": self.overlay,
            "default_params": self.default_params, "param_schema": self.param_schema,
        }


class BaseScanner(ABC):
    name: str
    description: str
    category: str
    param_schema: list

    @abstractmethod
    def run(
        self, symbols: List[str], exchange: str = "NSE", as_of_date: date = None, **params
    ) -> List[Dict[str, Any]]:
        """Return a list of dicts, each with at minimum {symbol, exchange, price, change_pct, ...}."""
        ...

    def to_dict(self) -> dict:
        return {
            "name": self.name, "description": self.description,
            "category": self.category, "param_schema": self.param_schema,
        }
