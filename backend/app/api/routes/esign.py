"""
E-Sign Integration API Routes.

Provides endpoints for initiating document signing, handling webhooks,
and checking signature status. Supports DocuSign integration with
fallback stub mode for development.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_user, get_db
from app.core.config import get_settings
from app.db import models
from app.db.models import Persona
from app.security.rbac import Action, authorize
from app.services.hashing import sha256_hex

router = APIRouter(prefix="/esign", tags=["esign"])

settings = get_settings()


class EsignStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    DELIVERED = "delivered"
    SIGNED = "signed"
    COMPLETED = "completed"
    DECLINED = "declined"
    VOIDED = "voided"
    EXPIRED = "expired"


class SignerInfo(BaseModel):
    email: str
    name: str
    role: str = "signer"  # signer, witness, cc
    routing_order: int = 1


class InitiateRequest(BaseModel):
    document_id: str
    parcel_id: str
    project_id: str
    signers: list[SignerInfo]
    subject: str = "Document Ready for Signature"
    message: Optional[str] = None
    return_url: Optional[str] = None
    expiration_days: int = 30


class InitiateResponse(BaseModel):
    envelope_id: str
    status: str
    signing_urls: dict[str, str]  # email -> signing URL
    created_at: str


class StatusResponse(BaseModel):
    envelope_id: str
    status: str
    document_id: str
    parcel_id: str
    signers: list[dict[str, Any]]
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None


class WebhookPayload(BaseModel):
    event: str
    envelope_id: str
    status: Optional[str] = None
    signer_email: Optional[str] = None
    timestamp: Optional[str] = None
    data: Optional[dict[str, Any]] = None


# In-memory store for development mode (replaced by DB in production)
_envelope_store: dict[str, dict[str, Any]] = {}


def _create_stub_envelope(
    document_id: str,
    parcel_id: str,
    project_id: str,
    signers: list[SignerInfo],
    subject: str,
    message: Optional[str],
    return_url: Optional[str],
) -> dict[str, Any]:
    """Create a stub envelope for development/testing."""
    envelope_id = f"ENV-{uuid4().hex[:12].upper()}"
    now = datetime.utcnow()
    
    signing_urls = {}
    signer_statuses = []
    for i, signer in enumerate(signers):
        # Generate unique signing URL for each signer
        token = uuid4().hex
        base_url = return_url or "http://localhost:3050/sign"
        signing_urls[signer.email] = f"{base_url}?envelope={envelope_id}&token={token}"
        signer_statuses.append({
            "email": signer.email,
            "name": signer.name,
            "role": signer.role,
            "routing_order": signer.routing_order,
            "status": "sent",
            "signed_at": None,
            "declined_at": None,
        })
    
    envelope = {
        "envelope_id": envelope_id,
        "document_id": document_id,
        "parcel_id": parcel_id,
        "project_id": project_id,
        "subject": subject,
        "message": message,
        "status": EsignStatus.SENT.value,
        "signers": signer_statuses,
        "signing_urls": signing_urls,
        "return_url": return_url,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
        "completed_at": None,
        "voided_at": None,
        "provider": "stub",
    }
    
    _envelope_store[envelope_id] = envelope
    return envelope


async def _create_docusign_envelope(
    document_id: str,
    parcel_id: str,
    project_id: str,
    signers: list[SignerInfo],
    subject: str,
    message: Optional[str],
    return_url: Optional[str],
    db: Session,
) -> dict[str, Any]:
    """
    Create a DocuSign envelope.
    
    In production, this would use the DocuSign API to:
    1. Create an envelope with the document
    2. Add signers with their tabs (signature locations)
    3. Send for signing
    4. Return signing URLs
    """
    # TODO: Implement actual DocuSign API integration
    # For now, fall back to stub mode
    return _create_stub_envelope(
        document_id, parcel_id, project_id, signers, subject, message, return_url
    )


@router.post("/initiate", response_model=InitiateResponse)
async def initiate_signing(
    payload: InitiateRequest,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Initiate document signing with specified signers.
    
    Creates an envelope and sends signing requests to all signers.
    Returns signing URLs that can be embedded or sent to signers.
    """
    authorize(persona, "esign", Action.WRITE)
    
    if len(payload.signers) == 0:
        raise HTTPException(status_code=400, detail="At least one signer is required")
    
    # Verify document exists
    document = db.get(models.Document, payload.document_id)
    if not document:
        raise HTTPException(status_code=404, detail="document_not_found")
    
    # Create envelope (DocuSign or stub)
    if settings.docusign_configured:
        envelope = await _create_docusign_envelope(
            document_id=payload.document_id,
            parcel_id=payload.parcel_id,
            project_id=payload.project_id,
            signers=payload.signers,
            subject=payload.subject,
            message=payload.message,
            return_url=payload.return_url,
            db=db,
        )
    else:
        envelope = _create_stub_envelope(
            document_id=payload.document_id,
            parcel_id=payload.parcel_id,
            project_id=payload.project_id,
            signers=payload.signers,
            subject=payload.subject,
            message=payload.message,
            return_url=payload.return_url,
        )
    
    # Persist envelope record
    esign_record = models.EsignEnvelope(
        id=envelope["envelope_id"],
        document_id=payload.document_id,
        parcel_id=payload.parcel_id,
        project_id=payload.project_id,
        status=envelope["status"],
        provider="docusign" if settings.docusign_configured else "stub",
        provider_envelope_id=envelope["envelope_id"],
        signers_json=envelope["signers"],
        metadata_json={
            "subject": payload.subject,
            "message": payload.message,
            "return_url": payload.return_url,
        },
        created_by=getattr(user, "id", None),
    )
    db.add(esign_record)
    
    # Audit log
    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            user_id=getattr(user, "id", None),
            actor_persona=persona,
            action="esign.initiate",
            resource="esign_envelope",
            payload={
                "envelope_id": envelope["envelope_id"],
                "document_id": payload.document_id,
                "parcel_id": payload.parcel_id,
                "signer_emails": [s.email for s in payload.signers],
            },
            hash=sha256_hex({
                "envelope_id": envelope["envelope_id"],
                "action": "initiate",
            }),
        )
    )
    
    db.commit()
    
    return InitiateResponse(
        envelope_id=envelope["envelope_id"],
        status=envelope["status"],
        signing_urls=envelope["signing_urls"],
        created_at=envelope["created_at"],
    )


