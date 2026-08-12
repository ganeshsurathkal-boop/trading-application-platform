"""
TICKR — Plugin Manager

Handles the full lifecycle of uploaded indicator/scanner plugins:
  - Validate + extract an uploaded .zip (manifest.json + entry module)
  - Dynamically import the entry class and register it into the live
    indicator/scanner registry (app.indicators.registry / app.scanners.registry)
  - Persist install metadata so plugins survive a server restart
  - Enable / disable / uninstall

SECURITY NOTE: installing a plugin executes arbitrary Python code with
full server privileges — there is no sandboxing. Only install plugins
you wrote yourself or fully trust, the same way you'd trust any other
dependency you add to this codebase.
"""
import importlib.util
import io
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.models.plugin import InstalledPlugin

REQUIRED_MANIFEST_FIELDS = ["name", "type", "version", "entry_module", "entry_class"]
VALID_TYPES = {"indicator", "scanner"}

# Where extracted plugin code lives on disk (gitignored — machine-local, not source).
PLUGINS_ROOT = Path(__file__).resolve().parent.parent.parent / "installed_plugins"


class PluginError(Exception):
    """Raised for any invalid/untrusted plugin — caller turns this into an HTTP 400."""


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", text.strip().lower()).strip("_")
    return slug or "plugin"


def _registry_for(plugin_type: str):
    if plugin_type == "indicator":
        from app.indicators import registry
        from app.indicators.base import BaseIndicator as base_cls
    else:
        from app.scanners import registry
        from app.scanners.base import BaseScanner as base_cls
    return registry, base_cls


def _ensure_plugin_sdk_alias():
    """
    Make `import plugin_sdk` resolve for plugin code, regardless of where the
    plugin's files live on disk. Plugin authors never need to know about the
    app.* package layout — only this stable `plugin_sdk` name.
    """
    import app.plugin_sdk as sdk_impl
    sys.modules.setdefault("plugin_sdk", sdk_impl)


