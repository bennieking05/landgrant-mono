"""Payment Ledger and Offers API.

Agreement Reference: Section 3.2(f) - Payment ledger (status-only, no valuation or dollar amounts)

NOTE: Per Agreement Section 3.3(a), this module stores offer/payment amounts as data fields
but does NOT perform any valuation, appraisal, or compensation computations.
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
from app.db.models import Persona, OfferType, OfferStatus, PaymentStatus
from app.security.rbac import Action, authorize
from app.services.hashing import sha256_hex


router = APIRouter(prefix="/offers", tags=["offers"])


# =============================================================================
# Request/Response Models
# =============================================================================


class OfferCreate(BaseModel):
    """Create a new offer."""
    parcel_id: str
    project_id: str
    offer_type: str  # initial, counteroffer, final, settlement
    amount: Optional[float] = None  # Stored as data, NOT computed
    terms: Optional[dict] = None
    terms_summary: Optional[str] = None
    response_due_date: Optional[str] = None  # ISO date
    offer_letter_id: Optional[str] = None


class OfferUpdate(BaseModel):
    """Update an offer status."""
    status: Optional[str] = None
    response_date: Optional[str] = None
    response_notes: Optional[str] = None
    response_document_id: Optional[str] = None


class CounterOfferCreate(BaseModel):
    """Record a counteroffer."""
    amount: Optional[float] = None
    terms: Optional[dict] = None
    terms_summary: Optional[str] = None
    source: str = "landowner"  # landowner or internal
    response_due_date: Optional[str] = None
    landowner_party_id: Optional[str] = None


class PaymentStatusUpdate(BaseModel):
    """Update payment ledger status."""
    status: str  # PaymentStatus enum value
    settlement_amount: Optional[float] = None
    settlement_date: Optional[str] = None
    payment_instruction_date: Optional[str] = None
    payment_cleared_date: Optional[str] = None
    payment_reference: Optional[str] = None


# =============================================================================
# Offer Endpoints
# =============================================================================


@router.post("")
def create_offer(
    payload: OfferCreate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Create a new offer for a parcel."""
    authorize(persona, "offer", Action.WRITE)
    
    try:
        offer_type = OfferType(payload.offer_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid_offer_type") from exc
    
    # Parse response due date if provided
    response_due = None
    if payload.response_due_date:
        try:
            response_due = datetime.fromisoformat(payload.response_due_date.replace("Z", ""))
        except Exception as exc:
            raise HTTPException(status_code=422, detail="invalid_response_due_date") from exc
    
    # Determine offer number
    existing_offers = (
        db.query(models.Offer)
        .filter(models.Offer.parcel_id == payload.parcel_id)
        .count()
    )
    
    offer_id = str(uuid4())
    offer = models.Offer(
        id=offer_id,
        parcel_id=payload.parcel_id,
        project_id=payload.project_id,
        offer_type=offer_type,
        offer_number=existing_offers + 1,
        amount=payload.amount,
        terms=payload.terms or {},
        terms_summary=payload.terms_summary,
        status=OfferStatus.DRAFT,
        response_due_date=response_due,
        offer_letter_id=payload.offer_letter_id,
        source="internal",
        created_by=getattr(user, "id", None),
    )
    db.add(offer)
    
    # Create or update payment ledger
    ledger = (
        db.query(models.PaymentLedger)
        .filter(models.PaymentLedger.parcel_id == payload.parcel_id)
        .first()
    )
    
    if not ledger:
        ledger = models.PaymentLedger(
            id=str(uuid4()),
            parcel_id=payload.parcel_id,
            project_id=payload.project_id,
            status=PaymentStatus.NOT_STARTED,
            current_offer_id=offer_id,
            status_history=[],
        )
        db.add(ledger)
    else:
        ledger.current_offer_id = offer_id
    
    # Audit event
    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            user_id=getattr(user, "id", None),
            actor_persona=persona,
            action="offer.create",
            resource="offer",
            payload={
                "offer_id": offer_id,
                "parcel_id": payload.parcel_id,
                "offer_type": payload.offer_type,
                "offer_number": existing_offers + 1,
            },
            hash=sha256_hex({
                "offer_id": offer_id,
                "parcel_id": payload.parcel_id,
            }),
        )
    )
    db.commit()
    
    return {"offer_id": offer_id, "offer_number": existing_offers + 1}


