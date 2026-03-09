from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_db
from app.db import models
from app.db.models import Persona, ParcelStage
from app.security.rbac import Action, authorize


router = APIRouter(prefix="/parcels", tags=["parcels"])


@router.get("")
def list_parcels(
    project_id: str | None = None,
    stage: str | None = None,
    min_risk: int | None = None,
    deadline_before: str | None = None,
    limit: int = 100,
    offset: int = 0,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    authorize(persona, "parcel", Action.READ)
    q = db.query(models.Parcel)
    if project_id:
        q = q.filter(models.Parcel.project_id == project_id)
    if stage:
        try:
            stage_enum = ParcelStage(stage)
            q = q.filter(models.Parcel.stage == stage_enum)
        except ValueError:
            # Invalid stage value, filter will return no results
            q = q.filter(False)
    if min_risk is not None:
        q = q.filter(models.Parcel.risk_score >= min_risk)
    if deadline_before:
        try:
            dt = datetime.fromisoformat(deadline_before.replace("Z", ""))
            q = q.filter(models.Parcel.next_deadline_at.isnot(None)).filter(models.Parcel.next_deadline_at <= dt)
        except Exception:
            pass
    total = q.count()
    items = (
        q.order_by(models.Parcel.updated_at.desc())
        .offset(max(offset, 0))
        .limit(min(max(limit, 1), 500))
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "id": p.id,
                "project_id": p.project_id,
                "stage": p.stage.value if p.stage else "intake",
                "risk_score": p.risk_score,
                "next_deadline_at": p.next_deadline_at.isoformat() + "Z" if p.next_deadline_at else None,
                "geom": p.geom,
            }
            for p in items
        ],
    }



