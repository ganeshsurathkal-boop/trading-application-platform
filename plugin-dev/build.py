#!/usr/bin/env python3
"""
TICKR Plugin Builder

Packages a plugin folder (manifest.json + entry module) into a .zip in
dist/, ready to upload via the TICKR app's Admin > Plugins page.

Usage:
    python build.py indicators/rsi
    python build.py scanners/my_scanner
"""
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
REQUIRED_FIELDS = ("name", "type", "version", "entry_module", "entry_class")


def build(plugin_path: str) -> Path:
    src = (ROOT / plugin_path).resolve()
    if not src.is_dir():
        sys.exit(f"Not a directory: {src}")

    manifest_path = src / "manifest.json"
    if not manifest_path.exists():
        sys.exit(f"Missing manifest.json in {src}")
    manifest = json.loads(manifest_path.read_text())

    missing = [f for f in REQUIRED_FIELDS if not manifest.get(f)]
    if missing:
        sys.exit(f"manifest.json is missing required field(s): {', '.join(missing)}")
    if manifest["type"] not in ("indicator", "scanner"):
        sys.exit(f"manifest 'type' must be 'indicator' or 'scanner', got '{manifest['type']}'")

    entry_file = src / f"{manifest['entry_module']}.py"
    if not entry_file.exists():
        sys.exit(f"Entry module not found: {entry_file}")

    DIST.mkdir(exist_ok=True)
    slug = manifest["name"].lower().replace(" ", "_")
    out_path = DIST / f"{slug}-{manifest['type']}-{manifest['version']}.zip"

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in src.rglob("*"):
            if not f.is_file() or "__pycache__" in f.parts:
                continue
            zf.write(f, f.relative_to(src))

    print(f"Built {out_path.relative_to(ROOT)}  ({manifest['name']} v{manifest['version']}, {manifest['type']})")
    print("Upload it via the TICKR app: Profile -> Admin -> Plugins -> Upload")
    return out_path


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <indicators/plugin_name | scanners/plugin_name>")
    build(sys.argv[1])
