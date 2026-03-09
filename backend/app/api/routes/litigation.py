"""Litigation Case Management API.

Agreement Reference: Section 3.2(d) - Litigation calendar
(quick-take vs standard flag, court/cause number, lead counsel, key litigation stages)
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
from app.db.models import Persona, LitigationStatus
from app.security.rbac import Action, authorize
from app.services.hashing import sha256_hex


router = APIRouter(prefix="/litigation", tags=["litigation"])


# =============================================================================
# Request/Response Models
# =============================================================================


class LitigationCaseCreate(BaseModel):
    """Create a new litigation case."""
    parcel_id: str
    project_id: str
    court: str
    court_county: Optional[str] = None
    cause_number: Optional[str] = None
    is_quick_take: bool = False
    lead_counsel_internal: Optional[str] = None
    lead_counsel_internal_id: Optional[str] = None
    lead_counsel_outside: Optional[str] = None
    lead_counsel_outside_firm: Optional[str] = None


class LitigationCaseUpdate(BaseModel):
    """Update litigation case."""
    status: Optional[str] = None
    cause_number: Optional[str] = None
    court: Optional[str] = None
    court_county: Optional[str] = None
    is_quick_take: Optional[bool] = None
    lead_counsel_internal: Optional[str] = None
    lead_counsel_internal_id: Optional[str] = None
    lead_counsel_outside: Optional[str] = None
    lead_counsel_outside_firm: Optional[str] = None
    filed_date: Optional[str] = None
    filing_document_id: Optional[str] = None
    commissioners_hearing_date: Optional[str] = None
    possession_order_date: Optional[str] = None
    trial_date: Optional[str] = None
    settlement_amount: Optional[float] = None
    final_judgment_amount: Optional[float] = None
    closed_date: Optional[str] = None


# =============================================================================
# Litigation Case Endpoints
# =============================================================================


@router.post("")
def create_litigation_case(
    payload: LitigationCaseCreate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Create a new litigation case for a parcel."""
    authorize(persona, "litigation", Action.WRITE)
    
    # Check for existing case on this parcel
    existing = (
        db.query(models.LitigationCase)
        .filter(
            models.LitigationCase.parcel_id == payload.parcel_id,
            models.LitigationCase.status.not_in([LitigationStatus.CLOSED, LitigationStatus.SETTLED]),
        )
        .first()
    )
    
    if existing:
        raise HTTPException(
            status_code=422,
            detail="active_case_exists_for_parcel"
        )
    
    case_id = str(uuid4())
    case = models.LitigationCase(
        id=case_id,
        parcel_id=payload.parcel_id,
        project_id=payload.project_id,
        court=payload.court,
        court_county=payload.court_county,
        cause_number=payload.cause_number,
        is_quick_take=payload.is_quick_take,
        status=LitigationStatus.NOT_FILED,
        lead_counsel_internal=payload.lead_counsel_internal,
        lead_counsel_internal_id=payload.lead_counsel_internal_id,
        lead_counsel_outside=payload.lead_counsel_outside,
        lead_counsel_outside_firm=payload.lead_counsel_outside_firm,
        created_by=getattr(user, "id", None),
    )
    db.add(case)
    
    # Create initial status change record
    db.add(
        models.StatusChange(
            id=str(uuid4()),
            project_id=payload.project_id,
            parcel_id=payload.parcel_id,
            old_status=None,
            new_status=LitigationStatus.NOT_FILED.value,
            reason="Case created",
            actor_persona=persona,
            hash=sha256_hex({
                "case_id": case_id,
                "status": LitigationStatus.NOT_FILED.value,
            }),
        )
    )
    
    # Audit
    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            user_id=getattr(user, "id", None),
            actor_persona=persona,
            action="litigation.create",
            resource="litigation",
            payload={
                "case_id": case_id,
                "parcel_id": payload.parcel_id,
                "court": payload.court,
                "is_quick_take": payload.is_quick_take,
            },
            hash=sha256_hex({
                "case_id": case_id,
                "parcel_id": payload.parcel_id,
            }),
        )
    )
    db.commit()
    
    return {"case_id": case_id, "status": LitigationStatus.NOT_FILED.value}


