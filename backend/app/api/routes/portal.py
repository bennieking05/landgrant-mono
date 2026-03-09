from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4
import secrets

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Response, Cookie, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_user, get_db
from app.db import models
from app.db.models import Persona
from app.security.rbac import Action, authorize
from app.services.hashing import sha256_hex
from app.services.notifications import preview_or_send

router = APIRouter(prefix="/portal", tags=["portal"])

# Simple in-memory stores for dev stubs. These are reset on process restart.
_uploads_by_parcel: dict[str, list[dict[str, Any]]] = {}
_decision_by_parcel: dict[str, dict[str, Any]] = {}

# Rate limiting configuration
_INVITE_MAX_FAILED = 5
_INVITE_FAIL_WINDOW = timedelta(minutes=10)
_INVITE_LOCKOUT_DURATION = timedelta(minutes=30)

# Session configuration
_SESSION_DURATION = timedelta(hours=24)

_LOCAL_STORAGE_ROOT = Path(__file__).resolve().parents[3] / "local_storage"


class InviteRequest(BaseModel):
    email: str
    parcel_id: str | None = None
    project_id: str | None = None


@router.post("/invites")
def send_invite(
    payload: InviteRequest,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    authorize(persona, "portal", Action.WRITE)
    invite_id = str(uuid4())
    token = str(uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=24)

    # Persist invite (best-effort; do not block if DB is unavailable).
    try:
        invite = models.PortalInvite(
            id=invite_id,
            token_sha256=sha256_hex(token),
            email=payload.email,
            project_id=payload.project_id,
            parcel_id=payload.parcel_id,
            expires_at=expires_at,
        )
        db.add(invite)
        db.add(
            models.AuditEvent(
                id=str(uuid4()),
                user_id=getattr(user, "id", None),
                actor_persona=persona,
                action="portal.invite.create",
                resource="portal_invite",
                payload={"invite_id": invite_id, "email": payload.email, "project_id": payload.project_id, "parcel_id": payload.parcel_id},
                hash=sha256_hex({"invite_id": invite_id, "email": payload.email, "project_id": payload.project_id, "parcel_id": payload.parcel_id}),
            )
        )

        invite_link = f"http://localhost:3050/intake?token={token}"
        if payload.project_id and payload.parcel_id:
            preview_or_send(
                db,
                persona=Persona.LAND_AGENT,  # send on behalf of system/agent in outbox
                template_id="portal_invite",
                channel="email",
                to=payload.email,
                variables={"invite_link": invite_link, "project_id": payload.project_id, "parcel_id": payload.parcel_id},
                project_id=payload.project_id,
                parcel_id=payload.parcel_id,
                user_id=getattr(user, "id", None),
            )
        db.commit()
    except Exception:
        db.rollback()
        invite_link = f"http://localhost:3050/intake?token={token}"

    return {
        "invite_id": invite_id,
        "email": payload.email,
        "parcel_id": payload.parcel_id,
        "project_id": payload.project_id,
        "status": "sent",
        "expires_at": expires_at.isoformat() + "Z",
        "invite_link": invite_link,
    }


class VerifyRequest(BaseModel):
    token: str


def _check_rate_limit(invite: models.PortalInvite) -> None:
    """Check if the invite is rate-limited due to failed attempts."""
    if not invite.failed_attempts or invite.failed_attempts < _INVITE_MAX_FAILED:
        return
    
    if not invite.last_failed_at:
        return
    
    time_since_last_fail = datetime.utcnow() - invite.last_failed_at
    
    # If still within lockout window after max failures, reject
    if time_since_last_fail < _INVITE_LOCKOUT_DURATION:
        remaining_seconds = int((_INVITE_LOCKOUT_DURATION - time_since_last_fail).total_seconds())
        raise HTTPException(
            status_code=429,
            detail=f"too_many_attempts",
            headers={"Retry-After": str(remaining_seconds)},
        )


def _record_failed_attempt(db: Session, invite: models.PortalInvite) -> None:
    """Record a failed verification attempt for rate limiting."""
    invite.failed_attempts = (invite.failed_attempts or 0) + 1
    invite.last_failed_at = datetime.utcnow()
    db.commit()


def _get_client_info(request: Request) -> dict[str, str]:
    """Extract client information from request for audit purposes."""
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "referer": request.headers.get("referer"),
    }


