"""Tamper-evident audit log.

Phase 3.2: every ``AuditEvent`` row is part of a hash chain
``hash_n = sha256(prev_hash_{n-1} || canonical(payload_n))``.  Inserting or
deleting a row in the middle of the chain will cause :func:`verify_chain`
to return the offending id so the AI Audit drawer can surface the break.

The chain is scoped to a ``firm_id`` so compromise of one tenant's data
cannot be used to rewrite another tenant's log.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db import models


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload or {}, sort_keys=True, default=str).encode("utf-8")


def _compute_hash(
    prev_hash: Optional[str], payload: Any, resource: str, action: str
) -> str:
    h = hashlib.sha256()
    h.update((prev_hash or "").encode("utf-8"))
    h.update(b"|")
    h.update(resource.encode("utf-8"))
    h.update(b"|")
    h.update(action.encode("utf-8"))
    h.update(b"|")
    h.update(_canonical(payload))
    return h.hexdigest()


def _tail_hash(db: Session, firm_id: Optional[str]) -> Optional[str]:
    q = db.query(models.AuditEvent)
    if firm_id is not None:
        q = q.filter(models.AuditEvent.firm_id == firm_id)
    row = q.order_by(models.AuditEvent.occurred_at.desc()).first()
    return row.hash if row else None


def append_audit_event(
    db: Session,
    *,
    action: str,
    resource: str,
    user_id: Optional[str] = None,
    actor_persona: Optional[models.Persona] = None,
    payload: Optional[dict[str, Any]] = None,
    firm_id: Optional[str] = None,
    occurred_at: Optional[datetime] = None,
) -> models.AuditEvent:
    """Append an event to the firm-scoped hash chain.

    Returns the persisted :class:`AuditEvent` row; callers can use its
    ``hash`` field as a receipt for downstream systems.
    """

    prev = _tail_hash(db, firm_id)
    when = occurred_at or datetime.utcnow()
    digest = _compute_hash(prev, payload, resource, action)

    row = models.AuditEvent(
        id=f"aev_{uuid.uuid4().hex[:12]}",
        firm_id=firm_id,
        user_id=user_id,
        actor_persona=actor_persona,
        action=action,
        resource=resource,
        payload=payload or {},
        occurred_at=when,
        prev_hash=prev,
        hash=digest,
    )
    db.add(row)
    db.commit()
    return row


@dataclass
class ChainVerification:
    firm_id: Optional[str]
    verified: bool
    rows_checked: int
    first_bad_event: Optional[str] = None
    reason: Optional[str] = None


def verify_chain(
    db: Session,
    firm_id: Optional[str] = None,
) -> ChainVerification:
    """Walk the firm's audit log in order and verify every hash.

    Returns a :class:`ChainVerification` record with the first event id at
    which the chain breaks (or ``None`` if intact).
    """

    q = db.query(models.AuditEvent)
    if firm_id is not None:
        q = q.filter(models.AuditEvent.firm_id == firm_id)
    rows = q.order_by(
        models.AuditEvent.occurred_at.asc(), models.AuditEvent.id.asc()
    ).all()

    prev: Optional[str] = None
    for row in rows:
        expected = _compute_hash(prev, row.payload, row.resource, row.action)
        if row.prev_hash != prev:
            return ChainVerification(
                firm_id=firm_id,
                verified=False,
                rows_checked=len(rows),
                first_bad_event=row.id,
                reason="prev_hash mismatch",
            )
        if row.hash != expected:
            return ChainVerification(
                firm_id=firm_id,
                verified=False,
                rows_checked=len(rows),
                first_bad_event=row.id,
                reason="hash mismatch",
            )
        prev = row.hash

    return ChainVerification(
        firm_id=firm_id,
        verified=True,
        rows_checked=len(rows),
    )