def _extract_zip_safely(zip_bytes: bytes, dest_dir: Path) -> None:
    """Extract a zip, rejecting path traversal / absolute-path entries (zip-slip)."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for member in zf.namelist():
            member_path = Path(member)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise PluginError(f"Unsafe path in plugin archive: {member}")
        dest_dir.mkdir(parents=True, exist_ok=True)
        zf.extractall(dest_dir)


def _read_manifest(plugin_dir: Path) -> dict:
    manifest_path = plugin_dir / "manifest.json"
    if not manifest_path.exists():
        raise PluginError("Archive is missing manifest.json at its root.")
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        raise PluginError(f"manifest.json is not valid JSON: {e}")

    missing = [f for f in REQUIRED_MANIFEST_FIELDS if not manifest.get(f)]
    if missing:
        raise PluginError(f"manifest.json is missing required field(s): {', '.join(missing)}")
    if manifest["type"] not in VALID_TYPES:
        raise PluginError(f"manifest 'type' must be one of {sorted(VALID_TYPES)}, got '{manifest['type']}'")

    entry_file = plugin_dir / f"{manifest['entry_module']}.py"
    if not entry_file.exists():
        raise PluginError(f"Entry module '{manifest['entry_module']}.py' not found in archive.")

    return manifest


def _load_instance(plugin_dir: Path, entry_module: str, entry_class: str, plugin_type: str):
    """Dynamically import entry_module.py from plugin_dir and instantiate entry_class."""
    _ensure_plugin_sdk_alias()
    module_file = plugin_dir / f"{entry_module}.py"
    module_name = f"tickr_plugin_{plugin_type}_{plugin_dir.name}"

    spec = importlib.util.spec_from_file_location(module_name, module_file)
    if spec is None or spec.loader is None:
        raise PluginError(f"Could not load module from {module_file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        sys.modules.pop(module_name, None)
        raise PluginError(f"Error executing plugin code: {e}")

    cls = getattr(module, entry_class, None)
    if cls is None:
        raise PluginError(f"Class '{entry_class}' not found in {entry_module}.py")

    _, base_cls = _registry_for(plugin_type)
    try:
        instance = cls()
    except Exception as e:
        raise PluginError(f"Failed to instantiate {entry_class}: {e}")
    if not isinstance(instance, base_cls):
        raise PluginError(
            f"{entry_class} must subclass plugin_sdk.{base_cls.__name__} "
            f"(got a class that doesn't inherit from it — check the plugin was built "
            f"against the current plugin_sdk)."
        )
    return instance


def install_from_zip(zip_bytes: bytes, db: Session) -> InstalledPlugin:
    """Validate, extract, load, register, and persist a plugin from raw zip bytes."""
    # Extract to a temp staging dir first so a bad upload never corrupts an existing install.
    staging_dir = PLUGINS_ROOT / "_staging" / _slugify(str(id(zip_bytes)))
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    try:
        _extract_zip_safely(zip_bytes, staging_dir)
        manifest = _read_manifest(staging_dir)

        name = manifest["name"]
        plugin_type = manifest["type"]
        dir_name = _slugify(f"{plugin_type}_{name}_{manifest['version']}")
        final_dir = PLUGINS_ROOT / f"{plugin_type}s" / dir_name

        # Validate it actually loads before touching the DB or replacing any existing install.
        instance = _load_instance(staging_dir, manifest["entry_module"], manifest["entry_class"], plugin_type)
        if instance.name != name:
            raise PluginError(
                f"manifest name '{name}' doesn't match the plugin class's declared "
                f"name '{instance.name}' — they must match."
            )

        existing = (
            db.query(InstalledPlugin)
            .filter_by(name=name, plugin_type=plugin_type)
            .first()
        )
        if existing:
            old_dir = PLUGINS_ROOT / f"{plugin_type}s" / existing.dir_name
            if old_dir.exists():
                shutil.rmtree(old_dir)
            db.delete(existing)
            db.flush()

        if final_dir.exists():
            shutil.rmtree(final_dir)
        final_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging_dir), str(final_dir))

        # Re-load from the final location (module identity tied to final path).
        instance = _load_instance(final_dir, manifest["entry_module"], manifest["entry_class"], plugin_type)

        row = InstalledPlugin(
            name=name,
            plugin_type=plugin_type,
            version=manifest["version"],
            description=manifest.get("description", ""),
            author=manifest.get("author", ""),
            entry_module=manifest["entry_module"],
            entry_class=manifest["entry_class"],
            dir_name=dir_name,
            enabled=True,
        )
        db.add(row)
        db.commit()
        db.refresh(row)

        registry, _ = _registry_for(plugin_type)
        registry.register_instance(instance)
        print(f"[PluginManager] Installed {plugin_type} plugin '{name}' v{manifest['version']}")
        return row
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)


def uninstall(plugin_id: int, db: Session) -> None:
    row = db.query(InstalledPlugin).filter_by(id=plugin_id).first()
    if not row:
        raise PluginError("Plugin not found.")
    registry, _ = _registry_for(row.plugin_type)
    registry.unregister(row.name)
    plugin_dir = PLUGINS_ROOT / f"{row.plugin_type}s" / row.dir_name
    if plugin_dir.exists():
        shutil.rmtree(plugin_dir)
    db.delete(row)
    db.commit()


def set_enabled(plugin_id: int, enabled: bool, db: Session) -> InstalledPlugin:
    row = db.query(InstalledPlugin).filter_by(id=plugin_id).first()
    if not row:
        raise PluginError("Plugin not found.")
    registry, _ = _registry_for(row.plugin_type)
    if enabled and not row.enabled:
        plugin_dir = PLUGINS_ROOT / f"{row.plugin_type}s" / row.dir_name
        instance = _load_instance(plugin_dir, row.entry_module, row.entry_class, row.plugin_type)
        registry.register_instance(instance)
    elif not enabled and row.enabled:
        registry.unregister(row.name)
    row.enabled = enabled
    db.commit()
    db.refresh(row)
    return row


def list_plugins(db: Session, plugin_type: Optional[str] = None) -> list[InstalledPlugin]:
    q = db.query(InstalledPlugin)
    if plugin_type:
        q = q.filter_by(plugin_type=plugin_type)
    return q.order_by(InstalledPlugin.installed_at.desc()).all()


SEED_PLUGINS_DIR = Path(__file__).resolve().parent.parent / "seed_plugins"


def seed_default_plugins(db: Session) -> None:
    """
    Install any bundled default plugins (currently: RSI) the first time the
    app runs, using the exact same install_from_zip() path a manual upload
    goes through. Skips any plugin whose name+type is already installed —
    safe to call on every startup.
    """
    if not SEED_PLUGINS_DIR.exists():
        return
    for zip_path in sorted(SEED_PLUGINS_DIR.glob("*.zip")):
        try:
            zip_bytes = zip_path.read_bytes()
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                manifest = json.loads(zf.read("manifest.json"))
            already_installed = (
                db.query(InstalledPlugin)
                .filter_by(name=manifest["name"], plugin_type=manifest["type"])
                .first()
            )
            if already_installed:
                continue
            install_from_zip(zip_bytes, db)
        except Exception as e:
            print(f"[PluginManager] Failed to seed default plugin {zip_path.name}: {e}")


def load_all_installed(db: Session) -> None:
    """Called once at app startup — loads every enabled installed plugin into the live registries."""
    from app.indicators.registry import get_registry as get_ind_registry
    from app.scanners.registry import get_registry as get_scan_registry
    get_ind_registry()   # force built-in discovery first
    get_scan_registry()

    rows = db.query(InstalledPlugin).filter_by(enabled=True).all()
    for row in rows:
        try:
            plugin_dir = PLUGINS_ROOT / f"{row.plugin_type}s" / row.dir_name
            instance = _load_instance(plugin_dir, row.entry_module, row.entry_class, row.plugin_type)
            registry, _ = _registry_for(row.plugin_type)
            registry.register_instance(instance)
            print(f"[PluginManager] Loaded installed {row.plugin_type} plugin '{row.name}' v{row.version}")
        except Exception as e:
            print(f"[PluginManager] Failed to load installed plugin '{row.name}': {e}")
