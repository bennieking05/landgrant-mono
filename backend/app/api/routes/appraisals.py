from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_user, get_db
from app.db import models
from app.db.models import Persona
from app.security.rbac import Action, authorize
from app.services.hashing import sha256_hex


router = APIRouter(prefix="/appraisals", tags=["appraisals"])


@router.get("")
def get_appraisal(
    parcel_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    authorize(persona, "appraisal", Action.READ)
    appraisal = db.query(models.Appraisal).filter(models.Appraisal.parcel_id == parcel_id).first()
    if not appraisal:
        return {"parcel_id": parcel_id, "appraisal": None}
    return {
        "parcel_id": parcel_id,
        "appraisal": {
            "id": appraisal.id,
            "value": float(appraisal.value) if appraisal.value is not None else None,
            "summary": appraisal.summary,
            "comps": appraisal.comps,
            "completed_at": appraisal.completed_at.isoformat() + "Z" if appraisal.completed_at else None,
            "attachment_id": appraisal.attachment_id,
        },
    }


class UpsertAppraisal(BaseModel):
    parcel_id: str
    value: float | None = None
    summary: str | None = None
    comps: list[dict] = []
    attachment_id: str | None = None


@router.post("")
def upsert_appraisal(
    payload: UpsertAppraisal,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    authorize(persona, "appraisal", Action.WRITE)
    appraisal = db.query(models.Appraisal).filter(models.Appraisal.parcel_id == payload.parcel_id).first()
    if not appraisal:
        appraisal = models.Appraisal(id=str(uuid4()), parcel_id=payload.parcel_id)
        db.add(appraisal)
    appraisal.value = payload.value
    appraisal.summary = payload.summary
    appraisal.comps = payload.comps
    appraisal.attachment_id = payload.attachment_id
    appraisal.completed_at = datetime.utcnow()

    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            user_id=getattr(user, "id", None),
            actor_persona=persona,
            action="appraisal.upsert",
            resource="appraisal",
            payload=payload.model_dump(),
            hash=sha256_hex(payload.model_dump()),
        )
    )
    db.commit()
    
    # Trigger workflow event if appraisal is complete with value
    if payload.value is not None:
        try:
            from app.tasks.workflow import process_workflow_event
            process_workflow_event.delay(
                "appraisal_complete",
                payload.parcel_id,
                {"appraisal_id": appraisal.id, "value": payload.value},
            )
        except Exception:
            pass  # Don't fail the request if workflow event fails
    
    return {"appraisal_id": appraisal.id}



