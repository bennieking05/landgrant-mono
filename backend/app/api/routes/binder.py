from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_db
from app.db import models
from app.db.models import ApprovalStatus, Persona
from app.security.rbac import Action, authorize

router = APIRouter(prefix="/binder", tags=["binder"])


@router.get("/status")
def binder_status(
    project_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    authorize(persona, "binder", Action.READ)

    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project_not_found")

    parcel_ids = [
        p[0]
        for p in db.query(models.Parcel.id)
        .filter(models.Parcel.project_id == project_id)
        .all()
    ]

    comms = (
        db.query(func.count(models.Communication.id))
        .filter(models.Communication.project_id == project_id)
        .scalar()
        or 0
    )

    rules = 0
    if parcel_ids:
        rules = (
            db.query(func.count(models.RuleResult.id))
            .filter(models.RuleResult.project_id == project_id)
            .scalar()
            or 0
        )

    docs = (
        db.query(func.count(models.Document.id))
        .filter(models.Document.project_id == project_id)
        .scalar()
        or 0
    )

    pending_approvals = (
        db.query(func.count(models.Approval.id))
        .filter(
            models.Approval.project_id == project_id,
            models.Approval.status.in_(
                [ApprovalStatus.PENDING_REVIEW, ApprovalStatus.DRAFT]
            ),
        )
        .scalar()
        or 0
    )

    sections = [
        {
            "name": "Comms timeline",
            "status": "Complete" if comms > 0 else "Missing",
            "detail": f"{int(comms)} communication(s) on project",
        },
        {
            "name": "Rule results",
            "status": "Complete" if rules > 0 else "Missing",
            "detail": f"{int(rules)} parcel rule result(s)",
        },
        {
            "name": "Project documents",
            "status": "Complete" if docs > 0 else "Missing",
            "detail": f"{int(docs)} document(s) on file for project",
        },
        {
            "name": "Approvals",
            "status": "Complete" if pending_approvals == 0 else "Pending",
            "detail": f"{int(pending_approvals)} open approval(s)",
        },
    ]
    done = sum(1 for s in sections if s["status"] == "Complete")
    completeness_pct = round(100.0 * done / len(sections), 1) if sections else 0.0

    return {
        "project_id": project_id,
        "completeness_pct": completeness_pct,
        "sections": sections,
    }
