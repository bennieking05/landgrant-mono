"""Tests for Approval Workflow Service."""

import pytest
from datetime import datetime

from app.services.approvals import (
    ApprovalService,
    ApprovalRequest,
    ApprovalGate,
    requires_approval,
    check_approval_status,
)


@pytest.fixture
def approval_service():
    """Create an approval service."""
    return ApprovalService()


def test_request_approval(approval_service):
    """Test requesting approval."""
    approval = approval_service.request_approval(
        request=ApprovalRequest(
            entity_type="document",
            entity_id="doc-123",
            action="send",
            content_hash="hash123",
            project_id="proj-001",
            jurisdiction="TX",
        ),
        user_id="user-001",
    )
    
    assert approval.id.startswith("appr_")
    assert approval.status == "pending_review"
    assert approval.requested_by == "user-001"
    assert len(approval.audit_trail) == 1


def test_list_approvals(approval_service):
    """Test listing approvals."""
    # Create multiple approvals
    approval_service.request_approval(
        ApprovalRequest(
            entity_type="document",
            entity_id="doc-1",
            action="send",
            content_hash="hash1",
        ),
        user_id="user-001",
    )
    approval_service.request_approval(
        ApprovalRequest(
            entity_type="offer",
            entity_id="offer-1",
            action="send_final",
            content_hash="hash2",
        ),
        user_id="user-001",
    )
    
    # List all
    all_approvals = approval_service.list_approvals()
    assert len(all_approvals) == 2
    
    # Filter by type
    doc_approvals = approval_service.list_approvals(entity_type="document")
    assert len(doc_approvals) == 1


def test_approve(approval_service):
    """Test approving an action."""
    approval = approval_service.request_approval(
        ApprovalRequest(
            entity_type="document",
            entity_id="doc-123",
            action="send",
            content_hash="hash123",
        ),
        user_id="user-001",
    )
    
    approved = approval_service.approve(
        approval_id=approval.id,
        user_id="counsel-001",
        notes="Looks good",
    )
    
    assert approved.status == "approved"
    assert approved.approved_by == "counsel-001"
    assert approved.approval_notes == "Looks good"
    assert len(approved.audit_trail) == 2


def test_reject(approval_service):
    """Test rejecting an action."""
    approval = approval_service.request_approval(
        ApprovalRequest(
            entity_type="document",
            entity_id="doc-123",
            action="send",
            content_hash="hash123",
        ),
        user_id="user-001",
    )
    
    rejected = approval_service.reject(
        approval_id=approval.id,
        user_id="counsel-001",
        reason="Missing required clause",
    )
    
    assert rejected.status == "rejected"
    assert rejected.rejected_by == "counsel-001"
    assert rejected.rejection_reason == "Missing required clause"


def test_approve_invalid_status(approval_service):
    """Test that approving from wrong status fails."""
    approval = approval_service.request_approval(
        ApprovalRequest(
            entity_type="document",
            entity_id="doc-123",
            action="send",
            content_hash="hash123",
        ),
        user_id="user-001",
    )
    
    # Approve first
    approval_service.approve(approval.id, "counsel-001")
    
    # Try to approve again - should fail
    with pytest.raises(ValueError, match="Cannot approve from status"):
        approval_service.approve(approval.id, "counsel-002")


def test_mark_executed(approval_service):
    """Test marking as executed."""
    approval = approval_service.request_approval(
        ApprovalRequest(
            entity_type="document",
            entity_id="doc-123",
            action="send",
            content_hash="hash123",
        ),
        user_id="user-001",
    )
    
    # Approve first
    approval_service.approve(approval.id, "counsel-001")
    
    # Mark executed
    executed = approval_service.mark_executed(
        approval_id=approval.id,
        final_content_hash="final_hash_123",
        result={"delivery_id": "msg-001"},
    )
    
    assert executed.status == "sent"
    assert executed.final_content_hash == "final_hash_123"
    assert executed.execution_result["delivery_id"] == "msg-001"


def test_mark_executed_without_approval(approval_service):
    """Test that execution without approval fails."""
    approval = approval_service.request_approval(
        ApprovalRequest(
            entity_type="document",
            entity_id="doc-123",
            action="send",
            content_hash="hash123",
        ),
        user_id="user-001",
    )
    
    # Try to execute without approving - should fail
    with pytest.raises(ValueError, match="Cannot execute from status"):
        approval_service.mark_executed(
            approval.id,
            "final_hash",
        )


def test_assign_reviewer(approval_service):
    """Test assigning a reviewer."""
    approval = approval_service.request_approval(
        ApprovalRequest(
            entity_type="document",
            entity_id="doc-123",
            action="send",
            content_hash="hash123",
        ),
        user_id="user-001",
    )
    
    assigned = approval_service.assign_reviewer(
        approval_id=approval.id,
        reviewer_id="counsel-001",
        assigner_id="admin-001",
    )
    
    assert assigned.reviewer_user_id == "counsel-001"


def test_get_by_entity(approval_service):
    """Test getting approval by entity."""
    approval_service.request_approval(
        ApprovalRequest(
            entity_type="document",
            entity_id="doc-123",
            action="send",
            content_hash="hash123",
        ),
        user_id="user-001",
    )
    
    found = approval_service.get_by_entity("document", "doc-123")
    
    assert found is not None
    assert found.entity_id == "doc-123"


def test_requires_approval():
    """Test the requires_approval check."""
    assert requires_approval("document", "send")
    assert requires_approval("filing", "file_petition")
    assert requires_approval("settlement", "execute")
    assert not requires_approval("document", "read")  # Not in list


def test_check_approval_status_approved(approval_service):
    """Test checking approval status."""
    approval = approval_service.request_approval(
        ApprovalRequest(
            entity_type="document",
            entity_id="doc-123",
            action="send",
            content_hash="hash123",
        ),
        user_id="user-001",
    )
    approval_service.approve(approval.id, "counsel-001")
    
    status = check_approval_status(
        approval_service,
        entity_type="document",
        entity_id="doc-123",
        action="send",
        current_content_hash="hash123",
    )
    
    assert status["approved"]
    assert status["approval_id"] == approval.id


def test_check_approval_status_content_changed(approval_service):
    """Test that content change invalidates approval."""
    approval = approval_service.request_approval(
        ApprovalRequest(
            entity_type="document",
            entity_id="doc-123",
            action="send",
            content_hash="hash123",
        ),
        user_id="user-001",
    )
    approval_service.approve(approval.id, "counsel-001")
    
    status = check_approval_status(
        approval_service,
        entity_type="document",
        entity_id="doc-123",
        action="send",
        current_content_hash="different_hash",  # Changed!
    )
    
    assert not status["approved"]
    assert "changed" in status["reason"]


def test_approval_gate(approval_service):
    """Test the approval gate."""
    gate = ApprovalGate(approval_service)
    
    # Request and approve
    approval = approval_service.request_approval(
        ApprovalRequest(
            entity_type="document",
            entity_id="doc-123",
            action="send",
            content_hash="hash123",
        ),
        user_id="user-001",
    )
    approval_service.approve(approval.id, "counsel-001")
    
    # Gate should pass
    result = gate.require(
        entity_type="document",
        entity_id="doc-123",
        action="send",
        content_hash="hash123",
    )
    
    assert result.id == approval.id


def test_approval_gate_fails(approval_service):
    """Test the approval gate blocks unapproved actions."""
    gate = ApprovalGate(approval_service)
    
    with pytest.raises(ValueError, match="requires approval"):
        gate.require(
            entity_type="document",
            entity_id="nonexistent",
            action="send",
            content_hash="hash123",
        )