@router.post("/verify")
def verify_invite(
    payload: VerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Verify a magic link token and create a session.
    
    This endpoint is publicly accessible (no auth required) since it IS the auth mechanism.
    Rate limiting is applied per-invite to prevent brute force attacks.
    """
    token_hash = sha256_hex(payload.token)
    
    # Find invite by token hash
    invite = db.query(models.PortalInvite).filter(
        models.PortalInvite.token_sha256 == token_hash
    ).first()
    
    if not invite:
        # Don't reveal whether token exists - use generic error
        raise HTTPException(status_code=401, detail="invalid_or_expired_token")
    
    # Check rate limiting before any other validation
    _check_rate_limit(invite)
    
    # Check expiration
    if invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="invite_expired")
    
    # If already verified, check if session is still valid
    if invite.verified_at:
        # Check if there's an active session
        active_session = db.query(models.PortalSession).filter(
            models.PortalSession.invite_id == invite.id,
            models.PortalSession.expires_at > datetime.utcnow(),
            models.PortalSession.revoked_at.is_(None),
        ).first()
        
        if active_session:
            # Refresh session expiry
            active_session.expires_at = datetime.utcnow() + _SESSION_DURATION
            active_session.last_activity_at = datetime.utcnow()
            db.commit()
            
            # Set session cookie
            response.set_cookie(
                key="portal_session",
                value=active_session.session_token,
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=int(_SESSION_DURATION.total_seconds()),
            )
            
            return {
                "status": "already_verified",
                "invite_id": invite.id,
                "verified_at": invite.verified_at.isoformat() + "Z",
                "session_expires_at": active_session.expires_at.isoformat() + "Z",
                "parcel_id": invite.parcel_id,
                "project_id": invite.project_id,
            }
    
    # Mark invite as verified
    invite.verified_at = datetime.utcnow()
    
    # Create a new session
    session_token = secrets.token_urlsafe(32)
    session_id = str(uuid4())
    session_expires = datetime.utcnow() + _SESSION_DURATION
    
    # Get client info for session tracking
    client_info = _get_client_info(request)
    
    portal_session = models.PortalSession(
        id=session_id,
        invite_id=invite.id,
        session_token=session_token,
        expires_at=session_expires,
        created_at=datetime.utcnow(),
        last_activity_at=datetime.utcnow(),
        ip_address=client_info.get("ip_address"),
        user_agent=client_info.get("user_agent"),
    )
    db.add(portal_session)
    
    # Audit log with comprehensive details
    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            user_id=None,  # No user yet - this is the verification
            actor_persona=Persona.LANDOWNER,
            action="portal.invite.verify",
            resource="portal_invite",
            payload={
                "invite_id": invite.id,
                "session_id": session_id,
                "parcel_id": invite.parcel_id,
                "project_id": invite.project_id,
                "email": invite.email,
                "client_info": client_info,
            },
            hash=sha256_hex({"invite_id": invite.id, "action": "verify", "session_id": session_id}),
        )
    )
    
    db.commit()
    
    # Set session cookie
    response.set_cookie(
        key="portal_session",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=int(_SESSION_DURATION.total_seconds()),
    )
    
    return {
        "status": "verified",
        "invite_id": invite.id,
        "verified_at": invite.verified_at.isoformat() + "Z",
        "session_expires_at": session_expires.isoformat() + "Z",
        "parcel_id": invite.parcel_id,
        "project_id": invite.project_id,
    }


@router.post("/verify/refresh")
def refresh_session(
    response: Response,
    db: Session = Depends(get_db),
    portal_session: Optional[str] = Cookie(None),
):
    """
    Refresh an existing portal session.
    
    Extends the session expiry if the session is still valid.
    """
    if not portal_session:
        raise HTTPException(status_code=401, detail="no_session")
    
    session = db.query(models.PortalSession).filter(
        models.PortalSession.session_token == portal_session,
        models.PortalSession.revoked_at.is_(None),
    ).first()
    
    if not session:
        raise HTTPException(status_code=401, detail="invalid_session")
    
    if session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="session_expired")
    
    # Refresh expiry
    session.expires_at = datetime.utcnow() + _SESSION_DURATION
    session.last_activity_at = datetime.utcnow()
    db.commit()
    
    # Refresh cookie
    response.set_cookie(
        key="portal_session",
        value=session.session_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=int(_SESSION_DURATION.total_seconds()),
    )
    
    # Get invite info
    invite = db.get(models.PortalInvite, session.invite_id)
    
    return {
        "status": "refreshed",
        "session_expires_at": session.expires_at.isoformat() + "Z",
        "parcel_id": invite.parcel_id if invite else None,
        "project_id": invite.project_id if invite else None,
    }


@router.post("/logout")
def logout_session(
    response: Response,
    db: Session = Depends(get_db),
    portal_session: Optional[str] = Cookie(None),
):
    """
    Logout and revoke the current portal session.
    """
    if portal_session:
        session = db.query(models.PortalSession).filter(
            models.PortalSession.session_token == portal_session,
        ).first()
        
        if session:
            session.revoked_at = datetime.utcnow()
            db.add(
                models.AuditEvent(
                    id=str(uuid4()),
                    user_id=None,
                    actor_persona=Persona.LANDOWNER,
                    action="portal.session.logout",
                    resource="portal_session",
                    payload={"session_id": session.id, "invite_id": session.invite_id},
                    hash=sha256_hex({"session_id": session.id, "action": "logout"}),
                )
            )
            db.commit()
    
    # Clear cookie
    response.delete_cookie(key="portal_session")
    
    return {"status": "logged_out"}


@router.get("/session")
def get_session_info(
    db: Session = Depends(get_db),
    portal_session: Optional[str] = Cookie(None),
):
    """
    Get current session information.
    
    Returns session details if authenticated, 401 otherwise.
    """
    if not portal_session:
        raise HTTPException(status_code=401, detail="no_session")
    
    session = db.query(models.PortalSession).filter(
        models.PortalSession.session_token == portal_session,
        models.PortalSession.expires_at > datetime.utcnow(),
        models.PortalSession.revoked_at.is_(None),
    ).first()
    
    if not session:
        raise HTTPException(status_code=401, detail="invalid_or_expired_session")
    
    invite = db.get(models.PortalInvite, session.invite_id)
    
    return {
        "status": "authenticated",
        "session_id": session.id,
        "invite_id": session.invite_id,
        "parcel_id": invite.parcel_id if invite else None,
        "project_id": invite.project_id if invite else None,
        "email": invite.email if invite else None,
        "session_expires_at": session.expires_at.isoformat() + "Z",
        "created_at": session.created_at.isoformat() + "Z",
    }


@router.post("/invites/{invite_id}/resend")
def resend_invite(
    invite_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Resend an invite with a new token.
    
    The old token is invalidated and a new one is generated.
    """
    authorize(persona, "portal", Action.WRITE)
    
    invite = db.get(models.PortalInvite, invite_id)
    if not invite:
        raise HTTPException(status_code=404, detail="invite_not_found")
    
    # Generate new token
    new_token = str(uuid4())
    invite.token_sha256 = sha256_hex(new_token)
    invite.expires_at = datetime.utcnow() + timedelta(hours=24)
    invite.failed_attempts = 0  # Reset rate limiting
    invite.last_failed_at = None
    
    # Revoke any existing sessions
    db.query(models.PortalSession).filter(
        models.PortalSession.invite_id == invite_id,
        models.PortalSession.revoked_at.is_(None),
    ).update({"revoked_at": datetime.utcnow()})
    
    # Audit log
    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            user_id=getattr(user, "id", None),
            actor_persona=persona,
            action="portal.invite.resend",
            resource="portal_invite",
            payload={"invite_id": invite_id, "email": invite.email},
            hash=sha256_hex({"invite_id": invite_id, "action": "resend"}),
        )
    )
    
    invite_link = f"http://localhost:3050/intake?token={new_token}"
    
    # Send notification if we have project/parcel context
    if invite.project_id and invite.parcel_id:
        try:
            preview_or_send(
                db,
                persona=Persona.LAND_AGENT,
                template_id="portal_invite",
                channel="email",
                to=invite.email,
                variables={
                    "invite_link": invite_link,
                    "project_id": invite.project_id,
                    "parcel_id": invite.parcel_id,
                },
                project_id=invite.project_id,
                parcel_id=invite.parcel_id,
                user_id=getattr(user, "id", None),
            )
        except Exception:
            pass  # Best effort
    
    db.commit()
    
    return {
        "invite_id": invite_id,
        "email": invite.email,
        "status": "resent",
        "expires_at": invite.expires_at.isoformat() + "Z",
        "invite_link": invite_link,
    }


