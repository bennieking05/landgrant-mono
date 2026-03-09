"""API routes for AI Audit Trail.

Provides endpoints for:
- Viewing AI events and traces
- Replaying AI runs
- Cost analysis
- Citation verification
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel

from app.api.deps import get_current_persona
from app.db.models import Persona
from app.security.rbac import authorize, Action

router = APIRouter(prefix="/audit", tags=["audit"])


# Response models
class AIEventSummary(BaseModel):
    """Summary of an AI event."""
    id: str
    action: str
    model: str
    confidence: Optional[float]
    latency_ms: Optional[int]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    cost_estimate_usd: Optional[str]
    project_id: Optional[str]
    parcel_id: Optional[str]
    created_at: str


class AIEventTrace(BaseModel):
    """Full trace of an AI event."""
    event: dict[str, Any]
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    verification: dict[str, bool]


class CostSummary(BaseModel):
    """Cost summary for AI usage."""
    total_cost_usd: str
    total_events: int
    total_input_tokens: int
    total_output_tokens: int
    by_model: dict[str, str]
    by_action: dict[str, str]


class ReplayConfig(BaseModel):
    """Configuration to replay an AI event."""
    event_id: str
    original_timestamp: str
    model: str
    temperature: Optional[float]
    prompt_template_id: Optional[str]
    inputs: dict[str, Any]
    retrieval_set_ids: list[str]
    expected_outputs_hash: str


@router.get("/ai-events")
async def list_ai_events(
    persona: Persona = Depends(get_current_persona),
    project_id: Optional[str] = None,
    parcel_id: Optional[str] = None,
    action: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = Query(50, le=200),
):
    """List AI events with optional filters.
    
    Returns summary information for each event.
    Use GET /audit/ai-events/{id} for full trace.
    """
    authorize(persona, "audit", Action.READ)
    
    from app.services.ai_telemetry import AITelemetryService
    
    service = AITelemetryService()
    events = service.list_events(
        project_id=project_id,
        parcel_id=parcel_id,
        action=action,
        since=since,
        limit=limit,
    )
    
    return {
        "count": len(events),
        "events": [
            AIEventSummary(
                id=e.id,
                action=e.action,
                model=e.model,
                confidence=e.confidence,
                latency_ms=e.latency_ms,
                input_tokens=e.input_tokens,
                output_tokens=e.output_tokens,
                cost_estimate_usd=str(e.cost_estimate_usd) if e.cost_estimate_usd else None,
                project_id=e.project_id,
                parcel_id=e.parcel_id,
                created_at=e.created_at.isoformat(),
            )
            for e in events
        ],
    }


@router.get("/ai-events/{event_id}")
async def get_ai_event_trace(
    event_id: str,
    persona: Persona = Depends(get_current_persona),
):
    """Get full trace for an AI event.
    
    Includes complete inputs, outputs, and hash verification.
    """
    authorize(persona, "audit", Action.READ)
    
    from app.services.ai_telemetry import AITelemetryService
    
    service = AITelemetryService()
    trace = service.get_event_trace(event_id)
    
    if "error" in trace:
        raise HTTPException(status_code=404, detail=trace["error"])
    
    return AIEventTrace(
        event=trace["event"],
        inputs=trace["inputs"],
        outputs=trace["outputs"],
        verification=trace["verification"],
    )


@router.get("/ai-events/{event_id}/replay")
async def get_replay_config(
    event_id: str,
    persona: Persona = Depends(get_current_persona),
):
    """Get configuration to replay an AI event.
    
    Returns all information needed to reproduce
    the exact same AI call.
    """
    authorize(persona, "audit", Action.READ)
    
    from app.services.ai_telemetry import AITelemetryService
    
    service = AITelemetryService()
    config = service.get_replay_config(event_id)
    
    if "error" in config:
        raise HTTPException(status_code=404, detail=config["error"])
    
    return ReplayConfig(**config)


@router.get("/costs")
async def get_cost_summary(
    persona: Persona = Depends(get_current_persona),
    project_id: Optional[str] = None,
    since: Optional[datetime] = None,
):
    """Get cost summary for AI usage.
    
    Shows total costs broken down by model and action type.
    """
    authorize(persona, "audit", Action.READ)
    
    from app.services.ai_telemetry import AITelemetryService
    
    service = AITelemetryService()
    summary = service.get_cost_summary(
        project_id=project_id,
        since=since,
    )
    
    return CostSummary(**summary)


@router.get("/citations/{entity_type}/{entity_id}")
async def get_entity_citations(
    entity_type: str,
    entity_id: str,
    persona: Persona = Depends(get_current_persona),
):
    """Get all citations for an entity.
    
    Returns citations with full source information
    for audit verification.
    """
    authorize(persona, "audit", Action.READ)
    
    from app.services.citations import CitationService
    
    service = CitationService()
    citations = service.get_citations_for_entity(entity_type, entity_id)
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "citations_count": len(citations),
        "citations": citations,
    }


@router.post("/citations/verify")
async def verify_citations(
    ai_output: dict[str, Any],
    persona: Persona = Depends(get_current_persona),
):
    """Verify citations in an AI output.
    
    Checks that all claims have valid citations
    pointing to verified sources.
    """
    authorize(persona, "audit", Action.READ)
    
    from app.services.citations import CitationService, ClaimChecker
    
    citation_service = CitationService()
    checker = ClaimChecker(citation_service)
    
    result = checker.check_ai_output(ai_output)
    
    return result


@router.post("/sources")
async def create_source(
    title: str,
    jurisdiction: str,
    authority_level: str,
    citation_string: Optional[str] = None,
    url: Optional[str] = None,
    raw_text: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
):
    """Create a new source for citations.
    
    Sources are the authoritative documents that
    citations reference.
    """
    authorize(persona, "audit", Action.WRITE)
    
    from app.services.citations import CitationService, SourceInput
    
    service = CitationService()
    source = service.create_source(SourceInput(
        title=title,
        jurisdiction=jurisdiction,
        authority_level=authority_level,
        citation_string=citation_string,
        url=url,
        raw_text=raw_text,
    ))
    
    return source


@router.get("/sources")
async def search_sources(
    persona: Persona = Depends(get_current_persona),
    jurisdiction: Optional[str] = None,
    authority_level: Optional[str] = None,
    query: Optional[str] = None,
):
    """Search sources by criteria."""
    authorize(persona, "audit", Action.READ)
    
    from app.services.citations import CitationService
    
    service = CitationService()
    sources = service.search_sources(
        jurisdiction=jurisdiction,
        authority_level=authority_level,
        query=query,
    )
    
    return {
        "count": len(sources),
        "sources": sources,
    }


@router.post("/sources/{source_id}/verify")
async def verify_source(
    source_id: str,
    notes: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
):
    """Mark a source as verified.
    
    Verified sources are trusted for citation validation.
    """
    authorize(persona, "audit", Action.APPROVE)
    
    from app.services.citations import CitationService
    
    service = CitationService()
    
    try:
        source = service.verify_source(
            source_id=source_id,
            user_id=str(persona),
            notes=notes,
        )
        return source
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
