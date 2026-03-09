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

from app.api.deps import get_current_persona
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
async def run_agent(request: AgentRequest, persona: Persona = Depends(get_current_persona)):
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
        
        # Run with orchestration
        orchestrator = AgentOrchestrator()
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
    
    # Return mock data for now
    # In production, would query AIDecision table
    return [
        AIDecisionListItem(
            id="decision-001",
            agent_type="intake",
            project_id=project_id,
            parcel_id=parcel_id,
            confidence=0.85,
            flags=["authority_concern"],
            reviewed=False,
            review_outcome=None,
            occurred_at=datetime.utcnow(),
        ),
        AIDecisionListItem(
            id="decision-002",
            agent_type="valuation",
            project_id=project_id,
            parcel_id=parcel_id,
            confidence=0.92,
            flags=[],
            reviewed=True,
            review_outcome="approved",
            occurred_at=datetime.utcnow(),
        ),
    ]


@router.get("/decisions/{decision_id}")
async def get_ai_decision(
    decision_id: str,
    persona: Persona = Depends(get_current_persona),
):
    """Get details of a specific AI decision.
    
    Returns full context, result data, and explanation.
    """
    authorize(persona, "ai_agent", Action.READ)
    
    # Return mock data
    return {
        "id": decision_id,
        "agent_type": "intake",
        "project_id": "proj-001",
        "parcel_id": "parcel-001",
        "context": {
            "jurisdiction": "TX",
            "apn": "123-456-789",
        },
        "result_data": {
            "eligibility": True,
            "risk_score": 45,
        },
        "confidence": 0.85,
        "flags": ["authority_concern"],
        "explanation": "Case appears eligible but authority requires verification.",
        "reviewed_by": None,
        "reviewed_at": None,
        "review_outcome": None,
        "occurred_at": datetime.utcnow().isoformat(),
    }


@router.get("/escalations", response_model=list[EscalationListItem])
async def list_escalations(
    persona: Persona = Depends(get_current_persona),
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
    
    # Return mock data
    return [
        EscalationListItem(
            id="esc-001",
            ai_decision_id="decision-001",
            reason="low_confidence",
            priority="medium",
            status="open",
            created_at=datetime.utcnow(),
            context_summary="Case: proj-001 | Parcel: parcel-001 | Confidence: 0.72",
        ),
        EscalationListItem(
            id="esc-002",
            ai_decision_id="decision-003",
            reason="compliance_violation",
            priority="high",
            status="open",
            created_at=datetime.utcnow(),
            context_summary="Case: proj-002 | Deadline missed by 3 days",
        ),
    ]


@router.get("/escalations/{escalation_id}")
async def get_escalation(
    escalation_id: str,
    persona: Persona = Depends(get_current_persona),
):
    """Get details of a specific escalation request."""
    authorize(persona, "ai_agent", Action.READ)
    
    return {
        "id": escalation_id,
        "ai_decision_id": "decision-001",
        "reason": "low_confidence",
        "priority": "medium",
        "status": "open",
        "ai_decision": {
            "agent_type": "intake",
            "confidence": 0.72,
            "flags": ["authority_concern"],
            "result_data": {},
            "explanation": "Case eligibility uncertain - authority validation needed.",
        },
        "context_summary": "Case: proj-001 | Parcel: parcel-001",
        "assigned_to": None,
        "resolution": None,
        "created_at": datetime.utcnow().isoformat(),
        "resolved_at": None,
    }


@router.post("/escalations/{escalation_id}/resolve")
async def resolve_escalation(
    escalation_id: str,
    request: EscalationResolveRequest,
    persona: Persona = Depends(get_current_persona),
):
    """Resolve an escalation request.
    
    Outcomes:
    - approved: Accept the AI decision as-is
    - rejected: Reject the AI decision
    - modified: Accept with modifications
    """
    authorize(persona, "ai_agent", Action.APPROVE)
    
    # In production, would update database
    return {
        "escalation_id": escalation_id,
        "status": "resolved",
        "resolution": request.resolution,
        "outcome": request.outcome,
        "resolved_by": str(persona),
        "resolved_at": datetime.utcnow().isoformat(),
    }


@router.post("/escalations/{escalation_id}/assign")
async def assign_escalation(
    escalation_id: str,
    assignee_id: str = Query(...),
    persona: Persona = Depends(get_current_persona),
):
    """Assign an escalation to a reviewer."""
    authorize(persona, "ai_agent", Action.WRITE)
    
    return {
        "escalation_id": escalation_id,
        "assigned_to": assignee_id,
        "status": "in_review",
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
