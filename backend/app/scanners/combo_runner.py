"""
TICKR — Scanner Combination Runner

Runs multiple scanners against the same universe and intersects on symbol
(AND semantics): a stock only appears in the combined result if it matched
every scanner in the combination.
"""
from datetime import date
from typing import Any, Dict, List, Optional

from app.scanners.registry import get_scanner
from app.scanners.universes import get_universe

# Fields treated as canonical (taken from the first scanner only) rather than
# merged/prefixed from every scanner in the combination.
_CANONICAL_FIELDS = {"symbol", "exchange", "price", "change_pct"}


def run_combo(
    criteria: List[Dict[str, Any]],
    universe: str,
    exchange: str = "NSE",
    as_of_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    criteria: [{"scanner_name": str, "params": dict}, ...]
    Returns {"results": [...], "match_count": int, "per_criterion_counts": {...}}
    Raises ValueError if any scanner_name doesn't resolve.
    """
    symbols = get_universe(universe)
    as_of = as_of_date or date.today()

    per_scanner_results: Dict[str, Dict[str, dict]] = {}
    missing_scanners = []

    for c in criteria:
        scanner = get_scanner(c["scanner_name"])
        if not scanner:
            missing_scanners.append(c["scanner_name"])
            continue
        rows = scanner.run(symbols, exchange=exchange, as_of_date=as_of, **c.get("params", {}))
        per_scanner_results[c["scanner_name"]] = {r["symbol"]: r for r in rows}

    if missing_scanners:
        raise ValueError(f"Unknown scanner(s): {', '.join(missing_scanners)}")

    if not per_scanner_results:
        return {"results": [], "match_count": 0, "per_criterion_counts": {}}

    symbol_sets = [set(d.keys()) for d in per_scanner_results.values()]
    intersected_symbols = set.intersection(*symbol_sets)

    scanner_names_in_order = [c["scanner_name"] for c in criteria]
    combined_rows = []

    for sym in intersected_symbols:
        first_name = scanner_names_in_order[0]
        # Seed with ONLY the canonical fields from the first scanner — its
        # non-canonical extra fields get merged in fresh by the loop below,
        # same as every other scanner, so they're never diffed against
        # themselves and don't spuriously collide with their own values.
        base_row = {
            k: v for k, v in per_scanner_results[first_name][sym].items()
            if k in _CANONICAL_FIELDS
        }

        for name in scanner_names_in_order:
            row = per_scanner_results[name][sym]
            for k, v in row.items():
                if k in _CANONICAL_FIELDS:
                    continue
                key = k if k not in base_row else f"{name}__{k}"
                base_row[key] = v

        base_row["matched_criteria"] = list(scanner_names_in_order)
        combined_rows.append(base_row)

    combined_rows.sort(key=lambda r: r.get("change_pct", 0), reverse=True)

    return {
        "results": combined_rows,
        "match_count": len(combined_rows),
        "per_criterion_counts": {name: len(rows) for name, rows in per_scanner_results.items()},
    }
