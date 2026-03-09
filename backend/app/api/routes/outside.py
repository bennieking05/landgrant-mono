from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_user, get_db
from app.db import models
from app.db.models import Persona, ParcelStage, PARCEL_STAGE_TRANSITIONS
from app.security.rbac import Action, authorize
from app.services.hashing import sha256_hex


router = APIRouter(prefix="/outside", tags=["outside"])


@router.get("/repository/completeness")
def repository_completeness(
    project_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    authorize(persona, "case", Action.READ)
    # Minimal completeness model: binder + at least one title instrument + one appraisal.
    has_binder = db.query(models.Document).filter(models.Document.doc_type == "binder").count() > 0
    has_title = db.query(models.TitleInstrument).count() > 0
    has_appraisal = db.query(models.Appraisal).count() > 0
    checks = {
        "binder_exported": has_binder,
        "title_attached": has_title,
        "appraisal_attached": has_appraisal,
    }
    percent = int(round((sum(1 for v in checks.values() if v) / len(checks)) * 100))
    missing = [k for k, v in checks.items() if not v]
    return {"project_id": project_id, "percent": percent, "checks": checks, "missing": missing}


class CaseInitiate(BaseModel):
    project_id: str
    parcel_id: str
    template_id: str


@router.post("/case/initiate")
def initiate_case(
    payload: CaseInitiate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    authorize(persona, "case", Action.WRITE)
    draft_id = str(uuid4())
    db.add(
        models.Task(
            id=str(uuid4()),
            project_id=payload.project_id,
            parcel_id=payload.parcel_id,
            title=f"Outside counsel draft initiated: {payload.template_id}",
            persona=Persona.OUTSIDE_COUNSEL,
            metadata_json={"draft_id": draft_id, "template_id": payload.template_id},
        )
    )
    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            user_id=getattr(user, "id", None),
            actor_persona=persona,
            action="outside.case.initiate",
            resource="case",
            payload=payload.model_dump(),
            hash=sha256_hex(payload.model_dump()),
        )
    )
    db.commit()
    return {"draft_id": draft_id, "docket_number": "DOCKET-TBD"}


class StatusUpdate(BaseModel):
    project_id: str
    parcel_id: str | None = None
    new_status: str
    reason: str


def validate_stage_transition(old_stage: ParcelStage | None, new_stage: ParcelStage) -> bool:
    """Validate that a stage transition is allowed."""
    if old_stage is None:
        # Allow setting initial stage
        return new_stage == ParcelStage.INTAKE
    allowed = PARCEL_STAGE_TRANSITIONS.get(old_stage, [])
    return new_stage in allowed


@router.post("/status")
def update_status(
    payload: StatusUpdate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    authorize(persona, "status", Action.EXECUTE)

    # Validate the new_status is a valid ParcelStage
    try:
        new_stage = ParcelStage(payload.new_status)
    except ValueError:
        valid_stages = [s.value for s in ParcelStage]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{payload.new_status}'. Valid stages: {valid_stages}",
        )

    # Get current parcel stage for transition validation
    old_stage = None
    old_status_str = None
    if payload.parcel_id:
        parcel = db.query(models.Parcel).filter(models.Parcel.id == payload.parcel_id).first()
        if parcel:
            old_stage = parcel.stage
            old_status_str = old_stage.value if old_stage else None

            # Validate the transition
            if not validate_stage_transition(old_stage, new_stage):
                allowed = [s.value for s in PARCEL_STAGE_TRANSITIONS.get(old_stage, [])]
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid transition from '{old_status_str}' to '{payload.new_status}'. "
                           f"Allowed transitions: {allowed}",
                )

            # Update parcel stage
            parcel.stage = new_stage

    record = {
        "project_id": payload.project_id,
        "parcel_id": payload.parcel_id,
        "new_status": payload.new_status,
        "reason": payload.reason,
        "occurred_at": datetime.utcnow().isoformat() + "Z",
    }
    db.add(
        models.StatusChange(
            id=str(uuid4()),
            project_id=payload.project_id,
            parcel_id=payload.parcel_id,
            old_status=old_status_str,
            new_status=payload.new_status,
            reason=payload.reason,
            actor_persona=persona,
            hash=sha256_hex(record),
        )
    )
    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            user_id=getattr(user, "id", None),
            actor_persona=persona,
            action="status.change",
            resource="status",
            payload=record,
            hash=sha256_hex(record),
        )
    )
    db.commit()
    return {"status_change_id": record["occurred_at"], "status": "ok", "old_status": old_status_str, "new_status": payload.new_status}



