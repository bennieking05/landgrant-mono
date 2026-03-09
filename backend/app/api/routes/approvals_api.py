"""API routes for Approval Workflow.

Provides endpoints for:
- Requesting approvals
- Reviewing and approving/rejecting
- Tracking approval status
- Gating critical actions
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel

from app.api.deps import get_current_persona
from app.db.models import Persona
from app.security.rbac import authorize, Action

router = APIRouter(prefix="/approvals", tags=["approvals"])


# Request/Response models
class ApprovalRequestInput(BaseModel):
    """Request for a new approval."""
    entity_type: str  # document, offer, filing, settlement
    entity_id: str
    action: str  # send, file, record, execute
    content_hash: str
    project_id: Optional[str] = None
    parcel_id: Optional[str] = None
    jurisdiction: Optional[str] = None


class ApprovalResponse(BaseModel):
    """Approval record response."""
    id: str
    entity_type: str
    entity_id: str
    action: str
    status: str
    content_hash: str
    requested_by: Optional[str]
    requested_at: Optional[str]
    approved_by: Optional[str]
    approved_at: Optional[str]
    rejected_by: Optional[str]
    rejection_reason: Optional[str]


class ResolveRequest(BaseModel):
    """Request to resolve an approval."""
    outcome: str  # approve, reject
    notes: Optional[str] = None
    reason: Optional[str] = None  # Required for rejection


class StatusCheckResponse(BaseModel):
    """Response from approval status check."""
    approved: bool
    reason: Optional[str] = None
    approval_id: Optional[str] = None
    requires_approval: bool = True


@router.post("/request", response_model=ApprovalResponse)
async def request_approval(
    request: ApprovalRequestInput,
    persona: Persona = Depends(get_current_persona),
):
    """Request approval for a critical action.
    
    Creates an approval record in pending_review status.
    """
    authorize(persona, "approvals", Action.WRITE)
    
    from app.services.approvals import ApprovalService, ApprovalRequest
    
    service = ApprovalService()
    approval = service.request_approval(
        request=ApprovalRequest(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            action=request.action,
            content_hash=request.content_hash,
            project_id=request.project_id,
            parcel_id=request.parcel_id,
            jurisdiction=request.jurisdiction,
        ),
        user_id=str(persona),
    )
    
    return ApprovalResponse(
        id=approval.id,
        entity_type=approval.entity_type,
        entity_id=approval.entity_id,
        action=approval.action,
        status=approval.status,
        content_hash=approval.content_hash,
        requested_by=approval.requested_by,
        requested_at=approval.requested_at.isoformat() if approval.requested_at else None,
        approved_by=approval.approved_by,
        approved_at=approval.approved_at.isoformat() if approval.approved_at else None,
        rejected_by=approval.rejected_by,
        rejection_reason=approval.rejection_reason,
    )


@router.get("", response_model=list[ApprovalResponse])
async def list_approvals(
    persona: Persona = Depends(get_current_persona),
    status: Optional[str] = None,
    entity_type: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = Query(50, le=200),
):
    """List approvals with optional filters."""
    authorize(persona, "approvals", Action.READ)
    
    from app.services.approvals import ApprovalService
    
    service = ApprovalService()
    approvals = service.list_approvals(
        status=status,
        entity_type=entity_type,
        project_id=project_id,
        limit=limit,
    )
    
    return [
        ApprovalResponse(
            id=a.id,
            entity_type=a.entity_type,
            entity_id=a.entity_id,
            action=a.action,
            status=a.status,
            content_hash=a.content_hash,
            requested_by=a.requested_by,
            requested_at=a.requested_at.isoformat() if a.requested_at else None,
            approved_by=a.approved_by,
            approved_at=a.approved_at.isoformat() if a.approved_at else None,
            rejected_by=a.rejected_by,
            rejection_reason=a.rejection_reason,
        )
        for a in approvals
    ]


@router.get("/{approval_id}")
async def get_approval(
    approval_id: str,
    persona: Persona = Depends(get_current_persona),
):
    """Get details of a specific approval."""
    authorize(persona, "approvals", Action.READ)
    
    from app.services.approvals import ApprovalService
    
    service = ApprovalService()
    approval = service.get_approval(approval_id)
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    return approval.to_dict()


@router.post("/{approval_id}/approve")
async def approve(
    approval_id: str,
    notes: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
):
    """Approve an action.
    
    Only counsel can approve actions.
    """
    authorize(persona, "approvals", Action.APPROVE)
    
    from app.services.approvals import ApprovalService
    
    service = ApprovalService()
    
    try:
        approval = service.approve(
            approval_id=approval_id,
            user_id=str(persona),
            notes=notes,
        )
        return approval.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{approval_id}/reject")
async def reject(
    approval_id: str,
    reason: str,
    persona: Persona = Depends(get_current_persona),
):
    """Reject an action.
    
    Requires a reason for the rejection.
    """
    authorize(persona, "approvals", Action.APPROVE)
    
    from app.services.approvals import ApprovalService
    
    service = ApprovalService()
    
    try:
        approval = service.reject(
            approval_id=approval_id,
            user_id=str(persona),
            reason=reason,
        )
        return approval.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{approval_id}/assign")
async def assign_reviewer(
    approval_id: str,
    reviewer_id: str,
    persona: Persona = Depends(get_current_persona),
):
    """Assign a reviewer to an approval."""
    authorize(persona, "approvals", Action.WRITE)
    
    from app.services.approvals import ApprovalService
    
    service = ApprovalService()
    
    try:
        approval = service.assign_reviewer(
            approval_id=approval_id,
            reviewer_id=reviewer_id,
            assigner_id=str(persona),
        )
        return approval.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/check/{entity_type}/{entity_id}", response_model=StatusCheckResponse)
async def check_approval_status(
    entity_type: str,
    entity_id: str,
    action: str,
    content_hash: str,
    persona: Persona = Depends(get_current_persona),
):
    """Check if an action is approved.
    
    Use before executing any critical action to verify
    approval exists and content hasn't changed.
    """
    authorize(persona, "approvals", Action.READ)
    
    from app.services.approvals import ApprovalService, check_approval_status as check_status
    
    service = ApprovalService()
    result = check_status(
        approval_service=service,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        current_content_hash=content_hash,
    )
    
    return StatusCheckResponse(
        approved=result["approved"],
        reason=result.get("reason"),
        approval_id=result.get("approval_id"),
        requires_approval=result.get("requires_approval", True),
    )


@router.post("/{approval_id}/execute")
async def mark_executed(
    approval_id: str,
    final_content_hash: str,
    result: Optional[dict[str, Any]] = None,
    persona: Persona = Depends(get_current_persona),
):
    """Mark an approved action as executed.
    
    Called after the action (send/file) is completed.
    Records the final content hash for audit.
    """
    authorize(persona, "approvals", Action.EXECUTE)
    
    from app.services.approvals import ApprovalService
    
    service = ApprovalService()
    
    try:
        approval = service.mark_executed(
            approval_id=approval_id,
            final_content_hash=final_content_hash,
            result=result,
        )
        return approval.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
