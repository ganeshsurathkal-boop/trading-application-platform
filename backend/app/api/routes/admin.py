"""
TICKR — Admin: Plugin Management

Upload, list, enable/disable, and uninstall indicator/scanner plugins.

SECURITY NOTE: uploading a plugin here executes arbitrary Python code
with full server privileges — there is no sandboxing. This app has a
single user account and no separate admin role, so these endpoints are
reachable by anyone who can log in. Only install plugins you wrote
yourself or fully trust.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_user
from app.database import get_db
from app.models.user import User
from app.services import plugin_manager
from app.services.plugin_manager import PluginError

router = APIRouter(prefix="/api/admin/plugins", tags=["admin"])


@router.get("")
def list_plugins(
    type: str | None = Query(None, description="Filter by 'indicator' or 'scanner'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = plugin_manager.list_plugins(db, plugin_type=type)
    return {"plugins": [r.to_dict() for r in rows]}


@router.post("/upload", status_code=201)
async def upload_plugin(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Plugin must be uploaded as a .zip file.")
    zip_bytes = await file.read()
    try:
        row = plugin_manager.install_from_zip(zip_bytes, db)
    except PluginError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "plugin": row.to_dict()}


@router.post("/{plugin_id}/enable")
def enable_plugin(plugin_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        row = plugin_manager.set_enabled(plugin_id, True, db)
    except PluginError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ok": True, "plugin": row.to_dict()}


@router.post("/{plugin_id}/disable")
def disable_plugin(plugin_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        row = plugin_manager.set_enabled(plugin_id, False, db)
    except PluginError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ok": True, "plugin": row.to_dict()}


@router.delete("/{plugin_id}")
def delete_plugin(plugin_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        plugin_manager.uninstall(plugin_id, db)
    except PluginError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ok": True}