@router.get("")
def list_offers(
    parcel_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """List all offers for a parcel."""
    authorize(persona, "offer", Action.READ)
    
    items = (
        db.query(models.Offer)
        .filter(models.Offer.parcel_id == parcel_id)
        .order_by(models.Offer.offer_number.asc())
        .all()
    )
    
    return {
        "parcel_id": parcel_id,
        "count": len(items),
        "items": [
            {
                "id": o.id,
                "offer_type": o.offer_type.value if o.offer_type else None,
                "offer_number": o.offer_number,
                "amount": float(o.amount) if o.amount else None,
                "terms": o.terms,
                "terms_summary": o.terms_summary,
                "status": o.status.value if o.status else None,
                "source": o.source,
                "created_date": o.created_date.isoformat() + "Z" if o.created_date else None,
                "sent_date": o.sent_date.isoformat() + "Z" if o.sent_date else None,
                "response_due_date": o.response_due_date.isoformat() + "Z" if o.response_due_date else None,
                "response_date": o.response_date.isoformat() + "Z" if o.response_date else None,
                "response_notes": o.response_notes,
                "previous_offer_id": o.previous_offer_id,
            }
            for o in items
        ],
    }


@router.get("/{offer_id}")
def get_offer(
    offer_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get a specific offer by ID."""
    authorize(persona, "offer", Action.READ)
    
    offer = db.query(models.Offer).filter(models.Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="offer_not_found")
    
    return {
        "id": offer.id,
        "parcel_id": offer.parcel_id,
        "project_id": offer.project_id,
        "offer_type": offer.offer_type.value if offer.offer_type else None,
        "offer_number": offer.offer_number,
        "amount": float(offer.amount) if offer.amount else None,
        "terms": offer.terms,
        "terms_summary": offer.terms_summary,
        "status": offer.status.value if offer.status else None,
        "source": offer.source,
        "landowner_party_id": offer.landowner_party_id,
        "created_date": offer.created_date.isoformat() + "Z" if offer.created_date else None,
        "sent_date": offer.sent_date.isoformat() + "Z" if offer.sent_date else None,
        "response_due_date": offer.response_due_date.isoformat() + "Z" if offer.response_due_date else None,
        "response_date": offer.response_date.isoformat() + "Z" if offer.response_date else None,
        "response_notes": offer.response_notes,
        "offer_letter_id": offer.offer_letter_id,
        "response_document_id": offer.response_document_id,
        "previous_offer_id": offer.previous_offer_id,
        "created_at": offer.created_at.isoformat() + "Z" if offer.created_at else None,
    }


@router.put("/{offer_id}")
def update_offer(
    offer_id: str,
    payload: OfferUpdate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Update offer status."""
    authorize(persona, "offer", Action.WRITE)
    
    offer = db.query(models.Offer).filter(models.Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="offer_not_found")
    
    changes = {}
    
    if payload.status is not None:
        try:
            offer.status = OfferStatus(payload.status)
            changes["status"] = payload.status
            
            # Update sent_date if status changed to sent
            if payload.status == "sent" and not offer.sent_date:
                offer.sent_date = datetime.utcnow()
                changes["sent_date"] = offer.sent_date.isoformat()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="invalid_status") from exc
    
    if payload.response_date is not None:
        try:
            offer.response_date = datetime.fromisoformat(payload.response_date.replace("Z", ""))
            changes["response_date"] = payload.response_date
        except Exception as exc:
            raise HTTPException(status_code=422, detail="invalid_response_date") from exc
    
    if payload.response_notes is not None:
        offer.response_notes = payload.response_notes
        changes["response_notes"] = payload.response_notes
    
    if payload.response_document_id is not None:
        offer.response_document_id = payload.response_document_id
        changes["response_document_id"] = payload.response_document_id
    
    offer.updated_at = datetime.utcnow()
    
    # Audit
    if changes:
        db.add(
            models.AuditEvent(
                id=str(uuid4()),
                user_id=getattr(user, "id", None),
                actor_persona=persona,
                action="offer.update",
                resource="offer",
                payload={"offer_id": offer_id, "changes": changes},
                hash=sha256_hex({"offer_id": offer_id, "changes": changes}),
            )
        )
    
    db.commit()
    
    # Trigger workflow events based on status changes
    if payload.status is not None:
        try:
            from app.tasks.workflow import process_workflow_event
            event_type = None
            
            if payload.status == "sent":
                event_type = "offer_sent"
            elif payload.status == "accepted":
                event_type = "offer_accepted"
            elif payload.status == "rejected":
                event_type = "offer_rejected"
            
            if event_type:
                process_workflow_event.delay(
                    event_type,
                    offer.parcel_id,
                    {"offer_id": offer_id, "status": payload.status},
                )
        except Exception:
            pass  # Don't fail the request if workflow event fails
    
    return {"offer_id": offer_id, "updated": True, "changes": changes}


@router.post("/{offer_id}/counter")
def create_counteroffer(
    offer_id: str,
    payload: CounterOfferCreate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Record a counteroffer in response to an existing offer."""
    authorize(persona, "offer", Action.WRITE)
    
    # Get the original offer
    original = db.query(models.Offer).filter(models.Offer.id == offer_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="original_offer_not_found")
    
    # Mark original as superseded
    original.status = OfferStatus.SUPERSEDED
    
    # Parse response due date if provided
    response_due = None
    if payload.response_due_date:
        try:
            response_due = datetime.fromisoformat(payload.response_due_date.replace("Z", ""))
        except Exception as exc:
            raise HTTPException(status_code=422, detail="invalid_response_due_date") from exc
    
    # Create counteroffer
    counter_id = str(uuid4())
    counter = models.Offer(
        id=counter_id,
        parcel_id=original.parcel_id,
        project_id=original.project_id,
        offer_type=OfferType.COUNTEROFFER,
        offer_number=original.offer_number + 1,
        previous_offer_id=offer_id,
        amount=payload.amount,
        terms=payload.terms or {},
        terms_summary=payload.terms_summary,
        status=OfferStatus.RECEIVED if payload.source == "landowner" else OfferStatus.DRAFT,
        source=payload.source,
        landowner_party_id=payload.landowner_party_id,
        response_due_date=response_due,
        created_by=getattr(user, "id", None),
    )
    db.add(counter)
    
    # Update payment ledger
    ledger = (
        db.query(models.PaymentLedger)
        .filter(models.PaymentLedger.parcel_id == original.parcel_id)
        .first()
    )
    
    if ledger:
        ledger.current_offer_id = counter_id
        if payload.source == "landowner":
            old_status = ledger.status
            ledger.status = PaymentStatus.COUNTEROFFER_RECEIVED
            ledger.status_history = ledger.status_history or []
            ledger.status_history.append({
                "from": old_status.value if old_status else None,
                "to": PaymentStatus.COUNTEROFFER_RECEIVED.value,
                "timestamp": datetime.utcnow().isoformat(),
            })
    
    # Audit
    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            user_id=getattr(user, "id", None),
            actor_persona=persona,
            action="offer.counteroffer",
            resource="offer",
            payload={
                "counter_id": counter_id,
                "original_offer_id": offer_id,
                "parcel_id": original.parcel_id,
                "source": payload.source,
            },
            hash=sha256_hex({
                "counter_id": counter_id,
                "original_offer_id": offer_id,
            }),
        )
    )
    db.commit()
    
    return {
        "counter_id": counter_id,
        "original_offer_id": offer_id,
        "offer_number": counter.offer_number,
    }


# =============================================================================
# Payment Ledger Endpoints
# =============================================================================


payment_router = APIRouter(prefix="/payment-ledger", tags=["payment-ledger"])


@payment_router.get("/{parcel_id}")
def get_payment_ledger(
    parcel_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get payment ledger status for a parcel."""
    authorize(persona, "offer", Action.READ)
    
    ledger = (
        db.query(models.PaymentLedger)
        .filter(models.PaymentLedger.parcel_id == parcel_id)
        .first()
    )
    
    if not ledger:
        return {
            "parcel_id": parcel_id,
            "status": PaymentStatus.NOT_STARTED.value,
            "exists": False,
        }
    
    return {
        "parcel_id": parcel_id,
        "exists": True,
        "id": ledger.id,
        "project_id": ledger.project_id,
        "status": ledger.status.value if ledger.status else None,
        "current_offer_id": ledger.current_offer_id,
        "settlement_offer_id": ledger.settlement_offer_id,
        "settlement_amount": float(ledger.settlement_amount) if ledger.settlement_amount else None,
        "settlement_date": ledger.settlement_date.isoformat() + "Z" if ledger.settlement_date else None,
        "payment_instruction_date": ledger.payment_instruction_date.isoformat() + "Z" if ledger.payment_instruction_date else None,
        "payment_cleared_date": ledger.payment_cleared_date.isoformat() + "Z" if ledger.payment_cleared_date else None,
        "payment_reference": ledger.payment_reference,
        "status_history": ledger.status_history,
    }


@payment_router.put("/{parcel_id}")
def update_payment_ledger(
    parcel_id: str,
    payload: PaymentStatusUpdate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Update payment ledger status."""
    authorize(persona, "offer", Action.WRITE)
    
    ledger = (
        db.query(models.PaymentLedger)
        .filter(models.PaymentLedger.parcel_id == parcel_id)
        .first()
    )
    
    if not ledger:
        raise HTTPException(status_code=404, detail="ledger_not_found")
    
    changes = {}
    old_status = ledger.status
    
    try:
        new_status = PaymentStatus(payload.status)
        ledger.status = new_status
        changes["status"] = payload.status
        
        # Record status change in history
        ledger.status_history = ledger.status_history or []
        ledger.status_history.append({
            "from": old_status.value if old_status else None,
            "to": new_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": getattr(user, "id", None),
        })
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid_status") from exc
    
    if payload.settlement_amount is not None:
        ledger.settlement_amount = payload.settlement_amount
        changes["settlement_amount"] = payload.settlement_amount
    
    if payload.settlement_date is not None:
        try:
            ledger.settlement_date = datetime.fromisoformat(payload.settlement_date.replace("Z", ""))
            changes["settlement_date"] = payload.settlement_date
        except Exception as exc:
            raise HTTPException(status_code=422, detail="invalid_settlement_date") from exc
    
    if payload.payment_instruction_date is not None:
        try:
            ledger.payment_instruction_date = datetime.fromisoformat(payload.payment_instruction_date.replace("Z", ""))
            changes["payment_instruction_date"] = payload.payment_instruction_date
        except Exception as exc:
            raise HTTPException(status_code=422, detail="invalid_payment_instruction_date") from exc
    
    if payload.payment_cleared_date is not None:
        try:
            ledger.payment_cleared_date = datetime.fromisoformat(payload.payment_cleared_date.replace("Z", ""))
            changes["payment_cleared_date"] = payload.payment_cleared_date
        except Exception as exc:
            raise HTTPException(status_code=422, detail="invalid_payment_cleared_date") from exc
    
    if payload.payment_reference is not None:
        ledger.payment_reference = payload.payment_reference
        changes["payment_reference"] = payload.payment_reference
    
    ledger.updated_at = datetime.utcnow()
    
    # Audit
    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            user_id=getattr(user, "id", None),
            actor_persona=persona,
            action="payment_ledger.update",
            resource="offer",
            payload={"parcel_id": parcel_id, "changes": changes},
            hash=sha256_hex({"parcel_id": parcel_id, "changes": changes}),
        )
    )
    db.commit()
    
    return {"parcel_id": parcel_id, "updated": True, "changes": changes}


# Combine routers
router.include_router(payment_router)
