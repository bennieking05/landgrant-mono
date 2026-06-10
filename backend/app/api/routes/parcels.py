from __future__ import annotations
from typing import Optional

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_principal, get_db
from app.db import models
from app.db.models import Persona, ParcelStage
from app.security.access_scope import filter_parcels_query
from app.security.jwt_auth import JWTPrincipal
from app.security.rbac import Action, authorize


router = APIRouter(prefix="/parcels", tags=["parcels"])


@router.get("")
def list_parcels(
    project_id: Optional[str] = None,
    stage: Optional[str] = None,
    min_risk: Optional[int] = None,
    deadline_before: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    persona: Persona = Depends(get_current_persona),
    principal: JWTPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    authorize(persona, "parcel", Action.READ)
    q = db.query(models.Parcel)
    q = filter_parcels_query(db, principal, q)
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
            q = q.filter(models.Parcel.next_deadline_at.isnot(None)).filter(
                models.Parcel.next_deadline_at <= dt
            )
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
                "next_deadline_at": (
                    p.next_deadline_at.isoformat() + "Z" if p.next_deadline_at else None
                ),
                "geom": p.geom,
            }
            for p in items
        ],
    }
