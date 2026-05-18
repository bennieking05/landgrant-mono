"""Approval Workflow Service.

Manages human-in-the-loop approval for critical actions:
    Draft -> QA Passed -> Pending Review -> Approved -> Sent/Filed

All irreversible actions (sending offers, filing petitions, recording deeds)
must flow through :class:`ApprovalService` so that an ``approvals`` row exists,
content hashes match, and the full audit trail is persisted.

Phase 1.2 of the AI-first robustness roadmap moved persistence off an in-memory
dict onto the ``approvals`` ORM table.  A SQLAlchemy ``Session`` is optional
(back-compat with tests that construct a bare service) but production code
paths are expected to inject one via ``Depends(get_db)``.
"""

from __future__ import annotations

import functools
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session


@dataclass
class ApprovalRequest:
    """Request for approval."""

    entity_type: str  # document, offer, filing, settlement
    entity_id: str
    action: str  # send, file, record, execute
    content_hash: str
    project_id: Optional[str] = None
    parcel_id: Optional[str] = None
    jurisdiction: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    idempotency_key: Optional[str] = None


@dataclass
class ApprovalRecord:
    """Complete approval record."""

    id: str
    entity_type: str
    entity_id: str
    action: str
    status: str  # draft, qa_passed, pending_review, approved, rejected, sent, filed

    content_hash: str

    project_id: Optional[str] = None
    parcel_id: Optional[str] = None
    jurisdiction: Optional[str] = None

    requested_by: Optional[str] = None
    requested_at: Optional[datetime] = None

    reviewer_user_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None

    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None

    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    executed_at: Optional[datetime] = None
    execution_result: Optional[dict[str, Any]] = None
    final_content_hash: Optional[str] = None

    diff_from_previous: Optional[dict[str, Any]] = None
    audit_trail: list[dict[str, Any]] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "status": self.status,
            "content_hash": self.content_hash,
            "project_id": self.project_id,
            "parcel_id": self.parcel_id,
            "jurisdiction": self.jurisdiction,
            "requested_by": self.requested_by,
            "requested_at": (
                self.requested_at.isoformat() if self.requested_at else None
            ),
            "reviewer_user_id": self.reviewer_user_id,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_notes": self.review_notes,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approval_notes": self.approval_notes,
            "rejected_by": self.rejected_by,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "rejection_reason": self.rejection_reason,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "execution_result": self.execution_result,
            "final_content_hash": self.final_content_hash,
            "audit_trail": self.audit_trail,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


APPROVAL_REQUIRED_ACTIONS: dict[str, list[str]] = {
    "document": ["send", "file", "record", "publish"],
    "offer": ["send_initial", "send_final", "send_counter"],
    "filing": ["file_petition", "file_motion", "record_deed"],
    "settlement": ["execute", "sign", "accept"],
    "binder": ["export", "publish"],
}


def action_requires_approval(entity_type: str, action: str) -> bool:
    """Predicate: is this entity/action combination gated by human approval?"""

    return action in APPROVAL_REQUIRED_ACTIONS.get(entity_type, [])


