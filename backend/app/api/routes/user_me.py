"""Current-user preferences and saved parcel grid views (UX-4)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_user, get_db
from app.db import models
from app.db.models import Persona
from app.security.rbac import Action, authorize

router = APIRouter(prefix="/users/me", tags=["users"])

_STAFF_ASSIGNER_PERSONAS = (
    Persona.LAND_AGENT,
    Persona.IN_HOUSE_COUNSEL,
    Persona.OUTSIDE_COUNSEL,
    Persona.FIRM_ADMIN,
    Persona.PLATFORM_ADMIN,
    Persona.ADMIN,
)


class ParcelGridViewOut(BaseModel):
    id: str
    name: str
    payload: dict[str, Any]
    created_at: str
    updated_at: str


class ParcelGridViewsListResponse(BaseModel):
    items: list[ParcelGridViewOut]


class ParcelGridViewCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    payload: dict[str, Any] = Field(default_factory=dict)


class FirmAssigneeOut(BaseModel):
    id: str
    full_name: Optional[str] = None
    email: str
    persona: str


class FirmAssigneesResponse(BaseModel):
    items: list[FirmAssigneeOut]


@router.get("/firm-assignees", response_model=FirmAssigneesResponse)
def list_firm_assignees(
    persona: Persona = Depends(get_current_persona),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FirmAssigneesResponse:
    """Staff in the same firm (for parcel assignee filters and task pickers)."""
    authorize(persona, "parcel", Action.READ)
    if persona == Persona.LANDOWNER:
        return FirmAssigneesResponse(items=[])
    firm_id = getattr(user, "firm_id", None)
    if not firm_id:
        return FirmAssigneesResponse(items=[])
    rows = (
        db.query(models.User)
        .filter(
            models.User.firm_id == firm_id,
            models.User.persona.in_(_STAFF_ASSIGNER_PERSONAS),
        )
        .order_by(models.User.full_name.asc(), models.User.email.asc())
        .all()
    )
    return FirmAssigneesResponse(
        items=[
            FirmAssigneeOut(
                id=r.id,
                full_name=r.full_name,
                email=r.email,
                persona=r.persona.value if r.persona else "",
            )
            for r in rows
        ]
    )


@router.get("/parcel-views", response_model=ParcelGridViewsListResponse)
def list_parcel_views(
    persona: Persona = Depends(get_current_persona),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ParcelGridViewsListResponse:
    authorize(persona, "parcel", Action.READ)
    rows = (
        db.query(models.ParcelGridSavedView)
        .filter(models.ParcelGridSavedView.user_id == user.id)
        .order_by(models.ParcelGridSavedView.updated_at.desc())
        .all()
    )
    return ParcelGridViewsListResponse(
        items=[
            ParcelGridViewOut(
                id=r.id,
                name=r.name,
                payload=r.payload_json or {},
                created_at=r.created_at.isoformat() if r.created_at else "",
                updated_at=r.updated_at.isoformat() if r.updated_at else "",
            )
            for r in rows
        ]
    )


@router.post("/parcel-views", response_model=ParcelGridViewOut)
def create_parcel_view(
    body: ParcelGridViewCreate,
    persona: Persona = Depends(get_current_persona),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ParcelGridViewOut:
    authorize(persona, "parcel", Action.READ)
    name = body.name.strip()
    dup = (
        db.query(models.ParcelGridSavedView)
        .filter(
            models.ParcelGridSavedView.user_id == user.id,
            models.ParcelGridSavedView.name == name,
        )
        .first()
    )
    if dup:
        raise HTTPException(
            status_code=409,
            detail="A saved view with this name already exists",
        )
    now = datetime.utcnow()
    row = models.ParcelGridSavedView(
        id=str(uuid4()),
        user_id=user.id,
        name=name,
        payload_json=body.payload,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ParcelGridViewOut(
        id=row.id,
        name=row.name,
        payload=row.payload_json or {},
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


@router.delete("/parcel-views/{view_id}")
def delete_parcel_view(
    view_id: str,
    persona: Persona = Depends(get_current_persona),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    authorize(persona, "parcel", Action.READ)
    row = db.get(models.ParcelGridSavedView, view_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Saved view not found")
    if row.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    db.delete(row)
    db.commit()
    return {"status": "deleted", "id": view_id}
