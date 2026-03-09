from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import models
from app.db.models import Persona
from app.services.hashing import sha256_hex


Channel = Literal["email", "sms"]


@dataclass(frozen=True)
class NotificationPreview:
    notification_id: str
    channel: Channel
    to: str
    subject: str | None
    body: str
    mode: str  # preview | send
    created_at: str
    communication_id: str | None
    audit_event_id: str | None


def _render_template(template_id: str, variables: dict[str, Any]) -> tuple[str | None, str]:
    """
    Minimal in-code templates for now.
    Later we can move this to templates/i18n + template library metadata.
    """
    if template_id == "portal_invite":
        invite_link = variables.get("invite_link", "")
        project_id = variables.get("project_id", "")
        parcel_id = variables.get("parcel_id", "")
        subject = "LandRight portal invite"
        body = f"You're invited to review your parcel. Project {project_id}, Parcel {parcel_id}. Link: {invite_link}"
        return subject, body
    if template_id == "decision_confirmation":
        selection = variables.get("selection", "")
        parcel_id = variables.get("parcel_id", "")
        subject = "Decision received"
        body = f"Thanks — we received your decision '{selection}' for parcel {parcel_id}."
        return subject, body
    # Generic fallback
    return None, str(variables.get("body", ""))


def _create_audit_event(
    db: Session,
    *,
    persona: Persona,
    action: str,
    resource: str,
    payload: dict[str, Any],
    user_id: str | None = None,
) -> models.AuditEvent:
    event_hash = sha256_hex({"action": action, "resource": resource, "payload": payload})
    event = models.AuditEvent(
        id=str(uuid4()),
        user_id=user_id,
        actor_persona=persona,
        action=action,
        resource=resource,
        payload=payload,
        hash=event_hash,
    )
    db.add(event)
    return event


def _create_outbox_communication(
    db: Session,
    *,
    project_id: str,
    parcel_id: str,
    channel: Channel,
    content: str,
    proof: dict[str, Any],
) -> models.Communication:
    comm_hash = sha256_hex(
        {
            "project_id": project_id,
            "parcel_id": parcel_id,
            "channel": channel,
            "direction": "outbound",
            "content": content,
            "proof": proof,
        }
    )
    comm = models.Communication(
        id=str(uuid4()),
        parcel_id=parcel_id,
        project_id=project_id,
        channel=channel,
        direction="outbound",
        content=content,
        delivery_status="queued" if proof.get("preview") is False else "preview",
        delivery_proof=proof,
        sla_due_at=None,
        hash=comm_hash,
        created_at=datetime.utcnow(),
    )
    db.add(comm)
    return comm


def preview_or_send(
    db: Session,
    *,
    persona: Persona,
    template_id: str,
    channel: Channel,
    to: str,
    variables: dict[str, Any],
    project_id: str,
    parcel_id: str,
    user_id: str | None = None,
) -> NotificationPreview:
    settings = get_settings()
    subject, body = _render_template(template_id, variables)

    mode = settings.notifications_mode.lower().strip()
    can_send = mode == "send"

    # Always generate the exact payload we would send.
    provider_payload: dict[str, Any]
    if channel == "email":
        provider_payload = {"to": to, "subject": subject, "body": body}
    else:
        provider_payload = {"to": to, "body": body}

    # Default to preview when secrets are missing.
    if channel == "email" and not settings.sendgrid_api_key:
        can_send = False
    if channel == "sms" and (not settings.twilio_account_sid or not settings.twilio_auth_token or not settings.twilio_from_number):
        can_send = False

    audit = _create_audit_event(
        db,
        persona=persona,
        user_id=user_id,
        action="notification.compose",
        resource=template_id,
        payload={"channel": channel, "to": to, "provider_payload": provider_payload, "project_id": project_id, "parcel_id": parcel_id},
    )

    comm: models.Communication | None = None

    if not can_send:
        comm = _create_outbox_communication(
            db,
            project_id=project_id,
            parcel_id=parcel_id,
            channel=channel,
            content=body,
            proof={"preview": True, "template_id": template_id, "payload": provider_payload},
        )
        db.commit()
        return NotificationPreview(
            notification_id=str(uuid4()),
            channel=channel,
            to=to,
            subject=subject,
            body=body,
            mode="preview",
            created_at=datetime.utcnow().isoformat() + "Z",
            communication_id=comm.id if comm else None,
            audit_event_id=audit.id,
        )

    # Provider send path (best-effort; still store comms + proof).
    proof: dict[str, Any] = {"preview": False, "template_id": template_id, "payload": provider_payload}
    status = "sent"
    try:
        if channel == "email":
            # Minimal SendGrid v3 mail send example; real integration can be expanded later.
            async_payload = {
                "personalizations": [{"to": [{"email": to}]}],
                "from": {"email": "no-reply@landright.local"},
                "subject": subject or "",
                "content": [{"type": "text/plain", "value": body}],
            }
            with httpx.Client(timeout=10.0) as client:
                r = client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={"Authorization": f"Bearer {settings.sendgrid_api_key}"},
                    json=async_payload,
                )
                proof["provider"] = "sendgrid"
                proof["status_code"] = r.status_code
        else:
            # Twilio send message API.
            with httpx.Client(timeout=10.0) as client:
                r = client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json",
                    auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                    data={"To": to, "From": settings.twilio_from_number, "Body": body},
                )
                proof["provider"] = "twilio"
                proof["status_code"] = r.status_code
        status = "sent"
    except Exception as exc:
        status = "failed"
        proof["error"] = str(exc)

    comm = _create_outbox_communication(
        db,
        project_id=project_id,
        parcel_id=parcel_id,
        channel=channel,
        content=body,
        proof=proof,
    )
    comm.delivery_status = status
    db.commit()

    return NotificationPreview(
        notification_id=str(uuid4()),
        channel=channel,
        to=to,
        subject=subject,
        body=body,
        mode="send",
        created_at=datetime.utcnow().isoformat() + "Z",
        communication_id=comm.id,
        audit_event_id=audit.id,
    )



