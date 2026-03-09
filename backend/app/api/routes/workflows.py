from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_persona
from app.db import models
from app.db.models import Persona, ParcelStage, StatusChange
from app.security.rbac import authorize, Action
from pydantic import BaseModel, Field
from uuid import uuid4
from app.services.hashing import sha256_hex

router = APIRouter(prefix="/workflows", tags=["workflows"])

_LOCAL_STORAGE_ROOT = Path(__file__).resolve().parents[3] / "local_storage"


class TaskCreate(BaseModel):
    project_id: str
    parcel_id: str | None = None
    title: str
    persona: Persona
    due_at: str | None = None


@router.post("/tasks")
def create_task(payload: TaskCreate, persona: Persona = Depends(get_current_persona), db: Session = Depends(get_db)):
    authorize(persona, "binder", Action.APPROVE)
    task = models.Task(
        id=str(uuid4()),
        project_id=payload.project_id,
        parcel_id=payload.parcel_id,
        title=payload.title,
        persona=payload.persona,
    )
    db.add(task)
    db.commit()
    return {"task_id": task.id}


class ApprovalItem(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    action: str
    status: str
    project_id: Optional[str] = None
    parcel_id: Optional[str] = None
    requested_at: Optional[datetime] = None
    jurisdiction: Optional[str] = None


@router.get("/approvals")
def list_approvals(
    status: Optional[str] = "pending_review",
    project_id: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """List pending approvals requiring attorney review."""
    authorize(persona, "template", Action.APPROVE)
    
    from app.db.models import Approval, ApprovalStatus
    
    query = db.query(Approval)
    
    # Filter by status
    if status:
        try:
            approval_status = ApprovalStatus(status)
            query = query.filter(Approval.status == approval_status)
        except ValueError:
            pass  # Invalid status, skip filter
    
    # Filter by project if specified
    if project_id:
        query = query.filter(Approval.project_id == project_id)
    
    # Order by most recent first
    approvals = query.order_by(Approval.requested_at.desc()).limit(100).all()
    
    return {
        "items": [
            ApprovalItem(
                id=a.id,
                entity_type=a.entity_type,
                entity_id=a.entity_id,
                action=a.action,
                status=a.status.value if hasattr(a.status, 'value') else str(a.status),
                project_id=a.project_id,
                parcel_id=a.parcel_id,
                requested_at=a.requested_at,
                jurisdiction=a.jurisdiction,
            ).model_dump()
            for a in approvals
        ],
        "count": len(approvals),
    }


class BinderExportRequest(BaseModel):
    project_id: str = Field(..., description="Project ID to export")
    parcel_id: Optional[str] = Field(None, description="Optional parcel ID to filter")


class BinderExportResponse(BaseModel):
    bundle_id: str
    hash: str
    storage_path: str
    project_id: str
    parcel_id: Optional[str] = None


import logging
_logger = logging.getLogger(__name__)


@router.post("/binder/export", response_model=BinderExportResponse)
def export_binder(
    request: BinderExportRequest,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    authorize(persona, "binder", Action.APPROVE)
    bundle_id = str(uuid4())
    try:
        # Fetch project and optionally parcel
        project = db.get(models.Project, request.project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project not found: {request.project_id}")
        
        parcel = None
        if request.parcel_id:
            parcel = db.get(models.Parcel, request.parcel_id)
            if not parcel:
                raise HTTPException(status_code=404, detail=f"Parcel not found: {request.parcel_id}")
        
        # Build manifest for the specified project/parcel
        comms_query = db.query(models.Communication).filter(
            models.Communication.project_id == request.project_id
        )
        if request.parcel_id:
            comms_query = comms_query.filter(models.Communication.parcel_id == request.parcel_id)
        comms = comms_query.order_by(models.Communication.created_at.asc()).all()
        
        rules_query = db.query(models.RuleResult).filter(
            models.RuleResult.project_id == request.project_id
        )
        if request.parcel_id:
            rules_query = rules_query.filter(models.RuleResult.parcel_id == request.parcel_id)
        rules = rules_query.order_by(models.RuleResult.fired_at.desc()).all()
        
        docs = db.query(models.Document).order_by(models.Document.created_at.desc()).all()

        manifest = {
            "bundle_id": bundle_id,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "project": {"id": project.id, "jurisdiction": project.jurisdiction_code},
            "parcel": {"id": parcel.id, "county_fips": parcel.county_fips} if parcel else None,
            "communications": [{"id": c.id, "channel": c.channel, "status": c.delivery_status, "hash": c.hash} for c in comms],
            "rule_results": [{"id": r.id, "rule_id": r.rule_id, "citation": r.citation, "payload": r.payload} for r in rules],
            "documents": [{"id": d.id, "doc_type": d.doc_type, "sha256": d.sha256, "path": d.storage_path} for d in docs],
        }
        bundle_hash = sha256_hex(manifest)

        out_dir = _LOCAL_STORAGE_ROOT / "binder"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{bundle_id}.json"
        out_path.write_text(__import__("json").dumps(manifest, indent=2, sort_keys=True))

        # Store as Document + AuditEvent (best-effort; do not fail export if DB is unhealthy/full).
        db.add(
            models.Document(
                id=bundle_id,
                doc_type="binder",
                version="1.0.0",
                sha256=bundle_hash,
                storage_path=str(out_path),
                metadata_json={"format": "json", "project_id": request.project_id, "parcel_id": request.parcel_id},
            )
        )
        db.add(
            models.AuditEvent(
                id=str(uuid4()),
                actor_persona=persona,
                action="binder.export",
                resource="binder",
                payload={"bundle_id": bundle_id, "sha256": bundle_hash, "path": str(out_path), "project_id": request.project_id},
                hash=sha256_hex({"bundle_id": bundle_id, "sha256": bundle_hash}),
            )
        )
        db.commit()
        return BinderExportResponse(
            bundle_id=bundle_id,
            hash=f"sha256:{bundle_hash}",
            storage_path=str(out_path),
            project_id=request.project_id,
            parcel_id=request.parcel_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        _logger.error(f"Binder export failed for project {request.project_id}: {e}", exc_info=True)
        # Return error response instead of silently failing
        raise HTTPException(status_code=500, detail=f"Binder export failed: {str(e)}")


# =============================================================================
# Workflow Engine Routes - Stage Progression Management
# =============================================================================

class TransitionRequest(BaseModel):
    """Request to manually transition a parcel to a new stage."""
    target_stage: str = Field(..., description="Target stage to transition to")
    notes: Optional[str] = Field(None, description="Notes for the transition")
    skip_guards: bool = Field(False, description="Skip guard checks (counsel only)")


class TransitionResponse(BaseModel):
    """Response from a transition attempt."""
    success: bool
    parcel_id: str
    from_stage: str
    to_stage: Optional[str]
    reason: str
    status_change_id: Optional[str] = None
    requires_escalation: bool = False


class EventRequest(BaseModel):
    """Request to trigger a workflow event."""
    event_type: str = Field(..., description="Type of workflow event")
    parcel_id: str = Field(..., description="Parcel ID to process")
    event_data: Optional[dict] = Field(None, description="Additional event data")


class PendingItem(BaseModel):
    """Parcel pending attorney review."""
    parcel_id: str
    project_id: str
    current_stage: str
    target_stage: str
    confidence: float
    reason: str
    requires_review: bool


class HistoryItem(BaseModel):
    """Stage change history entry."""
    id: str
    old_status: str
    new_status: str
    reason: Optional[str]
    actor_persona: str
    occurred_at: datetime


@router.get("/parcel/{parcel_id}/transitions")
def get_valid_transitions(
    parcel_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get valid next stages for a parcel with guard evaluation."""
    authorize(persona, "parcel", Action.READ)
    
    from app.services.workflow_engine import WorkflowEngine
    
    parcel = db.query(models.Parcel).filter(models.Parcel.id == parcel_id).first()
    if not parcel:
        raise HTTPException(status_code=404, detail=f"Parcel not found: {parcel_id}")
    
    engine = WorkflowEngine(db)
    valid_transitions = engine.get_valid_transitions(parcel)
    
    transitions = []
    for target_stage in valid_transitions:
        guard_result = engine.evaluate_transition(parcel, target_stage)
        transitions.append({
            "target_stage": target_stage.value,
            "allowed": guard_result.allowed,
            "confidence": guard_result.confidence,
            "reason": guard_result.reason,
            "requires_review": guard_result.requires_review,
            "missing_conditions": guard_result.missing_conditions,
        })
    
    return {
        "parcel_id": parcel_id,
        "current_stage": parcel.stage.value if hasattr(parcel.stage, 'value') else parcel.stage,
        "transitions": transitions,
    }


@router.post("/parcel/{parcel_id}/transition", response_model=TransitionResponse)
def execute_transition(
    parcel_id: str,
    request: TransitionRequest,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Manually transition a parcel to a new stage (counsel only for skip_guards)."""
    authorize(persona, "parcel", Action.UPDATE)
    
    # Only counsel can skip guards
    if request.skip_guards and persona not in [Persona.IN_HOUSE_COUNSEL, Persona.OUTSIDE_COUNSEL, Persona.ADMIN]:
        raise HTTPException(status_code=403, detail="Only counsel can skip guard checks")
    
    from app.services.workflow_engine import WorkflowEngine, TransitionReason
    
    parcel = db.query(models.Parcel).filter(models.Parcel.id == parcel_id).first()
    if not parcel:
        raise HTTPException(status_code=404, detail=f"Parcel not found: {parcel_id}")
    
    try:
        target_stage = ParcelStage(request.target_stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {request.target_stage}")
    
    engine = WorkflowEngine(db)
    result = engine.execute_transition(
        parcel,
        target_stage,
        reason=TransitionReason.MANUAL_OVERRIDE,
        actor_persona=persona,
        notes=request.notes,
        skip_guards=request.skip_guards,
    )
    
    return TransitionResponse(
        success=result.success,
        parcel_id=parcel_id,
        from_stage=result.from_stage.value,
        to_stage=result.to_stage.value if result.to_stage else None,
        reason=result.reason,
        status_change_id=result.status_change_id,
        requires_escalation=result.requires_escalation,
    )


@router.get("/pending", response_model=list[PendingItem])
def get_pending_progressions(
    project_id: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get parcels pending attorney review for stage progression."""
    authorize(persona, "parcel", Action.READ)
    
    from app.services.workflow_engine import WorkflowEngine
    
    engine = WorkflowEngine(db)
    pending = engine.get_pending_progressions(project_id)
    
    return [
        PendingItem(
            parcel_id=item["parcel_id"],
            project_id=item["project_id"],
            current_stage=item["current_stage"].value if hasattr(item["current_stage"], 'value') else item["current_stage"],
            target_stage=item["target_stage"],
            confidence=item["confidence"],
            reason=item["reason"],
            requires_review=item["requires_review"],
        )
        for item in pending
    ]


class EventResponse(BaseModel):
    """Response from triggering a workflow event."""
    queued: bool
    task_id: str
    parcel_id: str
    event_type: str
    message: str


@router.post("/event", response_model=EventResponse)
def trigger_workflow_event(
    request: EventRequest,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Trigger a workflow event that may cause stage progression.
    
    The event is processed asynchronously via Celery. Use the task_id
    to check status if needed.
    """
    authorize(persona, "parcel", Action.UPDATE)
    
    # Verify parcel exists before queuing
    parcel = db.query(models.Parcel).filter(models.Parcel.id == request.parcel_id).first()
    if not parcel:
        raise HTTPException(status_code=404, detail=f"Parcel not found: {request.parcel_id}")
    
    from app.tasks.workflow import process_workflow_event
    
    # Queue the task for async execution
    task = process_workflow_event.delay(
        request.event_type,
        request.parcel_id,
        request.event_data,
    )
    
    return EventResponse(
        queued=True,
        task_id=task.id,
        parcel_id=request.parcel_id,
        event_type=request.event_type,
        message=f"Event '{request.event_type}' queued for processing",
    )


@router.get("/parcel/{parcel_id}/history", response_model=list[HistoryItem])
def get_parcel_history(
    parcel_id: str,
    limit: int = 50,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get stage change history for a parcel."""
    authorize(persona, "parcel", Action.READ)
    
    parcel = db.query(models.Parcel).filter(models.Parcel.id == parcel_id).first()
    if not parcel:
        raise HTTPException(status_code=404, detail=f"Parcel not found: {parcel_id}")
    
    history = db.query(StatusChange).filter(
        StatusChange.parcel_id == parcel_id,
    ).order_by(StatusChange.occurred_at.desc()).limit(limit).all()
    
    return [
        HistoryItem(
            id=item.id,
            old_status=item.old_status,
            new_status=item.new_status,
            reason=item.reason,
            actor_persona=item.actor_persona.value if hasattr(item.actor_persona, 'value') else str(item.actor_persona),
            occurred_at=item.occurred_at,
        )
        for item in history
    ]


@router.get("/escalations")
def get_workflow_escalations(
    status: Optional[str] = "pending",
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get workflow escalations requiring attorney review."""
    authorize(persona, "parcel", Action.READ)
    
    from app.db.models import WorkflowEscalation
    
    query = db.query(WorkflowEscalation)
    if status:
        query = query.filter(WorkflowEscalation.status == status)
    
    escalations = query.order_by(WorkflowEscalation.created_at.desc()).limit(100).all()
    
    return {
        "escalations": [
            {
                "id": e.id,
                "parcel_id": e.parcel_id,
                "reason": e.reason,
                "priority": e.priority.value if hasattr(e.priority, 'value') else e.priority,
                "target_stage": e.target_stage,
                "status": e.status,
                "created_at": e.created_at,
            }
            for e in escalations
        ]
    }


@router.post("/escalations/{escalation_id}/resolve")
def resolve_escalation(
    escalation_id: str,
    action: str,  # "approve" or "reject"
    notes: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Resolve a workflow escalation by approving or rejecting the transition."""
    authorize(persona, "parcel", Action.APPROVE)
    
    from app.db.models import WorkflowEscalation
    from app.services.workflow_engine import WorkflowEngine, TransitionReason
    
    escalation = db.query(WorkflowEscalation).filter(WorkflowEscalation.id == escalation_id).first()
    if not escalation:
        raise HTTPException(status_code=404, detail=f"Escalation not found: {escalation_id}")
    
    if escalation.status != "pending":
        raise HTTPException(status_code=400, detail=f"Escalation already resolved: {escalation.status}")
    
    result = {"escalation_id": escalation_id, "action": action}
    
    if action == "approve":
        # Execute the transition
        parcel = db.query(models.Parcel).filter(models.Parcel.id == escalation.parcel_id).first()
        if parcel and escalation.target_stage:
            engine = WorkflowEngine(db)
            target_stage = ParcelStage(escalation.target_stage)
            transition_result = engine.execute_transition(
                parcel,
                target_stage,
                reason=TransitionReason.ESCALATION_RESOLVED,
                actor_persona=persona,
                notes=notes or f"Escalation {escalation_id} approved",
                skip_guards=True,
            )
            result["transition_success"] = transition_result.success
            result["to_stage"] = transition_result.to_stage.value if transition_result.to_stage else None
        
        escalation.status = "approved"
    else:
        escalation.status = "rejected"
    
    escalation.resolved_by = str(persona.value) if hasattr(persona, 'value') else str(persona)
    escalation.resolution_notes = notes
    escalation.resolved_at = datetime.utcnow()
    db.commit()
    
    result["status"] = escalation.status
    return result
