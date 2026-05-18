"""API routes for AI agents.

This module provides endpoints for:
- Running agent analyses
- Viewing AI decisions
- Managing escalation requests
- Resolving reviews
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_db
from app.db.models import Persona
from app.security.rbac import authorize, Action

router = APIRouter(prefix="/agents", tags=["agents"])


# Request/Response models
class AgentRequest(BaseModel):
    """Request to run an agent."""

    agent_type: str  # intake, compliance, valuation, docgen, filing, title, edge_case
    case_id: Optional[str] = None
    project_id: Optional[str] = None
    parcel_id: Optional[str] = None
    document_id: Optional[str] = None
    jurisdiction: Optional[str] = None
    action: Optional[str] = None
    payload: Optional[dict[str, Any]] = None


class AgentResponse(BaseModel):
    """Response from agent execution."""

    success: bool
    confidence: float
    data: dict[str, Any]
    flags: list[str]
    requires_review: bool
    decision_id: Optional[str] = None
    escalation_id: Optional[str] = None


class EscalationListItem(BaseModel):
    """Escalation request list item."""

    id: str
    ai_decision_id: str
    reason: str
    priority: str
    status: str
    created_at: datetime
    context_summary: Optional[str] = None


class EscalationResolveRequest(BaseModel):
    """Request to resolve an escalation."""

    resolution: str
    outcome: str = "approved"  # approved, rejected, modified


class AIDecisionListItem(BaseModel):
    """AI decision list item."""

    id: str
    agent_type: str
    project_id: Optional[str]
    parcel_id: Optional[str]
    confidence: float
    flags: list[str]
    reviewed: bool
    review_outcome: Optional[str]
    occurred_at: datetime


@router.post("/run", response_model=AgentResponse)
async def run_agent(
    request: AgentRequest,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Run an AI agent for analysis.

    Supported agent types:
    - intake: Case eligibility and property data
    - compliance: State-specific compliance checking
    - valuation: Appraisal cross-check and compensation
    - docgen: Document generation
    - filing: Deadline monitoring and e-filing
    - title: Title search and OCR analysis
    - edge_case: Special scenario handling
    """
    authorize(persona, "ai_agent", Action.EXECUTE)

    try:
        from app.agents.orchestrator import AgentOrchestrator
        from app.agents.base import AgentContext

        # Build context
        context = AgentContext(
            case_id=request.case_id,
            project_id=request.project_id,
            parcel_id=request.parcel_id,
            document_id=request.document_id,
            jurisdiction=request.jurisdiction,
            action=request.action,
            payload=request.payload,
            requested_by=str(persona),
        )

        # Get agent
        agent = _get_agent(request.agent_type)

        orchestrator = AgentOrchestrator(db_session=db)
        result = await orchestrator.execute_with_oversight(agent, context)

        return AgentResponse(
            success=result.result.success if result.result else False,
            confidence=result.result.confidence if result.result else 0.0,
            data=result.result.data if result.result else {},
            flags=result.result.flags if result.result else [],
            requires_review=result.status == "pending_review",
            decision_id=result.decision_id,
            escalation_id=result.escalation.id if result.escalation else None,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")


@router.get("/decisions", response_model=list[AIDecisionListItem])
async def list_ai_decisions(
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    project_id: Optional[str] = Query(None),
    parcel_id: Optional[str] = Query(None),
    agent_type: Optional[str] = Query(None),
    pending_review: Optional[bool] = Query(None),
    limit: int = Query(50, le=100),
):
    """List AI decisions with optional filters.

    Used by counsel to review agent decisions and their outcomes.
    """
    authorize(persona, "ai_agent", Action.READ)

    from app.db import models

    q = db.query(models.AIDecision)
    if project_id:
        q = q.filter(models.AIDecision.project_id == project_id)
    if parcel_id:
        q = q.filter(models.AIDecision.parcel_id == parcel_id)
    if agent_type:
        q = q.filter(models.AIDecision.agent_type == agent_type)
    if pending_review is True:
        q = q.filter(models.AIDecision.reviewed_at.is_(None))
    if pending_review is False:
        q = q.filter(models.AIDecision.reviewed_at.isnot(None))

    rows = q.order_by(models.AIDecision.occurred_at.desc()).limit(limit).all()
    return [
        AIDecisionListItem(
            id=r.id,
            agent_type=r.agent_type,
            project_id=r.project_id,
            parcel_id=r.parcel_id,
            confidence=float(r.confidence) if r.confidence is not None else 0.0,
            flags=list(r.flags or []),
            reviewed=r.reviewed_at is not None,
            review_outcome=r.review_outcome,
            occurred_at=r.occurred_at or datetime.utcnow(),
        )
        for r in rows
    ]


@router.get("/decisions/{decision_id}")
async def get_ai_decision(
    decision_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get details of a specific AI decision.

    Returns full context, result data, and explanation.
    """
    authorize(persona, "ai_agent", Action.READ)

    from app.db import models

    row = db.get(models.AIDecision, decision_id)
    if row is None:
        raise HTTPException(status_code=404, detail="AI decision not found")

    return {
        "id": row.id,
        "agent_type": row.agent_type,
        "project_id": row.project_id,
        "parcel_id": row.parcel_id,
        "context_hash": row.context_hash,
        "result_data": row.result_data,
        "confidence": float(row.confidence) if row.confidence is not None else None,
        "flags": list(row.flags or []),
        "explanation": row.explanation,
        "reviewed_by": row.reviewed_by,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "review_outcome": row.review_outcome,
        "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
        "hash": row.hash,
    }


@router.get("/escalations", response_model=list[EscalationListItem])
async def list_escalations(
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
):
    """List escalation requests requiring human review.

    Filters:
    - status: open, in_review, resolved
    - priority: low, medium, high, critical
    """
    authorize(persona, "ai_agent", Action.READ)

    from app.db import models

    q = db.query(models.EscalationRequest)
    if status:
        q = q.filter(models.EscalationRequest.status == status)
    if priority:
        q = q.filter(models.EscalationRequest.priority == priority)

    rows = q.order_by(models.EscalationRequest.created_at.desc()).limit(limit).all()
    return [
        EscalationListItem(
            id=r.id,
            ai_decision_id=r.ai_decision_id,
            reason=r.reason,
            priority=r.priority,
            status=r.status,
            created_at=r.created_at or datetime.utcnow(),
            context_summary=None,
        )
        for r in rows
    ]


@router.get("/escalations/{escalation_id}")
async def get_escalation(
    escalation_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get details of a specific escalation request."""
    authorize(persona, "ai_agent", Action.READ)

    from app.db import models

    row = db.get(models.EscalationRequest, escalation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Escalation not found")

    decision = row.ai_decision
    decision_payload = None
    if decision is not None:
        decision_payload = {
            "agent_type": decision.agent_type,
            "confidence": (
                float(decision.confidence) if decision.confidence is not None else None
            ),
            "flags": list(decision.flags or []),
            "result_data": decision.result_data,
            "explanation": decision.explanation,
        }

    return {
        "id": row.id,
        "ai_decision_id": row.ai_decision_id,
        "reason": row.reason,
        "priority": row.priority,
        "status": row.status,
        "ai_decision": decision_payload,
        "assigned_to": row.assigned_to,
        "resolution": row.resolution,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
    }


@router.post("/escalations/{escalation_id}/resolve")
async def resolve_escalation(
    escalation_id: str,
    request: EscalationResolveRequest,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Resolve an escalation request.

    Outcomes:
    - approved: Accept the AI decision as-is
    - rejected: Reject the AI decision
    - modified: Accept with modifications
    """
    authorize(persona, "ai_agent", Action.APPROVE)

    from app.db import models

    row = db.get(models.EscalationRequest, escalation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Escalation not found")

    row.status = "resolved"
    row.resolution = request.resolution
    row.resolved_at = datetime.utcnow()

    decision = row.ai_decision
    if decision is not None:
        # ``reviewed_by`` has a FK to ``users.id``. Dev/persona-only auth does
        # not carry a concrete user id, so we only set it when the persona
        # principal matches a real row; otherwise we leave it null to avoid
        # a FK violation on commit.
        from app.db import models

        persona_value = persona.value if hasattr(persona, "value") else str(persona)
        user_row = db.query(models.User).filter_by(persona=persona).first()
        decision.reviewed_by = user_row.id if user_row else None
        decision.reviewed_at = datetime.utcnow()
        decision.review_outcome = request.outcome
    else:
        persona_value = persona.value if hasattr(persona, "value") else str(persona)
    db.commit()

    return {
        "escalation_id": row.id,
        "status": row.status,
        "resolution": row.resolution,
        "outcome": request.outcome,
        "resolved_by": persona_value,
        "resolved_at": row.resolved_at.isoformat(),
    }


@router.post("/escalations/{escalation_id}/assign")
async def assign_escalation(
    escalation_id: str,
    assignee_id: str = Query(...),
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Assign an escalation to a reviewer."""
    authorize(persona, "ai_agent", Action.WRITE)

    from app.db import models

    row = db.get(models.EscalationRequest, escalation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Escalation not found")

    # ``assigned_to`` has a FK to ``users.id``; reject unknown assignees with a
    # clean 404 instead of letting the FK violation propagate as a 500.
    assignee = db.get(models.User, assignee_id)
    if assignee is None:
        raise HTTPException(
            status_code=404,
            detail=f"Assignee not found: {assignee_id}",
        )

    row.assigned_to = assignee_id
    row.status = "in_review"
    db.commit()

    return {
        "escalation_id": row.id,
        "assigned_to": row.assigned_to,
        "status": row.status,
    }


# Helper functions
def _get_agent(agent_type: str):
    """Get agent instance by type."""
    if agent_type == "intake":
        from app.agents.intake_agent import IntakeAgent

        return IntakeAgent()
    elif agent_type == "compliance":
        from app.agents.compliance_agent import ComplianceAgent

        return ComplianceAgent()
    elif agent_type == "valuation":
        from app.agents.valuation_agent import ValuationAgent

        return ValuationAgent()
    elif agent_type == "docgen":
        from app.agents.docgen_agent import DocGenAgent

        return DocGenAgent()
    elif agent_type == "filing":
        from app.agents.filing_agent import FilingAgent

        return FilingAgent()
    elif agent_type == "title":
        from app.agents.title_agent import TitleAgent

        return TitleAgent()
    elif agent_type == "edge_case":
        from app.agents.edge_case_agent import EdgeCaseAgent

        return EdgeCaseAgent()
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")
