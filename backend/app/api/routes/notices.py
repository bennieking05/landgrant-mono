"""Notices and service attempts (contract §1.3)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_user, get_db
from app.db import models
from app.db.models import NoticeType, Persona, ServiceMethod, ServiceOutcome
from app.security.rbac import Action, authorize

router = APIRouter(prefix="/notices", tags=["notices"])


class NoticeCreate(BaseModel):
    parcel_id: str
    project_id: str
    notice_type: str
    method: str
    jurisdiction: str
    statutory_citation: Optional[str] = None
    template_id: Optional[str] = None
    document_id: Optional[str] = None


@router.get("")
def list_notices(
    parcel_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    authorize(persona, "communication", Action.READ)
    rows = (
        db.query(models.Notice)
        .filter(models.Notice.parcel_id == parcel_id)
        .order_by(models.Notice.date_issued.desc())
        .all()
    )
    return {
        "parcel_id": parcel_id,
        "items": [
            {
                "id": n.id,
                "notice_type": n.notice_type.value if n.notice_type else None,
                "method": n.method.value if n.method else None,
                "status": n.status,
                "date_issued": (
                    n.date_issued.isoformat() + "Z" if n.date_issued else None
                ),
                "jurisdiction": n.jurisdiction,
                "statutory_citation": n.statutory_citation,
            }
            for n in rows
        ],
    }


@router.post("")
def create_notice(
    payload: NoticeCreate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    authorize(persona, "communication", Action.WRITE)
    try:
        nt = NoticeType(payload.notice_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid_notice_type") from exc
    try:
        meth = ServiceMethod(payload.method)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid_service_method") from exc

    nid = str(uuid4())
    row = models.Notice(
        id=nid,
        parcel_id=payload.parcel_id,
        project_id=payload.project_id,
        notice_type=nt,
        date_issued=datetime.utcnow(),
        method=meth,
        document_id=payload.document_id,
        template_id=payload.template_id,
        jurisdiction=payload.jurisdiction.strip().upper(),
        statutory_citation=payload.statutory_citation,
        status="pending",
        created_by=getattr(user, "id", None),
    )
    db.add(row)
    db.commit()
    return {"notice_id": nid}


class ServiceAttemptCreate(BaseModel):
    notice_id: str
    method: str
    outcome: str = "pending"
    proof_document_id: Optional[str] = None
    proof_sha256: Optional[str] = None
    outcome_notes: Optional[str] = None


@router.post("/service-attempts")
def create_service_attempt(
    payload: ServiceAttemptCreate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    authorize(persona, "communication", Action.WRITE)
    notice = db.get(models.Notice, payload.notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="notice_not_found")
    try:
        meth = ServiceMethod(payload.method)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid_service_method") from exc
    try:
        out = ServiceOutcome(payload.outcome)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid_outcome") from exc

    n = (
        db.query(models.ServiceAttempt)
        .filter(models.ServiceAttempt.notice_id == payload.notice_id)
        .count()
    )
    sid = str(uuid4())
    proof_desc = None
    if payload.proof_sha256:
        proof_desc = f"sha256:{payload.proof_sha256.strip()}"

    row = models.ServiceAttempt(
        id=sid,
        notice_id=payload.notice_id,
        attempt_number=n + 1,
        method=meth,
        attempt_date=datetime.utcnow(),
        outcome=out,
        proof_document_id=payload.proof_document_id,
        proof_description=proof_desc,
        outcome_notes=payload.outcome_notes,
        created_by=getattr(user, "id", None),
    )
    db.add(row)
    db.commit()
    return {"service_attempt_id": sid}
