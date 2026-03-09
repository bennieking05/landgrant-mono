"""Title Instruments and Curative Items API.

Agreement Reference: Section 3.2(e) - Title & curative tracking
(title document metadata, curative items and status)
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_user, get_db
from app.db import models
from app.db.models import Persona, CurativeStatus
from app.security.rbac import Action, authorize
from app.services.hashing import sha256_hex


router = APIRouter(prefix="/title", tags=["title"])

_LOCAL_STORAGE_ROOT = Path(__file__).resolve().parents[3] / "local_storage"


@router.get("/instruments")
def list_instruments(
    parcel_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    authorize(persona, "title", Action.READ)
    items = (
        db.query(models.TitleInstrument)
        .filter(models.TitleInstrument.parcel_id == parcel_id)
        .order_by(models.TitleInstrument.created_at.desc())
        .all()
    )
    return {
        "parcel_id": parcel_id,
        "items": [
            {
                "id": t.id,
                "document_id": t.document_id,
                "created_at": t.created_at.isoformat() + "Z" if t.created_at else None,
                "ocr_payload": t.ocr_payload,
                "metadata": t.metadata_json,
            }
            for t in items
        ],
    }


@router.post("/instruments")
async def upload_instrument(
    parcel_id: str = Form(...),
    file: UploadFile = File(...),
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    authorize(persona, "title", Action.WRITE)
    content = await file.read()
    doc_id = str(uuid4())
    sha = sha256_hex(content)
    out_dir = _LOCAL_STORAGE_ROOT / "title" / parcel_id
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = (file.filename or "title").replace("/", "_")
    out_path = out_dir / f"{doc_id}-{safe_name}"
    out_path.write_bytes(content)

    db.add(
        models.Document(
            id=doc_id,
            doc_type="title_instrument",
            version="1.0.0",
            sha256=sha,
            storage_path=str(out_path),
            metadata_json={"filename": file.filename, "content_type": file.content_type},
            created_by=getattr(user, "id", None),
        )
    )
    db.add(
        models.TitleInstrument(
            id=str(uuid4()),
            parcel_id=parcel_id,
            document_id=doc_id,
            # Stub OCR/parse output with confidence; real OCR can be swapped in later.
            ocr_payload={"confidence": 0.5, "entities": [], "source": "local_stub"},
            metadata_json={"parsed": False},
            created_at=datetime.utcnow(),
        )
    )
    db.commit()
    return {"document_id": doc_id, "sha256": sha, "storage_path": str(out_path)}


# =============================================================================
# Curative Items Request/Response Models
# =============================================================================


class CurativeItemCreate(BaseModel):
    """Create a new curative item."""
    parcel_id: str
    item_type: str  # missing_heir, unreleased_lien, variance, boundary_dispute, etc.
    description: str
    severity: str = "medium"  # low, medium, high, critical
    responsible_party: Optional[str] = None
    responsible_user_id: Optional[str] = None
    due_date: Optional[str] = None
    title_instrument_id: Optional[str] = None


class CurativeItemUpdate(BaseModel):
    """Update a curative item."""
    status: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None
    responsible_party: Optional[str] = None
    responsible_user_id: Optional[str] = None
    due_date: Optional[str] = None
    resolution_notes: Optional[str] = None
    resolution_document_id: Optional[str] = None


# =============================================================================
# Curative Items Endpoints
# =============================================================================


@router.post("/curative")
def create_curative_item(
    payload: CurativeItemCreate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Create a new curative item for a parcel."""
    authorize(persona, "title", Action.WRITE)
    
    # Validate severity
    valid_severities = ("low", "medium", "high", "critical")
    if payload.severity not in valid_severities:
        raise HTTPException(status_code=422, detail="invalid_severity")
    
    # Parse due date if provided
    due_date = None
    if payload.due_date:
        try:
            due_date = datetime.fromisoformat(payload.due_date.replace("Z", ""))
        except Exception as exc:
            raise HTTPException(status_code=422, detail="invalid_due_date") from exc
    
    item_id = str(uuid4())
    item = models.CurativeItem(
        id=item_id,
        parcel_id=payload.parcel_id,
        title_instrument_id=payload.title_instrument_id,
        item_type=payload.item_type,
        description=payload.description,
        severity=payload.severity,
        responsible_party=payload.responsible_party,
        responsible_user_id=payload.responsible_user_id,
        due_date=due_date,
        status=CurativeStatus.OPEN,
        identified_date=datetime.utcnow(),
        created_by=getattr(user, "id", None),
    )
    db.add(item)
    
    # Audit
    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            user_id=getattr(user, "id", None),
            actor_persona=persona,
            action="curative.create",
            resource="title",
            payload={
                "item_id": item_id,
                "parcel_id": payload.parcel_id,
                "item_type": payload.item_type,
                "severity": payload.severity,
            },
            hash=sha256_hex({
                "item_id": item_id,
                "parcel_id": payload.parcel_id,
            }),
        )
    )
    db.commit()
    
    return {"item_id": item_id, "status": "open"}


