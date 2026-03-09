"""Approval Workflow Service.

Manages human-in-the-loop approval for critical actions:
- Draft -> QA Passed -> Pending Review -> Approved -> Sent/Filed
- All irreversible actions require approval
- Provides audit trail for all approval decisions

No document is sent or filed without passing through this workflow.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from app.services.hashing import sha256_hex


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
        """Convert to dictionary."""
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
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
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


# Actions that require approval
APPROVAL_REQUIRED_ACTIONS = {
    "document": ["send", "file", "record", "publish"],
    "offer": ["send_initial", "send_final", "send_counter"],
    "filing": ["file_petition", "file_motion", "record_deed"],
    "settlement": ["execute", "sign", "accept"],
}


class ApprovalService:
    """Service for managing approval workflows."""

    def __init__(self):
        """Initialize the service."""
        self._approvals: dict[str, ApprovalRecord] = {}

    def request_approval(
        self,
        request: ApprovalRequest,
        user_id: str,
    ) -> ApprovalRecord:
        """Request approval for an action.
        
        Args:
            request: Approval request
            user_id: ID of requesting user
            
        Returns:
            Created approval record
        """
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        
        approval = ApprovalRecord(
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
            requested_at=datetime.utcnow(),
            audit_trail=[{
                "action": "requested",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "status_from": None,
                "status_to": "pending_review",
            }],
        )
        
        self._approvals[approval_id] = approval
        return approval

    def get_approval(self, approval_id: str) -> Optional[ApprovalRecord]:
        """Get an approval by ID.
        
        Args:
            approval_id: Approval identifier
            
        Returns:
            Approval record or None
        """
        return self._approvals.get(approval_id)

    def list_approvals(
        self,
        status: Optional[str] = None,
        entity_type: Optional[str] = None,
        project_id: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[ApprovalRecord]:
        """List approvals with filters.
        
        Args:
            status: Filter by status
            entity_type: Filter by entity type
            project_id: Filter by project
            reviewer_id: Filter by assigned reviewer
            limit: Maximum results
            
        Returns:
            Matching approvals
        """
        approvals = list(self._approvals.values())
        
        if status:
            approvals = [a for a in approvals if a.status == status]
        if entity_type:
            approvals = [a for a in approvals if a.entity_type == entity_type]
        if project_id:
            approvals = [a for a in approvals if a.project_id == project_id]
        if reviewer_id:
            approvals = [a for a in approvals if a.reviewer_user_id == reviewer_id]
        
        approvals.sort(key=lambda a: a.created_at, reverse=True)
        return approvals[:limit]

    def assign_reviewer(
        self,
        approval_id: str,
        reviewer_id: str,
        assigner_id: str,
    ) -> ApprovalRecord:
        """Assign a reviewer to an approval.
        
        Args:
            approval_id: Approval identifier
            reviewer_id: ID of reviewer to assign
            assigner_id: ID of user making assignment
            
        Returns:
            Updated approval
        """
        approval = self.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        approval.reviewer_user_id = reviewer_id
        approval.updated_at = datetime.utcnow()
        approval.audit_trail.append({
            "action": "assigned",
            "user_id": assigner_id,
            "reviewer_id": reviewer_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        return approval

    def approve(
        self,
        approval_id: str,
        user_id: str,
        notes: Optional[str] = None,
    ) -> ApprovalRecord:
        """Approve an action.
        
        Args:
            approval_id: Approval identifier
            user_id: ID of approving user
            notes: Optional approval notes
            
        Returns:
            Updated approval
        """
        approval = self.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        if approval.status not in ["pending_review", "qa_passed"]:
            raise ValueError(f"Cannot approve from status: {approval.status}")
        
        old_status = approval.status
        approval.status = "approved"
        approval.approved_by = user_id
        approval.approved_at = datetime.utcnow()
        approval.approval_notes = notes
        approval.updated_at = datetime.utcnow()
        
        approval.audit_trail.append({
            "action": "approved",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status_from": old_status,
            "status_to": "approved",
            "notes": notes,
        })
        
        return approval

    def reject(
        self,
        approval_id: str,
        user_id: str,
        reason: str,
    ) -> ApprovalRecord:
        """Reject an action.
        
        Args:
            approval_id: Approval identifier
            user_id: ID of rejecting user
            reason: Rejection reason
            
        Returns:
            Updated approval
        """
        approval = self.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        if approval.status not in ["pending_review", "qa_passed"]:
            raise ValueError(f"Cannot reject from status: {approval.status}")
        
        old_status = approval.status
        approval.status = "rejected"
        approval.rejected_by = user_id
        approval.rejected_at = datetime.utcnow()
        approval.rejection_reason = reason
        approval.updated_at = datetime.utcnow()
        
        approval.audit_trail.append({
            "action": "rejected",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status_from": old_status,
            "status_to": "rejected",
            "reason": reason,
        })
        
        return approval

    def mark_qa_passed(
        self,
        approval_id: str,
        qa_report_id: str,
    ) -> ApprovalRecord:
        """Mark approval as QA passed.
        
        Args:
            approval_id: Approval identifier
            qa_report_id: ID of passing QA report
            
        Returns:
            Updated approval
        """
        approval = self.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        if approval.status != "draft":
            raise ValueError(f"Cannot mark QA passed from status: {approval.status}")
        
        approval.status = "qa_passed"
        approval.updated_at = datetime.utcnow()
        
        approval.audit_trail.append({
            "action": "qa_passed",
            "qa_report_id": qa_report_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status_from": "draft",
            "status_to": "qa_passed",
        })
        
        return approval

    def mark_executed(
        self,
        approval_id: str,
        final_content_hash: str,
        result: Optional[dict[str, Any]] = None,
    ) -> ApprovalRecord:
        """Mark action as executed (sent/filed).
        
        Args:
            approval_id: Approval identifier
            final_content_hash: Hash of final executed content
            result: Execution result details
            
        Returns:
            Updated approval
        """
        approval = self.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        if approval.status != "approved":
            raise ValueError(f"Cannot execute from status: {approval.status}")
        
        # Determine final status based on action
        if approval.action in ["send", "send_initial", "send_final", "send_counter"]:
            final_status = "sent"
        elif approval.action in ["file", "file_petition", "file_motion", "record_deed"]:
            final_status = "filed"
        else:
            final_status = "sent"
        
        old_status = approval.status
        approval.status = final_status
        approval.executed_at = datetime.utcnow()
        approval.final_content_hash = final_content_hash
        approval.execution_result = result
        approval.updated_at = datetime.utcnow()
        
        approval.audit_trail.append({
            "action": "executed",
            "timestamp": datetime.utcnow().isoformat(),
            "status_from": old_status,
            "status_to": final_status,
            "final_content_hash": final_content_hash,
            "result": result,
        })
        
        return approval

    def get_by_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> Optional[ApprovalRecord]:
        """Get approval by entity.
        
        Args:
            entity_type: Entity type
            entity_id: Entity identifier
            
        Returns:
            Latest approval for entity or None
        """
        matching = [
            a for a in self._approvals.values()
            if a.entity_type == entity_type and a.entity_id == entity_id
        ]
        
        if not matching:
            return None
        
        # Return latest
        matching.sort(key=lambda a: a.created_at, reverse=True)
        return matching[0]


def requires_approval(entity_type: str, action: str) -> bool:
    """Check if an action requires approval.
    
    Args:
        entity_type: Type of entity
        action: Action to perform
        
    Returns:
        True if approval is required
    """
    required_actions = APPROVAL_REQUIRED_ACTIONS.get(entity_type, [])
    return action in required_actions


def check_approval_status(
    approval_service: ApprovalService,
    entity_type: str,
    entity_id: str,
    action: str,
    current_content_hash: str,
) -> dict[str, Any]:
    """Check if an action is approved and valid.
    
    Args:
        approval_service: Approval service instance
        entity_type: Entity type
        entity_id: Entity identifier
        action: Action to check
        current_content_hash: Hash of current content
        
    Returns:
        Status information
    """
    approval = approval_service.get_by_entity(entity_type, entity_id)
    
    if not approval:
        return {
            "approved": False,
            "reason": "No approval found",
            "requires_approval": requires_approval(entity_type, action),
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
        "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
    }


class ApprovalGate:
    """Gate that prevents execution without approval.
    
    Usage:
        gate = ApprovalGate(approval_service)
        gate.require(entity_type, entity_id, action, content_hash)
    """

    def __init__(self, approval_service: ApprovalService):
        """Initialize the gate.
        
        Args:
            approval_service: Approval service instance
        """
        self.approval_service = approval_service

    def require(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        content_hash: str,
    ) -> ApprovalRecord:
        """Require approval before proceeding.
        
        Args:
            entity_type: Entity type
            entity_id: Entity identifier
            action: Action to perform
            content_hash: Hash of content
            
        Returns:
            Valid approval record
            
        Raises:
            ValueError: If approval is missing or invalid
        """
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
        return approval
