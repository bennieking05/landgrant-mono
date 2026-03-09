"""ROE (Right-of-Entry) Management API.

Agreement Reference: Section 3.2(c) - ROE management (templates, effective/expiry dates,
access windows, field check-in/out)
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_user, get_db
from app.db import models
from app.db.models import Persona, ROEStatus
from app.security.rbac import Action, authorize
from app.services.hashing import sha256_hex


router = APIRouter(prefix="/roe", tags=["roe"])


# =============================================================================
# Request/Response Models
# =============================================================================


class ROECreate(BaseModel):
    """Create a new ROE agreement."""
    parcel_id: str
    project_id: str
    effective_date: str  # ISO date
    expiry_date: str  # ISO date
    conditions: Optional[str] = None
    permitted_activities: Optional[list[str]] = None
    access_windows: Optional[dict] = None  # e.g., {"weekdays": "8am-5pm"}
    template_id: Optional[str] = None
    landowner_party_id: Optional[str] = None


class ROEUpdate(BaseModel):
    """Update an existing ROE."""
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None
    conditions: Optional[str] = None
    permitted_activities: Optional[list[str]] = None
    access_windows: Optional[dict] = None
    status: Optional[str] = None
    signed_by: Optional[str] = None
    signed_at: Optional[str] = None


class FieldEventCreate(BaseModel):
    """Record a field check-in or check-out event."""
    event_type: str  # check_in, check_out
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    personnel_name: Optional[str] = None
    notes: Optional[str] = None
    photo_document_ids: Optional[list[str]] = None


# =============================================================================
# ROE CRUD Endpoints
# =============================================================================


@router.post("")
def create_roe(
    payload: ROECreate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Create a new ROE agreement for a parcel."""
    authorize(persona, "roe", Action.WRITE)
    
    try:
        effective = datetime.fromisoformat(payload.effective_date.replace("Z", ""))
        expiry = datetime.fromisoformat(payload.expiry_date.replace("Z", ""))
    except Exception as exc:
        raise HTTPException(status_code=422, detail="invalid_date_format") from exc
    
    if expiry <= effective:
        raise HTTPException(status_code=422, detail="expiry_must_be_after_effective")
    
    roe_id = str(uuid4())
    roe = models.ROE(
        id=roe_id,
        parcel_id=payload.parcel_id,
        project_id=payload.project_id,
        effective_date=effective,
        expiry_date=expiry,
        conditions=payload.conditions,
        permitted_activities=payload.permitted_activities or [],
        access_windows=payload.access_windows,
        template_id=payload.template_id,
        landowner_party_id=payload.landowner_party_id,
        status=ROEStatus.DRAFT,
        created_by=getattr(user, "id", None),
    )
    db.add(roe)
    
    # Audit event
    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            user_id=getattr(user, "id", None),
            actor_persona=persona,
            action="roe.create",
            resource="roe",
            payload={
                "roe_id": roe_id,
                "parcel_id": payload.parcel_id,
                "project_id": payload.project_id,
                "effective_date": payload.effective_date,
                "expiry_date": payload.expiry_date,
            },
            hash=sha256_hex({
                "roe_id": roe_id,
                "parcel_id": payload.parcel_id,
                "effective_date": payload.effective_date,
            }),
        )
    )
    db.commit()
    
    return {"roe_id": roe_id, "status": "draft"}