class ApprovalService:
    """Service for managing approval workflows.

    Pass ``db`` for persistent storage on the ``approvals`` table.  Without a
    session, an in-memory dict is used — convenient for unit tests but fatal
    for production because approvals would not survive a process restart.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self._approvals: dict[str, ApprovalRecord] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _row_to_record(self, row: Any) -> ApprovalRecord:
        status = row.status.value if hasattr(row.status, "value") else str(row.status)
        return ApprovalRecord(
            id=row.id,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            action=row.action,
            status=status,
            content_hash=row.content_hash,
            project_id=row.project_id,
            parcel_id=row.parcel_id,
            jurisdiction=row.jurisdiction,
            requested_by=row.requested_by,
            requested_at=row.requested_at,
            reviewer_user_id=row.reviewer_user_id,
            reviewed_at=row.reviewed_at,
            review_notes=row.review_notes,
            approved_by=row.approved_by,
            approved_at=row.approved_at,
            approval_notes=row.approval_notes,
            rejected_by=row.rejected_by,
            rejected_at=row.rejected_at,
            rejection_reason=row.rejection_reason,
            executed_at=row.executed_at,
            execution_result=row.execution_result,
            final_content_hash=row.final_content_hash,
            diff_from_previous=row.diff_from_previous,
            audit_trail=list(row.audit_trail or []),
            created_at=row.created_at or datetime.utcnow(),
            updated_at=row.updated_at or datetime.utcnow(),
        )

    def _commit_record(self, record: ApprovalRecord) -> None:
        """Persist ``record`` to DB or in-memory store."""

        if self.db is None:
            self._approvals[record.id] = record
            return

        from app.db import models

        row = self.db.get(models.Approval, record.id)
        if row is None:
            row = models.Approval(id=record.id, requested_by=record.requested_by)
            self.db.add(row)

        row.entity_type = record.entity_type
        row.entity_id = record.entity_id
        row.action = record.action
        row.status = models.ApprovalStatus(record.status)
        row.content_hash = record.content_hash
        row.project_id = record.project_id
        row.parcel_id = record.parcel_id
        row.jurisdiction = record.jurisdiction
        row.requested_by = record.requested_by
        row.requested_at = record.requested_at
        row.reviewer_user_id = record.reviewer_user_id
        row.reviewed_at = record.reviewed_at
        row.review_notes = record.review_notes
        row.approved_by = record.approved_by
        row.approved_at = record.approved_at
        row.approval_notes = record.approval_notes
        row.rejected_by = record.rejected_by
        row.rejected_at = record.rejected_at
        row.rejection_reason = record.rejection_reason
        row.executed_at = record.executed_at
        row.execution_result = record.execution_result
        row.final_content_hash = record.final_content_hash
        row.diff_from_previous = record.diff_from_previous
        row.audit_trail = record.audit_trail
        row.updated_at = record.updated_at
        self.db.commit()

    def _find_idempotent(
        self, request: ApprovalRequest
    ) -> Optional[ApprovalRecord]:
        """Return an existing open approval for the same entity/action/hash.

        This collapses retries so a caller who re-submits identical content
        gets the same record back instead of creating duplicates.
        """

        if self.db is None:
            for rec in self._approvals.values():
                if (
                    rec.entity_type == request.entity_type
                    and rec.entity_id == request.entity_id
                    and rec.action == request.action
                    and rec.content_hash == request.content_hash
                    and rec.status in {"draft", "qa_passed", "pending_review"}
                ):
                    return rec
            return None

        from app.db import models

        row = (
            self.db.query(models.Approval)
            .filter(
                models.Approval.entity_type == request.entity_type,
                models.Approval.entity_id == request.entity_id,
                models.Approval.action == request.action,
                models.Approval.content_hash == request.content_hash,
                models.Approval.status.in_(
                    [
                        models.ApprovalStatus.DRAFT,
                        models.ApprovalStatus.QA_PASSED,
                        models.ApprovalStatus.PENDING_REVIEW,
                    ]
                ),
            )
            .order_by(models.Approval.created_at.desc())
            .first()
        )
        return self._row_to_record(row) if row else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def request_approval(
        self, request: ApprovalRequest, user_id: str
    ) -> ApprovalRecord:
        """Create (or return existing) approval for an action.

        Idempotent: identical ``(entity_type, entity_id, action, content_hash)``
        tuples resolve to the same record while still in an open status.
        """

        existing = self._find_idempotent(request)
        if existing is not None:
            return existing

        now = datetime.utcnow()
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        record = ApprovalRecord(
            id=approval_id,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            action=request.action,
            status="pending_review",
            content_hash=request.content_hash,
            project_id=request.project_id,
            parcel_id=request.parcel_id,
            jurisdiction=request.jurisdiction,
            requested_by=user_id,
            requested_at=now,
            audit_trail=[
                {
                    "action": "requested",
                    "user_id": user_id,
                    "timestamp": now.isoformat(),
                    "status_from": None,
                    "status_to": "pending_review",
                    "idempotency_key": request.idempotency_key,
                }
            ],
            created_at=now,
            updated_at=now,
        )
        self._commit_record(record)
        return record

    def get_approval(self, approval_id: str) -> Optional[ApprovalRecord]:
        if self.db is None:
            return self._approvals.get(approval_id)

        from app.db import models

        row = self.db.get(models.Approval, approval_id)
        return self._row_to_record(row) if row else None

    def list_approvals(
        self,
        status: Optional[str] = None,
        entity_type: Optional[str] = None,
        project_id: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[ApprovalRecord]:
        if self.db is None:
            approvals = list(self._approvals.values())
            if status:
                approvals = [a for a in approvals if a.status == status]
            if entity_type:
                approvals = [a for a in approvals if a.entity_type == entity_type]
            if project_id:
                approvals = [a for a in approvals if a.project_id == project_id]
            if reviewer_id:
                approvals = [
                    a for a in approvals if a.reviewer_user_id == reviewer_id
                ]
            approvals.sort(key=lambda a: a.created_at, reverse=True)
            return approvals[:limit]

        from app.db import models

        q = self.db.query(models.Approval)
        if status:
            q = q.filter(models.Approval.status == models.ApprovalStatus(status))
        if entity_type:
            q = q.filter(models.Approval.entity_type == entity_type)
        if project_id:
            q = q.filter(models.Approval.project_id == project_id)
        if reviewer_id:
            q = q.filter(models.Approval.reviewer_user_id == reviewer_id)
        rows = q.order_by(models.Approval.created_at.desc()).limit(limit).all()
        return [self._row_to_record(r) for r in rows]

    def assign_reviewer(
        self, approval_id: str, reviewer_id: str, assigner_id: str
    ) -> ApprovalRecord:
        approval = self.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")

        approval.reviewer_user_id = reviewer_id
        approval.updated_at = datetime.utcnow()
        approval.audit_trail.append(
            {
                "action": "assigned",
                "user_id": assigner_id,
                "reviewer_id": reviewer_id,
                "timestamp": approval.updated_at.isoformat(),
            }
        )
        self._commit_record(approval)
        return approval

    def approve(
        self, approval_id: str, user_id: str, notes: Optional[str] = None
    ) -> ApprovalRecord:
        approval = self.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")

        if approval.status not in ["pending_review", "qa_passed"]:
            raise ValueError(f"Cannot approve from status: {approval.status}")

        now = datetime.utcnow()
        old_status = approval.status
        approval.status = "approved"
        approval.approved_by = user_id
        approval.approved_at = now
        approval.approval_notes = notes
        approval.updated_at = now
        approval.audit_trail.append(
            {
                "action": "approved",
                "user_id": user_id,
                "timestamp": now.isoformat(),
                "status_from": old_status,
                "status_to": "approved",
                "notes": notes,
            }
        )
        self._commit_record(approval)
        return approval

    def reject(
        self, approval_id: str, user_id: str, reason: str
    ) -> ApprovalRecord:
        approval = self.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")

        if approval.status not in ["pending_review", "qa_passed"]:
            raise ValueError(f"Cannot reject from status: {approval.status}")

        now = datetime.utcnow()
        old_status = approval.status
        approval.status = "rejected"
        approval.rejected_by = user_id
        approval.rejected_at = now
        approval.rejection_reason = reason
        approval.updated_at = now
        approval.audit_trail.append(
            {
                "action": "rejected",
                "user_id": user_id,
                "timestamp": now.isoformat(),
                "status_from": old_status,
                "status_to": "rejected",
                "reason": reason,
            }
        )
        self._commit_record(approval)
        return approval

    def mark_qa_passed(
        self, approval_id: str, qa_report_id: str
    ) -> ApprovalRecord:
        approval = self.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")

        if approval.status != "draft":
            raise ValueError(f"Cannot mark QA passed from status: {approval.status}")

        now = datetime.utcnow()
        approval.status = "qa_passed"
        approval.updated_at = now
        approval.audit_trail.append(
            {
                "action": "qa_passed",
                "qa_report_id": qa_report_id,
                "timestamp": now.isoformat(),
                "status_from": "draft",
                "status_to": "qa_passed",
            }
        )
        self._commit_record(approval)
        return approval

    def mark_executed(
        self,
        approval_id: str,
        final_content_hash: str,
        result: Optional[dict[str, Any]] = None,
    ) -> ApprovalRecord:
        approval = self.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")

        if approval.status != "approved":
            raise ValueError(f"Cannot execute from status: {approval.status}")

        if approval.action in ["send", "send_initial", "send_final", "send_counter"]:
            final_status = "sent"
        elif approval.action in [
            "file",
            "file_petition",
            "file_motion",
            "record_deed",
        ]:
            final_status = "filed"
        else:
            final_status = "sent"

        now = datetime.utcnow()
        old_status = approval.status
        approval.status = final_status
        approval.executed_at = now
        approval.final_content_hash = final_content_hash
        approval.execution_result = result
        approval.updated_at = now
        approval.audit_trail.append(
            {
                "action": "executed",
                "timestamp": now.isoformat(),
                "status_from": old_status,
                "status_to": final_status,
                "final_content_hash": final_content_hash,
                "result": result,
            }
        )
        self._commit_record(approval)
        return approval

    def get_by_entity(
        self, entity_type: str, entity_id: str
    ) -> Optional[ApprovalRecord]:
        if self.db is None:
            matching = [
                a
                for a in self._approvals.values()
                if a.entity_type == entity_type and a.entity_id == entity_id
            ]
            if not matching:
                return None
            matching.sort(key=lambda a: a.created_at, reverse=True)
            return matching[0]

        from app.db import models

        row = (
            self.db.query(models.Approval)
            .filter(
                models.Approval.entity_type == entity_type,
                models.Approval.entity_id == entity_id,
            )
            .order_by(models.Approval.created_at.desc())
            .first()
        )
        return self._row_to_record(row) if row else None


def check_approval_status(
    approval_service: ApprovalService,
    entity_type: str,
    entity_id: str,
    action: str,
    current_content_hash: str,
) -> dict[str, Any]:
    approval = approval_service.get_by_entity(entity_type, entity_id)

    if not approval:
        return {
            "approved": False,
            "reason": "No approval found",
            "requires_approval": action_requires_approval(entity_type, action),
        }

    if approval.status != "approved":
        return {
            "approved": False,
            "reason": f"Current status is {approval.status}, not approved",
            "approval_id": approval.id,
        }

    if approval.action != action:
        return {
            "approved": False,
            "reason": f"Approval is for action '{approval.action}', not '{action}'",
            "approval_id": approval.id,
        }

    if approval.content_hash != current_content_hash:
        return {
            "approved": False,
            "reason": "Content has changed since approval",
            "approval_id": approval.id,
            "approved_hash": approval.content_hash,
            "current_hash": current_content_hash,
        }

    return {
        "approved": True,
        "approval_id": approval.id,
        "approved_by": approval.approved_by,
        "approved_at": (
            approval.approved_at.isoformat() if approval.approved_at else None
        ),
    }


class ApprovalGate:
    """Gate that prevents execution without approval.

    Usage::

        gate = ApprovalGate(service)
        gate.require(entity_type, entity_id, action, content_hash)
    """

    def __init__(self, approval_service: ApprovalService):
        self.approval_service = approval_service

    def require(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        content_hash: str,
    ) -> ApprovalRecord:
        status = check_approval_status(
            self.approval_service,
            entity_type,
            entity_id,
            action,
            content_hash,
        )
        if not status["approved"]:
            raise ValueError(
                f"Action requires approval: {status.get('reason', 'Unknown reason')}"
            )
        approval = self.approval_service.get_approval(status["approval_id"])
        assert approval is not None
        return approval


# ----------------------------------------------------------------------
# Decorator for route handlers
# ----------------------------------------------------------------------


def requires_approval(
    entity_type: str,
    action: str,
    *,
    entity_id_arg: str = "entity_id",
    content_hash_arg: str = "content_hash",
    db_arg: str = "db",
):
    """Decorator for FastAPI handlers that gate irreversible legal actions.

    The decorated handler must expose ``entity_id`` and ``content_hash`` (or
    whatever names you pass in) as kwargs, plus a SQLAlchemy ``Session`` on the
    ``db_arg`` kwarg.  If no approved record matches, the decorator raises
    ``HTTPException(409)`` with an ``approval_id`` hint.

    For raw boolean checks, use :func:`action_requires_approval` instead.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            _assert_approved(kwargs, entity_type, action, entity_id_arg, content_hash_arg, db_arg)
            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            _assert_approved(kwargs, entity_type, action, entity_id_arg, content_hash_arg, db_arg)
            return func(*args, **kwargs)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def _assert_approved(
    kwargs: dict[str, Any],
    entity_type: str,
    action: str,
    entity_id_arg: str,
    content_hash_arg: str,
    db_arg: str,
) -> None:
    if not action_requires_approval(entity_type, action):
        return

    entity_id = kwargs.get(entity_id_arg)
    content_hash = kwargs.get(content_hash_arg)
    db = kwargs.get(db_arg)

    if not entity_id or not content_hash:
        raise HTTPException(
            status_code=400,
            detail=(
                "Approval gate requires both "
                f"'{entity_id_arg}' and '{content_hash_arg}' kwargs"
            ),
        )

    service = ApprovalService(db=db)
    status = check_approval_status(
        service, entity_type, str(entity_id), action, str(content_hash)
    )
    if not status.get("approved"):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "approval_required",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action": action,
                "reason": status.get("reason"),
                "approval_id": status.get("approval_id"),
            },
        )