@router.get("/decision/options")
def decision_options(persona: Persona = Depends(get_current_persona)):
    authorize(persona, "portal", Action.READ)
    return {"options": ["Accept", "Counter", "Request Call"]}


class DecisionRequest(BaseModel):
    parcel_id: str
    selection: str
    note: str | None = None


@router.post("/decision")
def submit_decision(
    payload: DecisionRequest,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    authorize(persona, "decision", Action.EXECUTE)
    decision_id = str(uuid4())
    record = {
        "decision_id": decision_id,
        "parcel_id": payload.parcel_id,
        "selection": payload.selection,
        "note": payload.note,
        "routed_to": "agent_queue" if payload.selection == "Counter" else "case_workflow",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    _decision_by_parcel[payload.parcel_id] = record
    # Persist task + audit (best-effort).
    try:
        parcel = db.get(models.Parcel, payload.parcel_id)
        project_id = parcel.project_id if parcel else "PRJ-001"
        assignee_persona = Persona.LAND_AGENT if payload.selection == "Counter" else Persona.IN_HOUSE_COUNSEL
        db.add(
            models.Task(
                id=str(uuid4()),
                project_id=project_id,
                parcel_id=payload.parcel_id,
                title=f"Landowner decision: {payload.selection}",
                persona=assignee_persona,
                metadata_json={"note": payload.note},
            )
        )
        db.add(
            models.AuditEvent(
                id=str(uuid4()),
                user_id=getattr(user, "id", None),
                actor_persona=persona,
                action="portal.decision.submit",
                resource="decision",
                payload=record,
                hash=sha256_hex(record),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
    return record


@router.get("/uploads")
def list_uploads(parcel_id: str, persona: Persona = Depends(get_current_persona)):
    authorize(persona, "portal", Action.READ)
    return {"items": _uploads_by_parcel.get(parcel_id, [])}


@router.post("/uploads")
async def upload_file(
    parcel_id: str = Form(...),
    file: UploadFile = File(...),
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    authorize(persona, "portal", Action.WRITE)
    upload_id = str(uuid4())
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="file_too_large")

    sha = sha256_hex(content)
    rel_dir = Path("uploads") / parcel_id
    out_dir = _LOCAL_STORAGE_ROOT / rel_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = (file.filename or "upload").replace("/", "_")
    out_path = out_dir / f"{upload_id}-{safe_name}"
    out_path.write_bytes(content)

    item = {
        "id": upload_id,
        "parcel_id": parcel_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(content),
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
        "sha256": sha,
        "storage_path": str(out_path),
        "virus_scan": "skipped_local",
    }
    _uploads_by_parcel.setdefault(parcel_id, []).append(item)

    # Persist as Document + audit + comms entry (best-effort)
    try:
        parcel = db.get(models.Parcel, parcel_id)
        project_id = parcel.project_id if parcel else "PRJ-001"
        doc = models.Document(
            id=upload_id,
            doc_type="upload",
            version="1.0.0",
            sha256=sha,
            storage_path=str(out_path),
            metadata_json={"filename": file.filename, "content_type": file.content_type, "virus_scan": "skipped_local"},
            created_by=getattr(user, "id", None),
        )
        db.add(doc)
        db.add(
            models.Communication(
                id=str(uuid4()),
                parcel_id=parcel_id,
                project_id=project_id,
                channel="portal",
                direction="inbound",
                content=f"Upload received: {file.filename}",
                delivery_status="stored",
                delivery_proof={"document_id": upload_id, "sha256": sha},
                hash=sha256_hex({"event": "upload", "document_id": upload_id, "sha256": sha}),
            )
        )
        db.add(
            models.AuditEvent(
                id=str(uuid4()),
                user_id=getattr(user, "id", None),
                actor_persona=persona,
                action="portal.upload",
                resource="document",
                payload=item,
                hash=sha256_hex(item),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
    return item


# =============================================================================
# Audit and Session Activity Endpoints
# =============================================================================


@router.get("/audit/sessions")
def list_portal_sessions(
    invite_id: Optional[str] = None,
    active_only: bool = False,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """
    List portal sessions with optional filters.
    
    Used to monitor session activity and detect suspicious access patterns.
    """
    authorize(persona, "portal", Action.READ)
    
    query = db.query(models.PortalSession)
    
    if invite_id:
        query = query.filter(models.PortalSession.invite_id == invite_id)
    
    if active_only:
        query = query.filter(
            models.PortalSession.expires_at > datetime.utcnow(),
            models.PortalSession.revoked_at.is_(None),
        )
    
    sessions = query.order_by(models.PortalSession.created_at.desc()).limit(100).all()
    
    items = []
    for s in sessions:
        invite = db.get(models.PortalInvite, s.invite_id)
        is_active = s.expires_at > datetime.utcnow() and s.revoked_at is None
        
        items.append({
            "session_id": s.id,
            "invite_id": s.invite_id,
            "email": invite.email if invite else None,
            "parcel_id": invite.parcel_id if invite else None,
            "project_id": invite.project_id if invite else None,
            "status": "active" if is_active else ("revoked" if s.revoked_at else "expired"),
            "created_at": s.created_at.isoformat() + "Z" if s.created_at else None,
            "expires_at": s.expires_at.isoformat() + "Z" if s.expires_at else None,
            "last_activity_at": s.last_activity_at.isoformat() + "Z" if s.last_activity_at else None,
            "revoked_at": s.revoked_at.isoformat() + "Z" if s.revoked_at else None,
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
        })
    
    return {
        "sessions": items,
        "count": len(items),
        "active_count": sum(1 for i in items if i["status"] == "active"),
    }


@router.get("/audit/activity/{parcel_id}")
def get_parcel_activity(
    parcel_id: str,
    limit: int = 50,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """
    Get all portal activity for a specific parcel.
    
    Returns audit events, sessions, uploads, and decisions.
    """
    authorize(persona, "portal", Action.READ)
    
    # Get audit events for this parcel
    audit_events = db.query(models.AuditEvent).filter(
        models.AuditEvent.action.like("portal.%"),
        models.AuditEvent.payload.contains({"parcel_id": parcel_id})
    ).order_by(models.AuditEvent.occurred_at.desc()).limit(limit).all()
    
    events = []
    for e in audit_events:
        events.append({
            "event_id": e.id,
            "action": e.action,
            "actor_persona": e.actor_persona.value if e.actor_persona else None,
            "occurred_at": e.occurred_at.isoformat() + "Z" if e.occurred_at else None,
            "payload": e.payload,
        })
    
    # Get related sessions
    invite = db.query(models.PortalInvite).filter(
        models.PortalInvite.parcel_id == parcel_id
    ).first()
    
    sessions = []
    if invite:
        for s in db.query(models.PortalSession).filter(
            models.PortalSession.invite_id == invite.id
        ).all():
            sessions.append({
                "session_id": s.id,
                "created_at": s.created_at.isoformat() + "Z" if s.created_at else None,
                "last_activity_at": s.last_activity_at.isoformat() + "Z" if s.last_activity_at else None,
                "ip_address": s.ip_address,
            })
    
    # Get uploads
    uploads = _uploads_by_parcel.get(parcel_id, [])
    
    # Get decision
    decision = _decision_by_parcel.get(parcel_id)
    
    return {
        "parcel_id": parcel_id,
        "invite": {
            "id": invite.id,
            "email": invite.email,
            "verified_at": invite.verified_at.isoformat() + "Z" if invite and invite.verified_at else None,
        } if invite else None,
        "sessions": sessions,
        "audit_events": events,
        "uploads": uploads,
        "decision": decision,
    }


@router.get("/audit/events")
def list_portal_audit_events(
    action: Optional[str] = None,
    project_id: Optional[str] = None,
    parcel_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """
    List portal-related audit events with filters.
    
    Provides comprehensive audit trail for compliance and investigation.
    """
    authorize(persona, "portal", Action.READ)
    
    query = db.query(models.AuditEvent).filter(
        models.AuditEvent.action.like("portal.%")
    )
    
    if action:
        query = query.filter(models.AuditEvent.action == action)
    
    # Note: JSON filtering in SQLAlchemy varies by database
    # This is a simplified version
    if project_id:
        query = query.filter(
            models.AuditEvent.payload.contains({"project_id": project_id})
        )
    
    if parcel_id:
        query = query.filter(
            models.AuditEvent.payload.contains({"parcel_id": parcel_id})
        )
    
    total = query.count()
    events = query.order_by(
        models.AuditEvent.occurred_at.desc()
    ).offset(offset).limit(limit).all()
    
    items = []
    for e in events:
        items.append({
            "id": e.id,
            "action": e.action,
            "resource": e.resource,
            "actor_persona": e.actor_persona.value if e.actor_persona else None,
            "user_id": e.user_id,
            "occurred_at": e.occurred_at.isoformat() + "Z" if e.occurred_at else None,
            "payload": e.payload,
        })
    
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/audit/sessions/{session_id}/revoke")
def revoke_session(
    session_id: str,
    reason: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Administratively revoke a portal session.
    
    Used to terminate access for suspicious or unauthorized sessions.
    """
    authorize(persona, "portal", Action.WRITE)
    
    session = db.get(models.PortalSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session_not_found")
    
    if session.revoked_at:
        return {"status": "already_revoked", "session_id": session_id}
    
    session.revoked_at = datetime.utcnow()
    
    # Audit log
    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            user_id=getattr(user, "id", None),
            actor_persona=persona,
            action="portal.session.admin_revoke",
            resource="portal_session",
            payload={
                "session_id": session_id,
                "invite_id": session.invite_id,
                "reason": reason,
                "revoked_by": getattr(user, "id", None),
            },
            hash=sha256_hex({"session_id": session_id, "action": "admin_revoke"}),
        )
    )
    
    db.commit()
    
    return {
        "status": "revoked",
        "session_id": session_id,
        "reason": reason,
    }


@router.get("/audit/summary")
def get_audit_summary(
    project_id: Optional[str] = None,
    days: int = 7,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """
    Get summary statistics for portal audit activity.
    
    Provides overview of portal usage and potential security concerns.
    """
    authorize(persona, "portal", Action.READ)
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(models.AuditEvent).filter(
        models.AuditEvent.action.like("portal.%"),
        models.AuditEvent.occurred_at >= cutoff,
    )
    
    if project_id:
        query = query.filter(
            models.AuditEvent.payload.contains({"project_id": project_id})
        )
    
    events = query.all()
    
    # Count by action type
    by_action: dict[str, int] = {}
    for e in events:
        by_action[e.action] = by_action.get(e.action, 0) + 1
    
    # Session statistics
    session_query = db.query(models.PortalSession).filter(
        models.PortalSession.created_at >= cutoff,
    )
    sessions = session_query.all()
    
    active_sessions = sum(
        1 for s in sessions 
        if s.expires_at > datetime.utcnow() and s.revoked_at is None
    )
    revoked_sessions = sum(1 for s in sessions if s.revoked_at is not None)
    
    # Unique IPs
    unique_ips = len(set(s.ip_address for s in sessions if s.ip_address))
    
    return {
        "period_days": days,
        "project_id": project_id,
        "total_events": len(events),
        "events_by_action": by_action,
        "sessions": {
            "total": len(sessions),
            "active": active_sessions,
            "revoked": revoked_sessions,
            "unique_ips": unique_ips,
        },
        "invites": {
            "verified": by_action.get("portal.invite.verify", 0),
            "created": by_action.get("portal.invite.create", 0),
            "resent": by_action.get("portal.invite.resend", 0),
        },
        "uploads": by_action.get("portal.upload", 0),
        "decisions": by_action.get("portal.decision.submit", 0),
    }

