"""
TICKR — Indicator Registry
Auto-discovers all BaseIndicator subclasses in the plugins/ directory.
No manual registration needed — just drop a new file in plugins/.
"""
import importlib
import pkgutil
from typing import Dict
from app.indicators.base import BaseIndicator

_registry: Dict[str, BaseIndicator] = {}


def _discover_plugins():
    """Walk the plugins package and import all modules to trigger class registration."""
    import app.indicators.plugins as pkg
    for _, module_name, _ in pkgutil.iter_modules(pkg.__path__):
        importlib.import_module(f"app.indicators.plugins.{module_name}")

    # Collect all concrete subclasses
    def get_all_subclasses(cls):
        result = []
        for sub in cls.__subclasses__():
            result.append(sub)
            result.extend(get_all_subclasses(sub))
        return result

    for cls in get_all_subclasses(BaseIndicator):
        try:
            instance = cls()
            _registry[instance.name] = instance
        except Exception as e:
            print(f"[IndicatorRegistry] Failed to register {cls.__name__}: {e}")

    print(f"[IndicatorRegistry] Registered {len(_registry)} indicators: {list(_registry.keys())}")


def get_registry() -> Dict[str, BaseIndicator]:
    if not _registry:
        _discover_plugins()
    return _registry


def get_indicator(name: str) -> BaseIndicator | None:
    return get_registry().get(name)


def list_indicators() -> list[dict]:
    return [ind.to_dict() for ind in get_registry().values()]
