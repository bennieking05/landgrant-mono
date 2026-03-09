from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from app.api.deps import get_current_persona
from app.db.models import Persona
from app.security.rbac import authorize, Action
from app.services.ai_pipeline import run_ai_pipeline, run_ai_pipeline_async
from pydantic import BaseModel

router = APIRouter(prefix="/ai", tags=["ai"])


class DraftRequest(BaseModel):
    jurisdiction: str
    payload: dict
    task_type: Optional[str] = "draft_analysis"  # draft_analysis, risk_assessment, document_review


class DraftResponse(BaseModel):
    jurisdiction: str
    template_id: str
    rationale: str
    rule_results: list[dict]
    suggestions: list[str]
    next_actions: list[str]
    ai_summary: Optional[str] = None
    ai_analysis: Optional[dict] = None


@router.post("/drafts", response_model=DraftResponse)
def generate_draft(request: DraftRequest, persona: Persona = Depends(get_current_persona)):
    """
    Generate AI-assisted draft analysis for eminent domain cases.
    
    The pipeline runs:
    1. Deterministic rules engine (always runs)
    2. Gemini AI analysis (optional, graceful degradation if unavailable)
    
    Task types:
    - draft_analysis: General case analysis and recommendations
    - risk_assessment: Risk evaluation for the case
    - document_review: Document extraction and analysis
    """
    authorize(persona, "template", Action.EXECUTE)
    response = run_ai_pipeline(request.jurisdiction, request.payload)
    summary = [result for result in response.rule_results if result.get("fired")]
    
    return DraftResponse(
        jurisdiction=request.jurisdiction,
        template_id=response.template_id,
        rationale=response.rationale,
        rule_results=summary,
        suggestions=response.suggestions,
        next_actions=["legal_review", "binder_update"] if summary else ["collect_more_data"],
        ai_summary=response.ai_summary,
        ai_analysis=response.ai_analysis,
    )


@router.post("/drafts/async", response_model=DraftResponse)
async def generate_draft_async(request: DraftRequest, persona: Persona = Depends(get_current_persona)):
    """
    Async version of draft generation - preferred for better performance.
    """
    authorize(persona, "template", Action.EXECUTE)
    response = await run_ai_pipeline_async(
        request.jurisdiction, 
        request.payload,
        task_type=request.task_type or "draft_analysis"
    )
    summary = [result for result in response.rule_results if result.get("fired")]
    
    return DraftResponse(
        jurisdiction=request.jurisdiction,
        template_id=response.template_id,
        rationale=response.rationale,
        rule_results=summary,
        suggestions=response.suggestions,
        next_actions=["legal_review", "binder_update"] if summary else ["collect_more_data"],
        ai_summary=response.ai_summary,
        ai_analysis=response.ai_analysis,
    )


@router.get("/health")
def ai_health():
    """Check if AI services are available."""
    from app.core.config import get_settings
    settings = get_settings()
    
    return {
        "gemini_enabled": settings.gemini_enabled,
        "gemini_model": settings.gemini_model,
        "gcp_project_configured": bool(settings.gcp_project),
    }