@router.get("")
def list_roes(
    parcel_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """List all ROE agreements for a parcel."""
    authorize(persona, "roe", Action.READ)
    
    items = (
        db.query(models.ROE)
        .filter(models.ROE.parcel_id == parcel_id)
        .order_by(models.ROE.created_at.desc())
        .all()
    )
    
    return {
        "parcel_id": parcel_id,
        "items": [
            {
                "id": r.id,
                "project_id": r.project_id,
                "effective_date": r.effective_date.isoformat() + "Z" if r.effective_date else None,
                "expiry_date": r.expiry_date.isoformat() + "Z" if r.expiry_date else None,
                "status": r.status.value if r.status else None,
                "conditions": r.conditions,
                "permitted_activities": r.permitted_activities,
                "access_windows": r.access_windows,
                "signed_by": r.signed_by,
                "signed_at": r.signed_at.isoformat() + "Z" if r.signed_at else None,
                "template_id": r.template_id,
                "document_id": r.document_id,
                "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
            }
            for r in items
        ],
    }


@router.get("/{roe_id}")
def get_roe(
    roe_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get a specific ROE by ID."""
    authorize(persona, "roe", Action.READ)
    
    roe = db.query(models.ROE).filter(models.ROE.id == roe_id).first()
    if not roe:
        raise HTTPException(status_code=404, detail="roe_not_found")
    
    # Get field events
    events = (
        db.query(models.ROEFieldEvent)
        .filter(models.ROEFieldEvent.roe_id == roe_id)
        .order_by(models.ROEFieldEvent.event_time.desc())
        .all()
    )
    
    return {
        "id": roe.id,
        "parcel_id": roe.parcel_id,
        "project_id": roe.project_id,
        "effective_date": roe.effective_date.isoformat() + "Z" if roe.effective_date else None,
        "expiry_date": roe.expiry_date.isoformat() + "Z" if roe.expiry_date else None,
        "status": roe.status.value if roe.status else None,
        "conditions": roe.conditions,
        "permitted_activities": roe.permitted_activities,
        "access_windows": roe.access_windows,
        "signed_by": roe.signed_by,
        "signed_at": roe.signed_at.isoformat() + "Z" if roe.signed_at else None,
        "template_id": roe.template_id,
        "document_id": roe.document_id,
        "landowner_party_id": roe.landowner_party_id,
        "expiry_warning_sent": roe.expiry_warning_sent,
        "created_at": roe.created_at.isoformat() + "Z" if roe.created_at else None,
        "updated_at": roe.updated_at.isoformat() + "Z" if roe.updated_at else None,
        "field_events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "event_time": e.event_time.isoformat() + "Z" if e.event_time else None,
                "latitude": float(e.latitude) if e.latitude else None,
                "longitude": float(e.longitude) if e.longitude else None,
                "personnel_name": e.personnel_name,
                "notes": e.notes,
                "photo_document_ids": e.photo_document_ids,
            }
            for e in events
        ],
    }


@router.put("/{roe_id}")
def update_roe(
    roe_id: str,
    payload: ROEUpdate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Update an existing ROE agreement."""
    authorize(persona, "roe", Action.WRITE)
    
    roe = db.query(models.ROE).filter(models.ROE.id == roe_id).first()
    if not roe:
        raise HTTPException(status_code=404, detail="roe_not_found")
    
    # Track changes for audit
    changes = {}
    
    if payload.effective_date is not None:
        try:
            roe.effective_date = datetime.fromisoformat(payload.effective_date.replace("Z", ""))
            changes["effective_date"] = payload.effective_date
        except Exception as exc:
            raise HTTPException(status_code=422, detail="invalid_effective_date") from exc
    
    if payload.expiry_date is not None:
        try:
            roe.expiry_date = datetime.fromisoformat(payload.expiry_date.replace("Z", ""))
            changes["expiry_date"] = payload.expiry_date
        except Exception as exc:
            raise HTTPException(status_code=422, detail="invalid_expiry_date") from exc
    
    if payload.conditions is not None:
        roe.conditions = payload.conditions
        changes["conditions"] = payload.conditions
    
    if payload.permitted_activities is not None:
        roe.permitted_activities = payload.permitted_activities
        changes["permitted_activities"] = payload.permitted_activities
    
    if payload.access_windows is not None:
        roe.access_windows = payload.access_windows
        changes["access_windows"] = payload.access_windows
    
    if payload.status is not None:
        try:
            roe.status = ROEStatus(payload.status)
            changes["status"] = payload.status
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="invalid_status") from exc
    
    if payload.signed_by is not None:
        roe.signed_by = payload.signed_by
        changes["signed_by"] = payload.signed_by
    
    if payload.signed_at is not None:
        try:
            roe.signed_at = datetime.fromisoformat(payload.signed_at.replace("Z", ""))
            changes["signed_at"] = payload.signed_at
        except Exception as exc:
            raise HTTPException(status_code=422, detail="invalid_signed_at") from exc
    
    roe.updated_at = datetime.utcnow()
    
    # Audit event
    if changes:
        db.add(
            models.AuditEvent(
                id=str(uuid4()),
                user_id=getattr(user, "id", None),
                actor_persona=persona,
                action="roe.update",
                resource="roe",
                payload={"roe_id": roe_id, "changes": changes},
                hash=sha256_hex({"roe_id": roe_id, "changes": changes}),
            )
        )
    
    db.commit()
    
    return {"roe_id": roe_id, "updated": True, "changes": changes}


# =============================================================================
# Field Events Endpoints
# =============================================================================


@router.post("/{roe_id}/field-events")
def create_field_event(
    roe_id: str,
    payload: FieldEventCreate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Record a field check-in or check-out event."""
    authorize(persona, "roe", Action.WRITE)
    
    roe = db.query(models.ROE).filter(models.ROE.id == roe_id).first()
    if not roe:
        raise HTTPException(status_code=404, detail="roe_not_found")
    
    if payload.event_type not in ("check_in", "check_out"):
        raise HTTPException(status_code=422, detail="invalid_event_type")
    
    # Validate ROE is active
    if roe.status not in (ROEStatus.ACTIVE, ROEStatus.SIGNED):
        raise HTTPException(status_code=422, detail="roe_not_active")
    
    event_id = str(uuid4())
    event = models.ROEFieldEvent(
        id=event_id,
        roe_id=roe_id,
        event_type=payload.event_type,
        event_time=datetime.utcnow(),
        latitude=payload.latitude,
        longitude=payload.longitude,
        user_id=getattr(user, "id", None),
        personnel_name=payload.personnel_name,
        notes=payload.notes,
        photo_document_ids=payload.photo_document_ids or [],
    )
    db.add(event)
    
    # Audit event
    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            user_id=getattr(user, "id", None),
            actor_persona=persona,
            action=f"roe.field_{payload.event_type}",
            resource="roe",
            payload={
                "roe_id": roe_id,
                "event_id": event_id,
                "event_type": payload.event_type,
                "latitude": payload.latitude,
                "longitude": payload.longitude,
            },
            hash=sha256_hex({
                "roe_id": roe_id,
                "event_id": event_id,
                "event_type": payload.event_type,
            }),
        )
    )
    db.commit()
    
    return {
        "event_id": event_id,
        "roe_id": roe_id,
        "event_type": payload.event_type,
        "event_time": event.event_time.isoformat() + "Z",
    }


@router.get("/{roe_id}/field-events")
def list_field_events(
    roe_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """List all field events for an ROE."""
    authorize(persona, "roe", Action.READ)
    
    events = (
        db.query(models.ROEFieldEvent)
        .filter(models.ROEFieldEvent.roe_id == roe_id)
        .order_by(models.ROEFieldEvent.event_time.desc())
        .all()
    )
    
    return {
        "roe_id": roe_id,
        "items": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "event_time": e.event_time.isoformat() + "Z" if e.event_time else None,
                "latitude": float(e.latitude) if e.latitude else None,
                "longitude": float(e.longitude) if e.longitude else None,
                "personnel_name": e.personnel_name,
                "user_id": e.user_id,
                "notes": e.notes,
                "photo_document_ids": e.photo_document_ids,
            }
            for e in events
        ],
    }


# =============================================================================
# Expiry Tracking Endpoints
# =============================================================================


@router.get("/expiring")
def list_expiring_roes(
    project_id: Optional[str] = None,
    days_threshold: int = 30,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """List ROEs expiring within the threshold (default 30 days)."""
    authorize(persona, "roe", Action.READ)
    
    threshold_date = datetime.utcnow() + timedelta(days=days_threshold)
    
    query = db.query(models.ROE).filter(
        models.ROE.expiry_date <= threshold_date,
        models.ROE.expiry_date >= datetime.utcnow(),
        models.ROE.status.in_([ROEStatus.ACTIVE, ROEStatus.SIGNED]),
    )
    
    if project_id:
        query = query.filter(models.ROE.project_id == project_id)
    
    items = query.order_by(models.ROE.expiry_date.asc()).all()
    
    return {
        "threshold_days": days_threshold,
        "project_id": project_id,
        "count": len(items),
        "items": [
            {
                "id": r.id,
                "parcel_id": r.parcel_id,
                "project_id": r.project_id,
                "expiry_date": r.expiry_date.isoformat() + "Z" if r.expiry_date else None,
                "days_until_expiry": (r.expiry_date - datetime.utcnow()).days if r.expiry_date else None,
                "status": r.status.value if r.status else None,
                "expiry_warning_sent": r.expiry_warning_sent,
            }
            for r in items
        ],
    }


@router.get("/expired")
def list_expired_roes(
    project_id: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """List all expired ROEs."""
    authorize(persona, "roe", Action.READ)
    
    query = db.query(models.ROE).filter(
        models.ROE.expiry_date < datetime.utcnow(),
        models.ROE.status.not_in([ROEStatus.EXPIRED, ROEStatus.REVOKED]),
    )
    
    if project_id:
        query = query.filter(models.ROE.project_id == project_id)
    
    items = query.order_by(models.ROE.expiry_date.desc()).all()
    
    return {
        "project_id": project_id,
        "count": len(items),
        "items": [
            {
                "id": r.id,
                "parcel_id": r.parcel_id,
                "project_id": r.project_id,
                "expiry_date": r.expiry_date.isoformat() + "Z" if r.expiry_date else None,
                "days_expired": (datetime.utcnow() - r.expiry_date).days if r.expiry_date else None,
                "status": r.status.value if r.status else None,
            }
            for r in items
        ],
    }