@router.get("")
def list_litigation_cases(
    project_id: Optional[str] = None,
    parcel_id: Optional[str] = None,
    status: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """List litigation cases with optional filters."""
    authorize(persona, "litigation", Action.READ)
    
    query = db.query(models.LitigationCase)
    
    if project_id:
        query = query.filter(models.LitigationCase.project_id == project_id)
    
    if parcel_id:
        query = query.filter(models.LitigationCase.parcel_id == parcel_id)
    
    if status:
        try:
            query = query.filter(models.LitigationCase.status == LitigationStatus(status))
        except ValueError:
            raise HTTPException(status_code=422, detail="invalid_status")
    
    items = query.order_by(models.LitigationCase.created_at.desc()).all()
    
    return {
        "count": len(items),
        "items": [
            {
                "id": c.id,
                "parcel_id": c.parcel_id,
                "project_id": c.project_id,
                "cause_number": c.cause_number,
                "court": c.court,
                "court_county": c.court_county,
                "is_quick_take": c.is_quick_take,
                "status": c.status.value if c.status else None,
                "lead_counsel_internal": c.lead_counsel_internal,
                "lead_counsel_outside": c.lead_counsel_outside,
                "filed_date": c.filed_date.isoformat() + "Z" if c.filed_date else None,
                "commissioners_hearing_date": c.commissioners_hearing_date.isoformat() + "Z" if c.commissioners_hearing_date else None,
                "trial_date": c.trial_date.isoformat() + "Z" if c.trial_date else None,
                "created_at": c.created_at.isoformat() + "Z" if c.created_at else None,
            }
            for c in items
        ],
    }


@router.get("/{case_id}")
def get_litigation_case(
    case_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get full litigation case details."""
    authorize(persona, "litigation", Action.READ)
    
    case = db.query(models.LitigationCase).filter(models.LitigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="case_not_found")
    
    return {
        "id": case.id,
        "parcel_id": case.parcel_id,
        "project_id": case.project_id,
        "cause_number": case.cause_number,
        "court": case.court,
        "court_county": case.court_county,
        "is_quick_take": case.is_quick_take,
        "status": case.status.value if case.status else None,
        "lead_counsel_internal": case.lead_counsel_internal,
        "lead_counsel_internal_id": case.lead_counsel_internal_id,
        "lead_counsel_outside": case.lead_counsel_outside,
        "lead_counsel_outside_firm": case.lead_counsel_outside_firm,
        "filed_date": case.filed_date.isoformat() + "Z" if case.filed_date else None,
        "filing_document_id": case.filing_document_id,
        "commissioners_hearing_date": case.commissioners_hearing_date.isoformat() + "Z" if case.commissioners_hearing_date else None,
        "possession_order_date": case.possession_order_date.isoformat() + "Z" if case.possession_order_date else None,
        "trial_date": case.trial_date.isoformat() + "Z" if case.trial_date else None,
        "settlement_amount": float(case.settlement_amount) if case.settlement_amount else None,
        "final_judgment_amount": float(case.final_judgment_amount) if case.final_judgment_amount else None,
        "closed_date": case.closed_date.isoformat() + "Z" if case.closed_date else None,
        "metadata": case.metadata_json,
        "created_at": case.created_at.isoformat() + "Z" if case.created_at else None,
        "updated_at": case.updated_at.isoformat() + "Z" if case.updated_at else None,
    }


@router.put("/{case_id}")
def update_litigation_case(
    case_id: str,
    payload: LitigationCaseUpdate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Update litigation case."""
    authorize(persona, "litigation", Action.WRITE)
    
    case = db.query(models.LitigationCase).filter(models.LitigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="case_not_found")
    
    changes = {}
    old_status = case.status
    
    if payload.status is not None:
        try:
            new_status = LitigationStatus(payload.status)
            case.status = new_status
            changes["status"] = {"from": old_status.value if old_status else None, "to": payload.status}
            
            # Create status change record
            db.add(
                models.StatusChange(
                    id=str(uuid4()),
                    project_id=case.project_id,
                    parcel_id=case.parcel_id,
                    old_status=old_status.value if old_status else None,
                    new_status=payload.status,
                    reason=f"Status updated to {payload.status}",
                    actor_persona=persona,
                    hash=sha256_hex({
                        "case_id": case_id,
                        "old_status": old_status.value if old_status else None,
                        "new_status": payload.status,
                    }),
                )
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="invalid_status") from exc
    
    if payload.cause_number is not None:
        case.cause_number = payload.cause_number
        changes["cause_number"] = payload.cause_number
    
    if payload.court is not None:
        case.court = payload.court
        changes["court"] = payload.court
    
    if payload.court_county is not None:
        case.court_county = payload.court_county
        changes["court_county"] = payload.court_county
    
    if payload.is_quick_take is not None:
        case.is_quick_take = payload.is_quick_take
        changes["is_quick_take"] = payload.is_quick_take
    
    if payload.lead_counsel_internal is not None:
        case.lead_counsel_internal = payload.lead_counsel_internal
        changes["lead_counsel_internal"] = payload.lead_counsel_internal
    
    if payload.lead_counsel_internal_id is not None:
        case.lead_counsel_internal_id = payload.lead_counsel_internal_id
        changes["lead_counsel_internal_id"] = payload.lead_counsel_internal_id
    
    if payload.lead_counsel_outside is not None:
        case.lead_counsel_outside = payload.lead_counsel_outside
        changes["lead_counsel_outside"] = payload.lead_counsel_outside
    
    if payload.lead_counsel_outside_firm is not None:
        case.lead_counsel_outside_firm = payload.lead_counsel_outside_firm
        changes["lead_counsel_outside_firm"] = payload.lead_counsel_outside_firm
    
    # Date fields
    date_fields = [
        ("filed_date", payload.filed_date),
        ("commissioners_hearing_date", payload.commissioners_hearing_date),
        ("possession_order_date", payload.possession_order_date),
        ("trial_date", payload.trial_date),
        ("closed_date", payload.closed_date),
    ]
    
    for field_name, value in date_fields:
        if value is not None:
            try:
                setattr(case, field_name, datetime.fromisoformat(value.replace("Z", "")))
                changes[field_name] = value
            except Exception as exc:
                raise HTTPException(status_code=422, detail=f"invalid_{field_name}") from exc
    
    if payload.filing_document_id is not None:
        case.filing_document_id = payload.filing_document_id
        changes["filing_document_id"] = payload.filing_document_id
    
    if payload.settlement_amount is not None:
        case.settlement_amount = payload.settlement_amount
        changes["settlement_amount"] = payload.settlement_amount
    
    if payload.final_judgment_amount is not None:
        case.final_judgment_amount = payload.final_judgment_amount
        changes["final_judgment_amount"] = payload.final_judgment_amount
    
    case.updated_at = datetime.utcnow()
    
    if changes:
        db.add(
            models.AuditEvent(
                id=str(uuid4()),
                user_id=getattr(user, "id", None),
                actor_persona=persona,
                action="litigation.update",
                resource="litigation",
                payload={"case_id": case_id, "changes": changes},
                hash=sha256_hex({"case_id": case_id, "changes": changes}),
            )
        )
    
    db.commit()
    
    # Trigger workflow events based on status changes
    if payload.status is not None:
        try:
            from app.tasks.workflow import process_workflow_event
            event_type = None
            
            if payload.status == "filed":
                event_type = "litigation_filed"
            elif payload.status in ["settled", "closed"]:
                event_type = "case_closed"
            
            if event_type:
                process_workflow_event.delay(
                    event_type,
                    case.parcel_id,
                    {"case_id": case_id, "status": payload.status},
                )
        except Exception:
            pass  # Don't fail the request if workflow event fails
    
    return {"case_id": case_id, "updated": True, "changes": changes}


@router.get("/{case_id}/history")
def get_case_status_history(
    case_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get status change history for a litigation case."""
    authorize(persona, "litigation", Action.READ)
    
    case = db.query(models.LitigationCase).filter(models.LitigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="case_not_found")
    
    # Get status changes for this parcel (litigation-related)
    changes = (
        db.query(models.StatusChange)
        .filter(models.StatusChange.parcel_id == case.parcel_id)
        .order_by(models.StatusChange.occurred_at.desc())
        .all()
    )
    
    return {
        "case_id": case_id,
        "parcel_id": case.parcel_id,
        "current_status": case.status.value if case.status else None,
        "history": [
            {
                "id": c.id,
                "old_status": c.old_status,
                "new_status": c.new_status,
                "reason": c.reason,
                "actor_persona": c.actor_persona.value if c.actor_persona else None,
                "occurred_at": c.occurred_at.isoformat() + "Z" if c.occurred_at else None,
            }
            for c in changes
        ],
    }


# =============================================================================
# Analytics Endpoints
# =============================================================================


@router.get("/analytics/summary")
def get_litigation_summary(
    project_id: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get summary analytics for litigation cases."""
    authorize(persona, "litigation", Action.READ)
    
    query = db.query(models.LitigationCase)
    
    if project_id:
        query = query.filter(models.LitigationCase.project_id == project_id)
    
    cases = query.all()
    
    # Count by status
    status_counts = {}
    quick_take_count = 0
    standard_count = 0
    
    for case in cases:
        status = case.status.value if case.status else "unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
        
        if case.is_quick_take:
            quick_take_count += 1
        else:
            standard_count += 1
    
    return {
        "project_id": project_id,
        "total_cases": len(cases),
        "status_breakdown": status_counts,
        "quick_take_count": quick_take_count,
        "standard_count": standard_count,
    }
