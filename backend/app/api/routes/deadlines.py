from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_user, get_db
from app.db import models
from app.db.models import Persona
from app.security.rbac import Action, authorize
from app.services.hashing import sha256_hex
from app.services.deadline_rules import derive_deadlines, derive_deadlines_from_template_render


router = APIRouter(prefix="/deadlines", tags=["deadlines"])


@router.get("")
def list_deadlines(
    project_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    authorize(persona, "deadline", Action.READ)
    items = (
        db.query(models.Deadline)
        .filter(models.Deadline.project_id == project_id)
        .order_by(models.Deadline.due_at.asc())
        .all()
    )
    return {
        "project_id": project_id,
        "items": [
            {
                "id": d.id,
                "title": d.title,
                "due_at": d.due_at.isoformat() + "Z",
                "parcel_id": d.parcel_id,
                "timezone": d.timezone,
            }
            for d in items
        ],
    }


class DeadlineCreate(BaseModel):
    project_id: str
    parcel_id: str | None = None
    title: str
    due_at: str  # ISO
    timezone: str = "UTC"


@router.post("")
def create_deadline(
    payload: DeadlineCreate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    authorize(persona, "deadline", Action.WRITE)
    try:
        due = datetime.fromisoformat(payload.due_at.replace("Z", ""))
    except Exception as exc:
        raise HTTPException(status_code=422, detail="invalid_due_at") from exc

    d = models.Deadline(
        id=str(uuid4()),
        project_id=payload.project_id,
        parcel_id=payload.parcel_id,
        title=payload.title,
        due_at=due,
        timezone=payload.timezone,
    )
    db.add(d)
    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            user_id=getattr(user, "id", None),
            actor_persona=persona,
            action="deadline.create",
            resource="deadline",
            payload={"deadline_id": d.id, "project_id": d.project_id, "parcel_id": d.parcel_id, "title": d.title, "due_at": payload.due_at},
            hash=sha256_hex({"deadline_id": d.id, "project_id": d.project_id, "parcel_id": d.parcel_id, "title": d.title, "due_at": payload.due_at}),
        )
    )
    db.commit()
    return {"deadline_id": d.id}


@router.get("/ical")
def deadlines_ical(
    project_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    authorize(persona, "deadline", Action.READ)
    deadlines = (
        db.query(models.Deadline).filter(models.Deadline.project_id == project_id).order_by(models.Deadline.due_at.asc()).all()
    )

    def fmt(dt: datetime) -> str:
        # Use UTC in local dev.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LandRight//Deadlines//EN",
    ]
    for d in deadlines:
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{d.id}",
                f"DTSTAMP:{fmt(datetime.utcnow().replace(tzinfo=timezone.utc))}",
                f"DTSTART:{fmt(d.due_at)}",
                f"SUMMARY:{d.title}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    ics = "\r\n".join(lines) + "\r\n"
    return {"project_id": project_id, "ical": ics}


class DeadlineDeriveRequest(BaseModel):
    """Request to derive statutory deadlines from anchor events."""

    project_id: str
    parcel_id: str | None = None
    jurisdiction: str  # Two-letter state code (e.g., 'IN', 'TX')
    anchor_events: dict[str, str]  # Event name -> ISO date string
    template_id: str | None = None  # Optional: derive from template render
    template_variables: dict | None = None  # Variables used in template render
    persist: bool = True  # Whether to save derived deadlines to DB
    timezone: str = "America/Indiana/Indianapolis"


class DerivedDeadlineItem(BaseModel):
    """A single derived deadline."""

    id: str
    title: str
    description: str
    due_date: str  # ISO date
    anchor_event: str
    anchor_date: str  # ISO date
    offset_days: int
    citation: str
    deadline_type: str
    extendable: bool
    max_extension_days: int
    notes: str | None


class DeadlineDeriveResponse(BaseModel):
    """Response from deadline derivation."""

    jurisdiction: str
    project_id: str
    parcel_id: str | None
    derived_count: int
    persisted_count: int
    deadlines: list[DerivedDeadlineItem]
    errors: list[str]


@router.post("/derive", response_model=DeadlineDeriveResponse)
def derive_statutory_deadlines(
    payload: DeadlineDeriveRequest,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Derive statutory deadlines from anchor events based on jurisdiction rules.

    Accepts anchor events (e.g., offer_served, complaint_filed) and computes
    the corresponding statutory deadlines per the jurisdiction's rules pack.
    Optionally persists the derived deadlines to the database.
    """
    authorize(persona, "deadline", Action.WRITE)

    # Derive deadlines
    if payload.template_id and payload.template_variables:
        result = derive_deadlines_from_template_render(
            jurisdiction=payload.jurisdiction,
            template_id=payload.template_id,
            render_variables=payload.template_variables,
            additional_anchors=payload.anchor_events,
        )
    else:
        result = derive_deadlines(
            jurisdiction=payload.jurisdiction,
            anchor_events=payload.anchor_events,
        )

    # Convert to response items
    deadline_items: list[DerivedDeadlineItem] = []
    for dl in result.deadlines:
        deadline_items.append(
            DerivedDeadlineItem(
                id=dl.id,
                title=dl.title,
                description=dl.description,
                due_date=dl.due_date.isoformat(),
                anchor_event=dl.anchor_event,
                anchor_date=dl.anchor_date.isoformat(),
                offset_days=dl.offset_days,
                citation=dl.citation,
                deadline_type=dl.deadline_type,
                extendable=dl.extendable,
                max_extension_days=dl.max_extension_days,
                notes=dl.notes,
            )
        )

    persisted_count = 0

    # Persist to database if requested
    if payload.persist and deadline_items:
        for item in deadline_items:
            # Skip non-deadline types (floors, eligibility dates)
            if item.deadline_type not in ("deadline", "service_requirement"):
                continue

            try:
                due_dt = datetime.fromisoformat(item.due_date)
            except ValueError:
                continue

            # Create deadline with citation in title
            title_with_citation = f"{item.title} ({item.citation})" if item.citation else item.title

            d = models.Deadline(
                id=str(uuid4()),
                project_id=payload.project_id,
                parcel_id=payload.parcel_id,
                title=title_with_citation,
                due_at=due_dt,
                timezone=payload.timezone,
            )
            db.add(d)

            # Audit event
            db.add(
                models.AuditEvent(
                    id=str(uuid4()),
                    user_id=getattr(user, "id", None),
                    actor_persona=persona,
                    action="deadline.derive",
                    resource="deadline",
                    payload={
                        "deadline_id": d.id,
                        "project_id": d.project_id,
                        "parcel_id": d.parcel_id,
                        "title": d.title,
                        "due_at": item.due_date,
                        "anchor_event": item.anchor_event,
                        "citation": item.citation,
                        "jurisdiction": payload.jurisdiction,
                    },
                    hash=sha256_hex({
                        "deadline_id": d.id,
                        "anchor_event": item.anchor_event,
                        "citation": item.citation,
                    }),
                )
            )
            persisted_count += 1

        db.commit()

    return DeadlineDeriveResponse(
        jurisdiction=result.jurisdiction,
        project_id=payload.project_id,
        parcel_id=payload.parcel_id,
        derived_count=len(deadline_items),
        persisted_count=persisted_count,
        deadlines=deadline_items,
        errors=result.errors,
    )



