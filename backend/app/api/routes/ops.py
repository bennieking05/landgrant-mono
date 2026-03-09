from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_db
from app.db import models
from app.db.models import Persona
from app.security.rbac import Action, authorize


router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/routes/plan")
def route_plan(
    project_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    authorize(persona, "ops", Action.READ)
    parcels = (
        db.query(models.Parcel)
        .filter(models.Parcel.project_id == project_id)
        .order_by(models.Parcel.risk_score.desc(), models.Parcel.next_deadline_at.asc().nulls_last())
        .all()
    )
    ordered = [p.id for p in parcels]
    csv_lines = ["stop,parcel_id"] + [f"{idx+1},{pid}" for idx, pid in enumerate(ordered)]
    return {"project_id": project_id, "parcel_ids": ordered, "csv": "\n".join(csv_lines) + "\n"}