@router.get("/status/{envelope_id}", response_model=StatusResponse)
async def get_signing_status(
    envelope_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """
    Get the current status of a signing envelope.
    
    Returns detailed status including per-signer status.
    """
    authorize(persona, "esign", Action.READ)
    
    # Check DB first
    esign_record = db.get(models.EsignEnvelope, envelope_id)
    if esign_record:
        return StatusResponse(
            envelope_id=esign_record.id,
            status=esign_record.status,
            document_id=esign_record.document_id,
            parcel_id=esign_record.parcel_id,
            signers=esign_record.signers_json or [],
            created_at=esign_record.created_at.isoformat() + "Z" if esign_record.created_at else "",
            updated_at=esign_record.updated_at.isoformat() + "Z" if esign_record.updated_at else "",
            completed_at=esign_record.completed_at.isoformat() + "Z" if esign_record.completed_at else None,
        )
    
    # Fall back to in-memory store (dev mode)
    if envelope_id in _envelope_store:
        envelope = _envelope_store[envelope_id]
        return StatusResponse(
            envelope_id=envelope["envelope_id"],
            status=envelope["status"],
            document_id=envelope["document_id"],
            parcel_id=envelope["parcel_id"],
            signers=envelope["signers"],
            created_at=envelope["created_at"],
            updated_at=envelope["updated_at"],
            completed_at=envelope.get("completed_at"),
        )
    
    raise HTTPException(status_code=404, detail="envelope_not_found")


@router.post("/webhook")
async def handle_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Handle e-sign provider webhooks.
    
    Updates envelope status based on provider notifications.
    Supports DocuSign Connect webhooks and stub mode callbacks.
    """
    # Parse webhook payload
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_json")
    
    # Extract envelope ID and event type
    envelope_id = body.get("envelope_id") or body.get("envelopeId")
    event = body.get("event") or body.get("status")
    
    if not envelope_id:
        raise HTTPException(status_code=400, detail="missing_envelope_id")
    
    # Update in database
    esign_record = db.get(models.EsignEnvelope, envelope_id)
    if esign_record:
        old_status = esign_record.status
        
        # Map webhook event to status
        status_map = {
            "sent": EsignStatus.SENT.value,
            "delivered": EsignStatus.DELIVERED.value,
            "signed": EsignStatus.SIGNED.value,
            "completed": EsignStatus.COMPLETED.value,
            "declined": EsignStatus.DECLINED.value,
            "voided": EsignStatus.VOIDED.value,
            "expired": EsignStatus.EXPIRED.value,
        }
        new_status = status_map.get(event.lower() if event else "", esign_record.status)
        
        esign_record.status = new_status
        esign_record.updated_at = datetime.utcnow()
        
        if new_status == EsignStatus.COMPLETED.value:
            esign_record.completed_at = datetime.utcnow()
        
        # Update signer status if provided
        signer_email = body.get("signer_email") or body.get("signerEmail")
        if signer_email and esign_record.signers_json:
            for signer in esign_record.signers_json:
                if signer.get("email") == signer_email:
                    signer["status"] = event.lower() if event else signer["status"]
                    if event and event.lower() == "signed":
                        signer["signed_at"] = datetime.utcnow().isoformat() + "Z"
                    elif event and event.lower() == "declined":
                        signer["declined_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Audit log
        db.add(
            models.AuditEvent(
                id=str(uuid4()),
                user_id=None,
                actor_persona=Persona.SYSTEM,
                action="esign.webhook",
                resource="esign_envelope",
                payload={
                    "envelope_id": envelope_id,
                    "event": event,
                    "old_status": old_status,
                    "new_status": new_status,
                    "signer_email": signer_email,
                },
                hash=sha256_hex({
                    "envelope_id": envelope_id,
                    "event": event,
                    "timestamp": datetime.utcnow().isoformat(),
                }),
            )
        )
        
        db.commit()
    
    # Also update in-memory store for dev mode
    if envelope_id in _envelope_store:
        envelope = _envelope_store[envelope_id]
        envelope["status"] = event.lower() if event else envelope["status"]
        envelope["updated_at"] = datetime.utcnow().isoformat() + "Z"
        if event and event.lower() == "completed":
            envelope["completed_at"] = datetime.utcnow().isoformat() + "Z"
    
    return {"status": "received", "envelope_id": envelope_id}


@router.post("/void/{envelope_id}")
async def void_envelope(
    envelope_id: str,
    reason: str = "Voided by user",
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Void an existing envelope.
    
    Cancels the signing request. Cannot void completed envelopes.
    """
    authorize(persona, "esign", Action.WRITE)
    
    esign_record = db.get(models.EsignEnvelope, envelope_id)
    if not esign_record:
        if envelope_id not in _envelope_store:
            raise HTTPException(status_code=404, detail="envelope_not_found")
    
    # Check if envelope can be voided
    current_status = esign_record.status if esign_record else _envelope_store[envelope_id]["status"]
    if current_status in [EsignStatus.COMPLETED.value, EsignStatus.VOIDED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot void envelope with status: {current_status}"
        )
    
    # Update status
    if esign_record:
        esign_record.status = EsignStatus.VOIDED.value
        esign_record.updated_at = datetime.utcnow()
        esign_record.metadata_json = esign_record.metadata_json or {}
        esign_record.metadata_json["void_reason"] = reason
        
        db.add(
            models.AuditEvent(
                id=str(uuid4()),
                user_id=getattr(user, "id", None),
                actor_persona=persona,
                action="esign.void",
                resource="esign_envelope",
                payload={
                    "envelope_id": envelope_id,
                    "reason": reason,
                },
                hash=sha256_hex({
                    "envelope_id": envelope_id,
                    "action": "void",
                }),
            )
        )
        db.commit()
    
    if envelope_id in _envelope_store:
        _envelope_store[envelope_id]["status"] = EsignStatus.VOIDED.value
        _envelope_store[envelope_id]["voided_at"] = datetime.utcnow().isoformat() + "Z"
    
    return {"status": "voided", "envelope_id": envelope_id}


@router.post("/resend/{envelope_id}")
async def resend_envelope(
    envelope_id: str,
    signer_email: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Resend signing notification to signers.
    
    Can resend to all signers or a specific signer by email.
    """
    authorize(persona, "esign", Action.WRITE)
    
    esign_record = db.get(models.EsignEnvelope, envelope_id)
    if not esign_record and envelope_id not in _envelope_store:
        raise HTTPException(status_code=404, detail="envelope_not_found")
    
    # Check status allows resend
    current_status = esign_record.status if esign_record else _envelope_store[envelope_id]["status"]
    if current_status not in [EsignStatus.SENT.value, EsignStatus.DELIVERED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resend envelope with status: {current_status}"
        )
    
    # Audit log
    if esign_record:
        db.add(
            models.AuditEvent(
                id=str(uuid4()),
                user_id=getattr(user, "id", None),
                actor_persona=persona,
                action="esign.resend",
                resource="esign_envelope",
                payload={
                    "envelope_id": envelope_id,
                    "signer_email": signer_email,
                },
                hash=sha256_hex({
                    "envelope_id": envelope_id,
                    "action": "resend",
                }),
            )
        )
        db.commit()
    
    return {
        "status": "resent",
        "envelope_id": envelope_id,
        "signer_email": signer_email or "all",
    }


@router.get("/list")
async def list_envelopes(
    parcel_id: Optional[str] = None,
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """
    List signing envelopes with optional filters.
    """
    authorize(persona, "esign", Action.READ)
    
    query = db.query(models.EsignEnvelope)
    
    if parcel_id:
        query = query.filter(models.EsignEnvelope.parcel_id == parcel_id)
    if project_id:
        query = query.filter(models.EsignEnvelope.project_id == project_id)
    if status:
        query = query.filter(models.EsignEnvelope.status == status)
    
    envelopes = query.order_by(models.EsignEnvelope.created_at.desc()).limit(100).all()
    
    return {
        "items": [
            {
                "envelope_id": e.id,
                "document_id": e.document_id,
                "parcel_id": e.parcel_id,
                "project_id": e.project_id,
                "status": e.status,
                "provider": e.provider,
                "created_at": e.created_at.isoformat() + "Z" if e.created_at else None,
                "completed_at": e.completed_at.isoformat() + "Z" if e.completed_at else None,
            }
            for e in envelopes
        ],
        "count": len(envelopes),
    }


# Dev/test endpoint to simulate signer completing signature
@router.post("/dev/simulate-sign/{envelope_id}")
async def simulate_signing(
    envelope_id: str,
    signer_email: str,
    db: Session = Depends(get_db),
):
    """
    DEV ONLY: Simulate a signer completing their signature.
    
    This endpoint is only available in non-production environments.
    """
    if settings.environment == "production":
        raise HTTPException(status_code=403, detail="Not available in production")
    
    # Trigger webhook-like update
    if envelope_id in _envelope_store:
        envelope = _envelope_store[envelope_id]
        for signer in envelope["signers"]:
            if signer["email"] == signer_email:
                signer["status"] = "signed"
                signer["signed_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Check if all signers have signed
        all_signed = all(s["status"] == "signed" for s in envelope["signers"])
        if all_signed:
            envelope["status"] = EsignStatus.COMPLETED.value
            envelope["completed_at"] = datetime.utcnow().isoformat() + "Z"
        
        envelope["updated_at"] = datetime.utcnow().isoformat() + "Z"
    
    # Also update DB record if exists
    esign_record = db.get(models.EsignEnvelope, envelope_id)
    if esign_record and esign_record.signers_json:
        for signer in esign_record.signers_json:
            if signer["email"] == signer_email:
                signer["status"] = "signed"
                signer["signed_at"] = datetime.utcnow().isoformat() + "Z"
        
        all_signed = all(s.get("status") == "signed" for s in esign_record.signers_json)
        if all_signed:
            esign_record.status = EsignStatus.COMPLETED.value
            esign_record.completed_at = datetime.utcnow()
        
        esign_record.updated_at = datetime.utcnow()
        db.commit()
    
    return {"status": "simulated", "envelope_id": envelope_id, "signer_email": signer_email}
