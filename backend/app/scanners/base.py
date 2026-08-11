"""
TICKR — BaseScanner Abstract Class
All scanner plugins must inherit from this class.

To add a new scanner:
1. Create a file in app/scanners/plugins/
2. Define a class that inherits BaseScanner
3. Implement the run() method
4. The registry will auto-discover it — no other changes needed.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import date


class BaseScanner(ABC):
    # ── Required class-level attributes ───────────────────────────────────────
    name: str           # e.g. "52-week high"
    description: str    # Human-readable description
    category: str       # "technical" | "fundamental" | "plugin"
    param_schema: list  # UI parameter definitions

    @abstractmethod
    def run(
        self,
        symbols: List[str],
        exchange: str = "NSE",
        as_of_date: date = None,
        **params,
    ) -> List[Dict[str, Any]]:
        """
        Run the scan and return matching results.

        Args:
            symbols: List of stock symbols to scan
            exchange: Exchange code (NSE/BSE)
            as_of_date: Date to run the scan as of (defaults to today)
            **params: Scan-specific parameters

        Returns:
            List of dicts, each with at minimum:
            {symbol, exchange, price, change_pct, <scan-specific fields>}
        """
        ...

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "param_schema": self.param_schema,
        }
