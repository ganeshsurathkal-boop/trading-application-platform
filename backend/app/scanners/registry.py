"""TICKR — Scanner Registry (mirrors indicator registry pattern)"""
import importlib
import pkgutil
from typing import Dict, List
from app.scanners.base import BaseScanner

_registry: Dict[str, BaseScanner] = {}


def _discover_plugins():
    import app.scanners.plugins as pkg
    for _, module_name, _ in pkgutil.iter_modules(pkg.__path__):
        importlib.import_module(f"app.scanners.plugins.{module_name}")

    def get_all_subclasses(cls):
        result = []
        for sub in cls.__subclasses__():
            result.append(sub)
            result.extend(get_all_subclasses(sub))
        return result

    for cls in get_all_subclasses(BaseScanner):
        try:
            instance = cls()
            _registry[instance.name] = instance
        except Exception as e:
            print(f"[ScannerRegistry] Failed to register {cls.__name__}: {e}")

    print(f"[ScannerRegistry] Registered {len(_registry)} scanners: {list(_registry.keys())}")


def get_registry() -> Dict[str, BaseScanner]:
    if not _registry:
        _discover_plugins()
    return _registry


def get_scanner(name: str) -> BaseScanner | None:
    return get_registry().get(name)


def list_scanners() -> List[dict]:
    return [s.to_dict() for s in get_registry().values()]


def list_by_category() -> dict:
    result = {"technical": [], "fundamental": [], "plugin": []}
    for s in get_registry().values():
        cat = s.category if s.category in result else "plugin"
        result[cat].append(s.to_dict())
    return result