@router.get("/curative")
def list_curative_items(
    parcel_id: str,
    status: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """List curative items for a parcel."""
    authorize(persona, "title", Action.READ)
    
    query = db.query(models.CurativeItem).filter(models.CurativeItem.parcel_id == parcel_id)
    
    if status:
        try:
            query = query.filter(models.CurativeItem.status == CurativeStatus(status))
        except ValueError:
            raise HTTPException(status_code=422, detail="invalid_status")
    
    items = query.order_by(models.CurativeItem.created_at.desc()).all()
    
    return {
        "parcel_id": parcel_id,
        "count": len(items),
        "items": [
            {
                "id": c.id,
                "item_type": c.item_type,
                "description": c.description,
                "severity": c.severity,
                "status": c.status.value if c.status else None,
                "responsible_party": c.responsible_party,
                "responsible_user_id": c.responsible_user_id,
                "due_date": c.due_date.isoformat() + "Z" if c.due_date else None,
                "identified_date": c.identified_date.isoformat() + "Z" if c.identified_date else None,
                "resolved_date": c.resolved_date.isoformat() + "Z" if c.resolved_date else None,
                "title_instrument_id": c.title_instrument_id,
                "resolution_notes": c.resolution_notes,
            }
            for c in items
        ],
    }


@router.get("/curative/{item_id}")
def get_curative_item(
    item_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get a specific curative item by ID."""
    authorize(persona, "title", Action.READ)
    
    item = db.query(models.CurativeItem).filter(models.CurativeItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="item_not_found")
    
    return {
        "id": item.id,
        "parcel_id": item.parcel_id,
        "item_type": item.item_type,
        "description": item.description,
        "severity": item.severity,
        "status": item.status.value if item.status else None,
        "responsible_party": item.responsible_party,
        "responsible_user_id": item.responsible_user_id,
        "due_date": item.due_date.isoformat() + "Z" if item.due_date else None,
        "identified_date": item.identified_date.isoformat() + "Z" if item.identified_date else None,
        "resolved_date": item.resolved_date.isoformat() + "Z" if item.resolved_date else None,
        "title_instrument_id": item.title_instrument_id,
        "resolution_notes": item.resolution_notes,
        "resolution_document_id": item.resolution_document_id,
        "metadata": item.metadata_json,
        "created_at": item.created_at.isoformat() + "Z" if item.created_at else None,
        "updated_at": item.updated_at.isoformat() + "Z" if item.updated_at else None,
    }


@router.put("/curative/{item_id}")
def update_curative_item(
    item_id: str,
    payload: CurativeItemUpdate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Update a curative item."""
    authorize(persona, "title", Action.WRITE)
    
    item = db.query(models.CurativeItem).filter(models.CurativeItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="item_not_found")
    
    changes = {}
    
    if payload.status is not None:
        try:
            old_status = item.status
            new_status = CurativeStatus(payload.status)
            item.status = new_status
            changes["status"] = {"from": old_status.value if old_status else None, "to": payload.status}
            
            # Set resolved_date if transitioning to resolved/waived
            if payload.status in ("resolved", "waived") and not item.resolved_date:
                item.resolved_date = datetime.utcnow()
                changes["resolved_date"] = item.resolved_date.isoformat()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="invalid_status") from exc
    
    if payload.severity is not None:
        valid_severities = ("low", "medium", "high", "critical")
        if payload.severity not in valid_severities:
            raise HTTPException(status_code=422, detail="invalid_severity")
        item.severity = payload.severity
        changes["severity"] = payload.severity
    
    if payload.description is not None:
        item.description = payload.description
        changes["description"] = payload.description
    
    if payload.responsible_party is not None:
        item.responsible_party = payload.responsible_party
        changes["responsible_party"] = payload.responsible_party
    
    if payload.responsible_user_id is not None:
        item.responsible_user_id = payload.responsible_user_id
        changes["responsible_user_id"] = payload.responsible_user_id
    
    if payload.due_date is not None:
        try:
            item.due_date = datetime.fromisoformat(payload.due_date.replace("Z", ""))
            changes["due_date"] = payload.due_date
        except Exception as exc:
            raise HTTPException(status_code=422, detail="invalid_due_date") from exc
    
    if payload.resolution_notes is not None:
        item.resolution_notes = payload.resolution_notes
        changes["resolution_notes"] = payload.resolution_notes
    
    if payload.resolution_document_id is not None:
        item.resolution_document_id = payload.resolution_document_id
        changes["resolution_document_id"] = payload.resolution_document_id
    
    item.updated_at = datetime.utcnow()
    
    if changes:
        db.add(
            models.AuditEvent(
                id=str(uuid4()),
                user_id=getattr(user, "id", None),
                actor_persona=persona,
                action="curative.update",
                resource="title",
                payload={"item_id": item_id, "parcel_id": item.parcel_id, "changes": changes},
                hash=sha256_hex({"item_id": item_id, "changes": changes}),
            )
        )
    
    db.commit()
    
    return {"item_id": item_id, "updated": True, "changes": changes}


@router.get("/curative/analytics/summary")
def get_curative_analytics(
    project_id: Optional[str] = None,
    parcel_id: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get curative items analytics - counts and types summary."""
    authorize(persona, "title", Action.READ)
    
    query = db.query(models.CurativeItem)
    
    if parcel_id:
        query = query.filter(models.CurativeItem.parcel_id == parcel_id)
    elif project_id:
        # Join through parcel to filter by project
        query = query.join(models.Parcel).filter(models.Parcel.project_id == project_id)
    
    items = query.all()
    
    # Count by status
    status_counts = {}
    for item in items:
        status = item.status.value if item.status else "unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Count by type
    type_counts = {}
    for item in items:
        item_type = item.item_type or "unknown"
        type_counts[item_type] = type_counts.get(item_type, 0) + 1
    
    # Count by severity
    severity_counts = {}
    for item in items:
        severity = item.severity or "unknown"
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    # Count overdue items
    now = datetime.utcnow()
    overdue_count = sum(
        1 for item in items
        if item.due_date and item.due_date < now and item.status in (CurativeStatus.OPEN, CurativeStatus.IN_PROGRESS)
    )
    
    return {
        "project_id": project_id,
        "parcel_id": parcel_id,
        "total_items": len(items),
        "status_breakdown": status_counts,
        "type_breakdown": type_counts,
        "severity_breakdown": severity_counts,
        "overdue_count": overdue_count,
    }

