"""GIS Alignment and Segmentation API.

Agreement Reference: Section 3.2(h) - GIS alignment and parcel segmentation
(alignment import, segment generation, per-segment ED status)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_user, get_db
from app.db import models
from app.db.models import Persona, SegmentEDStatus
from app.security.rbac import Action, authorize
from app.services.hashing import sha256_hex


router = APIRouter(prefix="/alignments", tags=["alignments"])


# =============================================================================
# Request/Response Models
# =============================================================================


class AlignmentImport(BaseModel):
    """Import alignment geometry."""
    project_id: str
    name: str
    description: Optional[str] = None
    alignment_type: Optional[str] = None  # pipeline, transmission, road, etc.
    geometry: dict  # GeoJSON LineString or MultiLineString
    total_length_miles: Optional[float] = None


class AlignmentUpdate(BaseModel):
    """Update alignment metadata."""
    name: Optional[str] = None
    description: Optional[str] = None
    alignment_type: Optional[str] = None
    status: Optional[str] = None
    total_length_miles: Optional[float] = None


class SegmentCreate(BaseModel):
    """Create a segment linking alignment to parcel."""
    parcel_id: str
    segment_number: Optional[int] = None
    name: Optional[str] = None
    geometry: Optional[dict] = None  # GeoJSON LineString
    length_feet: Optional[float] = None
    width_feet: Optional[float] = None
    area_sqft: Optional[float] = None
    acquisition_type: Optional[str] = None  # fee, permanent_easement, temporary_easement


class SegmentUpdate(BaseModel):
    """Update segment, particularly ED status."""
    ed_status: Optional[str] = None
    acquisition_type: Optional[str] = None
    length_feet: Optional[float] = None
    width_feet: Optional[float] = None
    area_sqft: Optional[float] = None


class BulkSegmentGenerate(BaseModel):
    """Bulk generate segments from parcel list."""
    parcel_ids: list[str]
    acquisition_type: Optional[str] = "permanent_easement"


# =============================================================================
# Alignment Endpoints
# =============================================================================


@router.post("/import")
def import_alignment(
    payload: AlignmentImport,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Import alignment geometry (GeoJSON) for a project."""
    authorize(persona, "alignment", Action.WRITE)
    
    # Validate geometry type
    geom_type = payload.geometry.get("type")
    if geom_type not in ("LineString", "MultiLineString"):
        raise HTTPException(
            status_code=422,
            detail="geometry_must_be_linestring_or_multilinestring"
        )
    
    alignment_id = str(uuid4())
    alignment = models.Alignment(
        id=alignment_id,
        project_id=payload.project_id,
        name=payload.name,
        description=payload.description,
        alignment_type=payload.alignment_type,
        geometry=payload.geometry,
        total_length_miles=payload.total_length_miles,
        status="active",
        created_by=getattr(user, "id", None),
    )
    db.add(alignment)
    
    # Audit
    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            user_id=getattr(user, "id", None),
            actor_persona=persona,
            action="alignment.import",
            resource="alignment",
            payload={
                "alignment_id": alignment_id,
                "project_id": payload.project_id,
                "name": payload.name,
                "geometry_type": geom_type,
            },
            hash=sha256_hex({
                "alignment_id": alignment_id,
                "project_id": payload.project_id,
            }),
        )
    )
    db.commit()
    
    return {"alignment_id": alignment_id, "name": payload.name}


@router.get("")
def list_alignments(
    project_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """List alignments for a project."""
    authorize(persona, "alignment", Action.READ)
    
    items = (
        db.query(models.Alignment)
        .filter(models.Alignment.project_id == project_id)
        .order_by(models.Alignment.created_at.desc())
        .all()
    )
    
    return {
        "project_id": project_id,
        "count": len(items),
        "items": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "alignment_type": a.alignment_type,
                "total_length_miles": float(a.total_length_miles) if a.total_length_miles else None,
                "total_parcels": a.total_parcels,
                "status": a.status,
                "created_at": a.created_at.isoformat() + "Z" if a.created_at else None,
            }
            for a in items
        ],
    }


