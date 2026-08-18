"""TICKR — Saved Scanner Combination API routes"""
import io
import json
import re
from datetime import date, datetime
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_user
from app.database import get_db
from app.models.scan_combo import ScanCombo, ScanComboCriterion
from app.models.user import User
from app.scanners.combo_runner import run_combo
from app.scanners.registry import get_scanner

router = APIRouter(prefix="/api/scan-combos", tags=["scan-combos"])


class CriterionIn(BaseModel):
    scanner_name: str
    params: dict = {}


class ScanComboCreateReq(BaseModel):
    name: str
    universe: str = "NIFTY 50"
    exchange: str = "NSE"
    criteria: List[CriterionIn]


class ScanComboUpdateReq(BaseModel):
    name: Optional[str] = None
    universe: Optional[str] = None
    exchange: Optional[str] = None
    criteria: Optional[List[CriterionIn]] = None


class RunOverrideReq(BaseModel):
    universe: Optional[str] = None
    exchange: Optional[str] = None


class RunAdHocReq(BaseModel):
    universe: str = "NIFTY 50"
    exchange: str = "NSE"
    criteria: List[CriterionIn]


class ExportCriterion(BaseModel):
    scanner_name: str
    params: dict = {}


class ExportComboReq(BaseModel):
    combo_name: Optional[str] = None
    universe: str
    exchange: str = "NSE"
    criteria: List[ExportCriterion]
    run_at: str
    results: List[dict]


def _validate_criteria(criteria: List[CriterionIn]):
    unknown = [c.scanner_name for c in criteria if not get_scanner(c.scanner_name)]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown scanner(s): {', '.join(unknown)}")


def _get_owned_combo(combo_id: int, current_user: User, db: Session) -> ScanCombo:
    combo = (
        db.query(ScanCombo)
        .filter(ScanCombo.id == combo_id, ScanCombo.user_id == current_user.id)
        .first()
    )
    if not combo:
        raise HTTPException(status_code=404, detail="Saved scanner combination not found")
    return combo


def _set_criteria(combo: ScanCombo, criteria: List[CriterionIn], db: Session):
    for existing in list(combo.criteria):
        db.delete(existing)
    db.flush()
    for i, c in enumerate(criteria):
        db.add(ScanComboCriterion(
            combo_id=combo.id,
            scanner_name=c.scanner_name,
            params_json=json.dumps(c.params),
            position=i,
        ))


def _run_response(combo_id, combo_name, universe, exchange, criteria: List[dict], run_result: dict) -> dict:
    return {
        "combo_id": combo_id,
        "combo_name": combo_name,
        "universe": universe,
        "exchange": exchange,
        "run_at": datetime.utcnow().isoformat(),
        "criteria": criteria,
        **run_result,
    }


# ── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("")
def list_combos(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    combos = (
        db.query(ScanCombo)
        .filter(ScanCombo.user_id == current_user.id)
        .order_by(ScanCombo.updated_at.desc())
        .all()
    )
    return [c.to_dict() for c in combos]


@router.get("/{combo_id}")
def get_combo(combo_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    combo = _get_owned_combo(combo_id, current_user, db)
    return combo.to_dict()


@router.post("", status_code=201)
def create_combo(req: ScanComboCreateReq, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_criteria(req.criteria)
    combo = ScanCombo(name=req.name, user_id=current_user.id, universe=req.universe, exchange=req.exchange)
    db.add(combo)
    try:
        db.flush()
        _set_criteria(combo, req.criteria, db)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"A saved scanner combination named '{req.name}' already exists.")
    db.refresh(combo)
    return combo.to_dict()


@router.put("/{combo_id}")
def update_combo(combo_id: int, req: ScanComboUpdateReq, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    combo = _get_owned_combo(combo_id, current_user, db)
    if req.name is not None:
        combo.name = req.name
    if req.universe is not None:
        combo.universe = req.universe
    if req.exchange is not None:
        combo.exchange = req.exchange
    if req.criteria is not None:
        _validate_criteria(req.criteria)
        _set_criteria(combo, req.criteria, db)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"A saved scanner combination named '{req.name}' already exists.")
    db.refresh(combo)
    return combo.to_dict()


@router.delete("/{combo_id}")
def delete_combo(combo_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    combo = _get_owned_combo(combo_id, current_user, db)
    db.delete(combo)
    db.commit()
    return {"ok": True}


# ── Run ──────────────────────────────────────────────────────────────────────

@router.post("/{combo_id}/run")
def run_saved_combo(
    combo_id: int,
    req: RunOverrideReq = RunOverrideReq(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    combo = _get_owned_combo(combo_id, current_user, db)
    universe = req.universe or combo.universe
    exchange = req.exchange or combo.exchange
    criteria = [c.to_dict() for c in combo.criteria]
    try:
        result = run_combo(criteria, universe=universe, exchange=exchange, as_of_date=date.today())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _run_response(combo.id, combo.name, universe, exchange, criteria, result)


@router.post("/run-ad-hoc")
def run_ad_hoc(req: RunAdHocReq, current_user: User = Depends(get_current_user)):
    _validate_criteria(req.criteria)
    criteria = [c.dict() for c in req.criteria]
    try:
        result = run_combo(criteria, universe=req.universe, exchange=req.exchange, as_of_date=date.today())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _run_response(None, None, req.universe, req.exchange, criteria, result)


# ── Export ───────────────────────────────────────────────────────────────────

@router.post("/export")
def export_combo_run(req: ExportComboReq, current_user: User = Depends(get_current_user)):
    """
    Exports exactly the run payload the frontend already has in hand (results +
    the combination that produced them) rather than re-running server-side —
    re-running could return different numbers than what's on screen if market
    data has moved since the run, and this also works for ad-hoc (unsaved) runs.
    """
    results_df = pd.DataFrame(req.results)

    definition_rows = [{
        "Combination name": req.combo_name or "Ad-hoc scan",
        "Universe": req.universe,
        "Exchange": req.exchange,
        "Run at": req.run_at,
    }]
    criteria_rows = [
        {"Scanner": c.scanner_name, "Parameters": json.dumps(c.params)}
        for c in req.criteria
    ]

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        results_df.to_excel(writer, sheet_name="Results", index=False)
        pd.DataFrame(definition_rows).to_excel(writer, sheet_name="Scan Definition", index=False, startrow=0)
        pd.DataFrame(criteria_rows).to_excel(
            writer, sheet_name="Scan Definition", index=False, startrow=len(definition_rows) + 2
        )
    buf.seek(0)

    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", req.combo_name or "adhoc_scan").strip("_") or "scan"
    filename = f"{safe_name}_{date.today().isoformat()}.xlsx"

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