@router.get("/{alignment_id}")
def get_alignment(
    alignment_id: str,
    include_geometry: bool = True,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get alignment details including geometry and segments."""
    authorize(persona, "alignment", Action.READ)
    
    alignment = db.query(models.Alignment).filter(models.Alignment.id == alignment_id).first()
    if not alignment:
        raise HTTPException(status_code=404, detail="alignment_not_found")
    
    # Get segments
    segments = (
        db.query(models.Segment)
        .filter(models.Segment.alignment_id == alignment_id)
        .order_by(models.Segment.segment_number.asc())
        .all()
    )
    
    result = {
        "id": alignment.id,
        "project_id": alignment.project_id,
        "name": alignment.name,
        "description": alignment.description,
        "alignment_type": alignment.alignment_type,
        "total_length_miles": float(alignment.total_length_miles) if alignment.total_length_miles else None,
        "total_parcels": alignment.total_parcels,
        "status": alignment.status,
        "created_at": alignment.created_at.isoformat() + "Z" if alignment.created_at else None,
        "updated_at": alignment.updated_at.isoformat() + "Z" if alignment.updated_at else None,
        "segments": [
            {
                "id": s.id,
                "parcel_id": s.parcel_id,
                "segment_number": s.segment_number,
                "name": s.name,
                "ed_status": s.ed_status.value if s.ed_status else None,
                "acquisition_type": s.acquisition_type,
                "length_feet": float(s.length_feet) if s.length_feet else None,
                "width_feet": float(s.width_feet) if s.width_feet else None,
                "area_sqft": float(s.area_sqft) if s.area_sqft else None,
            }
            for s in segments
        ],
    }
    
    if include_geometry:
        result["geometry"] = alignment.geometry
        for i, s in enumerate(segments):
            result["segments"][i]["geometry"] = s.geometry
    
    return result


@router.put("/{alignment_id}")
def update_alignment(
    alignment_id: str,
    payload: AlignmentUpdate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Update alignment metadata."""
    authorize(persona, "alignment", Action.WRITE)
    
    alignment = db.query(models.Alignment).filter(models.Alignment.id == alignment_id).first()
    if not alignment:
        raise HTTPException(status_code=404, detail="alignment_not_found")
    
    changes = {}
    
    if payload.name is not None:
        alignment.name = payload.name
        changes["name"] = payload.name
    
    if payload.description is not None:
        alignment.description = payload.description
        changes["description"] = payload.description
    
    if payload.alignment_type is not None:
        alignment.alignment_type = payload.alignment_type
        changes["alignment_type"] = payload.alignment_type
    
    if payload.status is not None:
        alignment.status = payload.status
        changes["status"] = payload.status
    
    if payload.total_length_miles is not None:
        alignment.total_length_miles = payload.total_length_miles
        changes["total_length_miles"] = payload.total_length_miles
    
    alignment.updated_at = datetime.utcnow()
    
    if changes:
        db.add(
            models.AuditEvent(
                id=str(uuid4()),
                user_id=getattr(user, "id", None),
                actor_persona=persona,
                action="alignment.update",
                resource="alignment",
                payload={"alignment_id": alignment_id, "changes": changes},
                hash=sha256_hex({"alignment_id": alignment_id, "changes": changes}),
            )
        )
    
    db.commit()
    
    return {"alignment_id": alignment_id, "updated": True, "changes": changes}


# =============================================================================
# Segment Endpoints
# =============================================================================


@router.post("/{alignment_id}/segments")
def create_segment(
    alignment_id: str,
    payload: SegmentCreate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Create a segment linking alignment to parcel."""
    authorize(persona, "alignment", Action.WRITE)
    
    alignment = db.query(models.Alignment).filter(models.Alignment.id == alignment_id).first()
    if not alignment:
        raise HTTPException(status_code=404, detail="alignment_not_found")
    
    # Determine segment number
    existing_count = (
        db.query(models.Segment)
        .filter(models.Segment.alignment_id == alignment_id)
        .count()
    )
    segment_number = payload.segment_number or (existing_count + 1)
    
    segment_id = str(uuid4())
    segment = models.Segment(
        id=segment_id,
        alignment_id=alignment_id,
        parcel_id=payload.parcel_id,
        segment_number=segment_number,
        name=payload.name or f"Segment {segment_number}",
        geometry=payload.geometry,
        length_feet=payload.length_feet,
        width_feet=payload.width_feet,
        area_sqft=payload.area_sqft,
        ed_status=SegmentEDStatus.NOT_STARTED,
        acquisition_type=payload.acquisition_type,
    )
    db.add(segment)
    
    # Update alignment parcel count
    alignment.total_parcels = existing_count + 1
    
    # Audit
    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            user_id=getattr(user, "id", None),
            actor_persona=persona,
            action="segment.create",
            resource="alignment",
            payload={
                "segment_id": segment_id,
                "alignment_id": alignment_id,
                "parcel_id": payload.parcel_id,
                "segment_number": segment_number,
            },
            hash=sha256_hex({
                "segment_id": segment_id,
                "alignment_id": alignment_id,
            }),
        )
    )
    db.commit()
    
    return {"segment_id": segment_id, "segment_number": segment_number}


@router.post("/{alignment_id}/segments/bulk")
def bulk_generate_segments(
    alignment_id: str,
    payload: BulkSegmentGenerate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Bulk generate segments for multiple parcels."""
    authorize(persona, "alignment", Action.WRITE)
    
    alignment = db.query(models.Alignment).filter(models.Alignment.id == alignment_id).first()
    if not alignment:
        raise HTTPException(status_code=404, detail="alignment_not_found")
    
    # Get existing segment count
    existing_count = (
        db.query(models.Segment)
        .filter(models.Segment.alignment_id == alignment_id)
        .count()
    )
    
    created_segments = []
    for i, parcel_id in enumerate(payload.parcel_ids):
        segment_number = existing_count + i + 1
        segment_id = str(uuid4())
        
        segment = models.Segment(
            id=segment_id,
            alignment_id=alignment_id,
            parcel_id=parcel_id,
            segment_number=segment_number,
            name=f"Segment {segment_number}",
            ed_status=SegmentEDStatus.NOT_STARTED,
            acquisition_type=payload.acquisition_type,
        )
        db.add(segment)
        created_segments.append({
            "segment_id": segment_id,
            "parcel_id": parcel_id,
            "segment_number": segment_number,
        })
    
    # Update alignment parcel count
    alignment.total_parcels = existing_count + len(payload.parcel_ids)
    
    # Audit
    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            user_id=getattr(user, "id", None),
            actor_persona=persona,
            action="segment.bulk_create",
            resource="alignment",
            payload={
                "alignment_id": alignment_id,
                "parcel_count": len(payload.parcel_ids),
            },
            hash=sha256_hex({
                "alignment_id": alignment_id,
                "parcel_ids": payload.parcel_ids,
            }),
        )
    )
    db.commit()
    
    return {
        "alignment_id": alignment_id,
        "created_count": len(created_segments),
        "segments": created_segments,
    }


# =============================================================================
# Segment by Parcel Endpoints
# =============================================================================


segments_router = APIRouter(prefix="/segments", tags=["segments"])


@segments_router.get("")
def get_segments_by_parcel(
    parcel_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get all segments linked to a parcel."""
    authorize(persona, "alignment", Action.READ)
    
    segments = (
        db.query(models.Segment)
        .filter(models.Segment.parcel_id == parcel_id)
        .order_by(models.Segment.segment_number.asc())
        .all()
    )
    
    return {
        "parcel_id": parcel_id,
        "count": len(segments),
        "items": [
            {
                "id": s.id,
                "alignment_id": s.alignment_id,
                "segment_number": s.segment_number,
                "name": s.name,
                "ed_status": s.ed_status.value if s.ed_status else None,
                "acquisition_type": s.acquisition_type,
                "length_feet": float(s.length_feet) if s.length_feet else None,
                "width_feet": float(s.width_feet) if s.width_feet else None,
                "area_sqft": float(s.area_sqft) if s.area_sqft else None,
                "geometry": s.geometry,
            }
            for s in segments
        ],
    }


@segments_router.put("/{segment_id}")
def update_segment(
    segment_id: str,
    payload: SegmentUpdate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Update segment, particularly ED status."""
    authorize(persona, "alignment", Action.WRITE)
    
    segment = db.query(models.Segment).filter(models.Segment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="segment_not_found")
    
    changes = {}
    
    if payload.ed_status is not None:
        try:
            old_status = segment.ed_status
            segment.ed_status = SegmentEDStatus(payload.ed_status)
            changes["ed_status"] = {"from": old_status.value if old_status else None, "to": payload.ed_status}
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="invalid_ed_status") from exc
    
    if payload.acquisition_type is not None:
        segment.acquisition_type = payload.acquisition_type
        changes["acquisition_type"] = payload.acquisition_type
    
    if payload.length_feet is not None:
        segment.length_feet = payload.length_feet
        changes["length_feet"] = payload.length_feet
    
    if payload.width_feet is not None:
        segment.width_feet = payload.width_feet
        changes["width_feet"] = payload.width_feet
    
    if payload.area_sqft is not None:
        segment.area_sqft = payload.area_sqft
        changes["area_sqft"] = payload.area_sqft
    
    segment.updated_at = datetime.utcnow()
    
    if changes:
        db.add(
            models.AuditEvent(
                id=str(uuid4()),
                user_id=getattr(user, "id", None),
                actor_persona=persona,
                action="segment.update",
                resource="alignment",
                payload={"segment_id": segment_id, "parcel_id": segment.parcel_id, "changes": changes},
                hash=sha256_hex({"segment_id": segment_id, "changes": changes}),
            )
        )
    
    db.commit()
    
    return {"segment_id": segment_id, "updated": True, "changes": changes}


# Combine routers
router.include_router(segments_router)
