"""Attorney-in-the-loop AI orchestration with deterministic guardrails, RAG, and Gemini integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.config import get_settings
from app.services.rules_engine import evaluate_rules

logger = logging.getLogger(__name__)
settings = get_settings()

# Import RAG service (lazy to avoid circular imports)
_rag_service = None

def get_rag_service():
    """Lazy import RAG service."""
    global _rag_service
    if _rag_service is None:
        from app.services import rag_service
        _rag_service = rag_service
    return _rag_service

# Lazy load Vertex AI to avoid import errors when not in GCP
_gemini_model = None


def get_gemini_model():
    """Lazily initialize the Gemini model."""
    global _gemini_model
    if _gemini_model is None and settings.gemini_enabled:
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel, GenerationConfig
            
            # Initialize Vertex AI
            vertexai.init(
                project=settings.gcp_project or None,
                location=settings.gemini_location,
            )
            
            # Create model with safety settings for legal content
            _gemini_model = GenerativeModel(
                settings.gemini_model,
                generation_config=GenerationConfig(
                    max_output_tokens=settings.gemini_max_output_tokens,
                    temperature=settings.gemini_temperature,
                    top_p=0.8,
                    top_k=40,
                ),
            )
            logger.info(f"Initialized Gemini model: {settings.gemini_model}")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini model: {e}")
            _gemini_model = None
    return _gemini_model


@dataclass
class DraftResponse:
    template_id: str
    rationale: str
    suggestions: list[str]
    rule_results: list[dict[str, Any]]
    ai_summary: Optional[str] = None
    ai_analysis: Optional[dict[str, Any]] = None


@dataclass
class GeminiRequest:
    """Structured request for Gemini AI analysis."""
    jurisdiction: str
    payload: dict[str, Any]
    rule_results: list[dict[str, Any]]
    task_type: str = "draft_analysis"  # draft_analysis, risk_assessment, document_review
    rag_context: Optional[str] = None  # Pre-retrieved RAG context
    skip_rag: bool = False  # Skip RAG retrieval (if context already provided)


LEGAL_ANALYSIS_PROMPT = """You are a legal assistant specializing in eminent domain law. 
Analyze the following case information and provide insights.

IMPORTANT GUIDELINES:
- Do NOT provide legal advice or final legal conclusions
- Focus on factual analysis and procedural observations
- Flag items requiring attorney review
- Reference specific statutory citations when relevant
- Be concise and actionable
- Use the provided legal context to ground your analysis

Jurisdiction: {jurisdiction}

{legal_context}

Case Data:
{payload}

Rule Engine Results:
{rule_results}

Please provide:
1. A brief summary of the current case status (2-3 sentences)
2. Key observations from the rule engine results
3. Suggested next actions for the attorney to review
4. Any potential compliance concerns that need human review
5. Relevant citations from the legal context provided

Format your response as structured JSON with keys: summary, observations, suggested_actions, compliance_flags, citations
"""


DOCUMENT_REVIEW_PROMPT = """You are a legal document analyst specializing in eminent domain proceedings.
Review the following document information and extract key details.

IMPORTANT: This is for attorney review only. Do not make final determinations.

{legal_context}

Document Context:
{payload}

Please extract and structure:
1. Document type and purpose
2. Key dates and deadlines mentioned
3. Parties identified
4. Critical terms or conditions
5. Items requiring attorney attention
6. Relevant statutory requirements based on the legal context

Format as JSON with keys: doc_type, dates, parties, terms, attorney_review_items, statutory_requirements
"""


RISK_ASSESSMENT_PROMPT = """You are a risk analyst for eminent domain cases.
Assess the following case information for potential risks.

IMPORTANT: Flag items for attorney review. Do not make legal determinations.

Jurisdiction: {jurisdiction}

{legal_context}

Case Data:
{payload}

Rule Engine Findings:
{rule_results}

Provide a risk assessment with:
1. Overall risk level (low/medium/high) with reasoning
2. Specific risk factors identified
3. Compliance status based on rule results
4. Recommended mitigation steps for attorney review
5. Statutory basis for risk assessment (citing relevant law)

Format as JSON with keys: risk_level, risk_factors, compliance_status, mitigation_recommendations, statutory_basis
"""


async def retrieve_rag_context(
    query: str,
    jurisdiction: str = None,
) -> str:
    """Retrieve relevant legal context from the RAG knowledge base.
    
    Args:
        query: Search query (case summary or question)
        jurisdiction: Optional jurisdiction filter
        
    Returns:
        Formatted context string for inclusion in prompts
    """
    if not settings.rag_enabled:
        return "No legal context available (RAG disabled)."
    
    try:
        rag = get_rag_service()
        results = await rag.search_for_context(query, jurisdiction)
        return rag.format_context_for_prompt(results)
    except Exception as e:
        logger.warning(f"RAG retrieval failed: {e}")
        return "No legal context available (retrieval failed)."


async def call_gemini(request: GeminiRequest) -> Optional[dict[str, Any]]:
    """Call Gemini API with structured prompt based on task type.
    
    Now includes RAG-retrieved legal context for grounded analysis.
    """
    model = get_gemini_model()
    if model is None:
        logger.info("Gemini model not available, skipping AI analysis")
        return None
    
    # Retrieve RAG context if not provided and not skipped
    legal_context = request.rag_context
    if legal_context is None and not request.skip_rag:
        # Build search query from payload
        query_parts = []
        if request.jurisdiction:
            query_parts.append(f"{request.jurisdiction} eminent domain")
        if request.payload:
            # Extract key terms from payload
            if "parcel" in str(request.payload):
                query_parts.append("property compensation")
            if "deadline" in str(request.payload).lower():
                query_parts.append("statutory deadlines")
            if "offer" in str(request.payload).lower():
                query_parts.append("offer requirements")
        
        search_query = " ".join(query_parts) if query_parts else f"{request.jurisdiction} eminent domain procedures"
        legal_context = await retrieve_rag_context(search_query, request.jurisdiction)
    
    if legal_context is None:
        legal_context = "No legal context available."
    
    # Select prompt based on task type
    if request.task_type == "document_review":
        prompt = DOCUMENT_REVIEW_PROMPT.format(
            legal_context=legal_context,
            payload=str(request.payload),
        )
    elif request.task_type == "risk_assessment":
        prompt = RISK_ASSESSMENT_PROMPT.format(
            jurisdiction=request.jurisdiction,
            legal_context=legal_context,
            payload=str(request.payload),
            rule_results=str(request.rule_results),
        )
    else:  # draft_analysis
        prompt = LEGAL_ANALYSIS_PROMPT.format(
            jurisdiction=request.jurisdiction,
            legal_context=legal_context,
            payload=str(request.payload),
            rule_results=str(request.rule_results),
        )
    
    try:
        response = await model.generate_content_async(prompt)
        
        # Extract text from response
        if response.candidates and len(response.candidates) > 0:
            text = response.candidates[0].content.parts[0].text
            
            # Try to parse as JSON
            import json
            try:
                # Handle markdown code blocks
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                
                result = json.loads(text)
                # Add RAG context indicator
                result["_rag_context_used"] = legal_context != "No legal context available."
                return result
            except json.JSONDecodeError:
                # Return as raw text if not valid JSON
                return {"raw_response": text, "_rag_context_used": legal_context != "No legal context available."}
        
        return None
        
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        return None


def run_ai_pipeline(jurisdiction: str, payload: dict[str, Any]) -> DraftResponse:
    """
    Synchronous entry point for AI pipeline.
    Fan-out evaluation order: deterministic rules → optional Vertex summarization → response.
    """
    # Step 1: Run deterministic rules engine (always runs)
    rule_results = [result.__dict__ for result in evaluate_rules(jurisdiction, payload)]
    
    # Determine rationale from rules
    fired_rules = [r for r in rule_results if r.get("fired")]
    rationale = "Rules satisfied" if fired_rules else "Insufficient data for rule evaluation"
    
    # Step 2: Generate suggestions based on rule results
    suggestions = generate_suggestions(rule_results, payload)
    
    # Step 3: Attempt Gemini analysis (optional, graceful degradation)
    ai_summary = None
    ai_analysis = None
    
    if settings.gemini_enabled and settings.gcp_project:
        try:
            import asyncio
            
            request = GeminiRequest(
                jurisdiction=jurisdiction,
                payload=payload,
                rule_results=rule_results,
                task_type="draft_analysis",
            )
            
            # Run async in sync context
            loop = asyncio.new_event_loop()
            try:
                ai_analysis = loop.run_until_complete(call_gemini(request))
                if ai_analysis and "summary" in ai_analysis:
                    ai_summary = ai_analysis["summary"]
            finally:
                loop.close()
                
        except Exception as e:
            logger.warning(f"AI analysis failed, continuing without it: {e}")
    
    return DraftResponse(
        template_id="fol",
        rationale=rationale,
        suggestions=suggestions,
        rule_results=rule_results,
        ai_summary=ai_summary,
        ai_analysis=ai_analysis,
    )


async def run_ai_pipeline_async(
    jurisdiction: str, 
    payload: dict[str, Any],
    task_type: str = "draft_analysis"
) -> DraftResponse:
    """
    Async entry point for AI pipeline - preferred for web handlers.
    """
    # Step 1: Run deterministic rules engine
    rule_results = [result.__dict__ for result in evaluate_rules(jurisdiction, payload)]
    
    fired_rules = [r for r in rule_results if r.get("fired")]
    rationale = "Rules satisfied" if fired_rules else "Insufficient data for rule evaluation"
    
    # Step 2: Generate suggestions
    suggestions = generate_suggestions(rule_results, payload)
    
    # Step 3: Gemini analysis
    ai_summary = None
    ai_analysis = None
    
    if settings.gemini_enabled and settings.gcp_project:
        request = GeminiRequest(
            jurisdiction=jurisdiction,
            payload=payload,
            rule_results=rule_results,
            task_type=task_type,
        )
        ai_analysis = await call_gemini(request)
        if ai_analysis and "summary" in ai_analysis:
            ai_summary = ai_analysis["summary"]
    
    return DraftResponse(
        template_id="fol",
        rationale=rationale,
        suggestions=suggestions,
        rule_results=rule_results,
        ai_summary=ai_summary,
        ai_analysis=ai_analysis,
    )


def generate_suggestions(rule_results: list[dict], payload: dict) -> list[str]:
    """Generate actionable suggestions based on rule results and case data."""
    suggestions = []
    
    fired_rules = [r for r in rule_results if r.get("fired")]
    
    if fired_rules:
        suggestions.append("Attach good-faith binder snapshot")
        suggestions.append("Schedule counsel review of rule compliance")
        
        # Check for specific rule triggers
        for rule in fired_rules:
            rule_id = rule.get("rule_id", "")
            if "valuation" in rule_id.lower():
                suggestions.append("Verify appraisal documentation is complete")
            if "meeting" in rule_id.lower():
                suggestions.append("Confirm meeting notice was properly served")
            if "deadline" in rule_id.lower():
                suggestions.append("Review statutory deadline compliance")
    else:
        suggestions.append("Collect additional case data for rule evaluation")
        suggestions.append("Review jurisdiction requirements")
    
    # Add suggestions based on payload content
    if payload.get("parcel"):
        if not payload.get("parcel", {}).get("appraisal"):
            suggestions.append("Order property appraisal")
        if not payload.get("parcel", {}).get("title_search"):
            suggestions.append("Complete title search")
    
    return suggestions[:5]  # Limit to 5 most relevant suggestions
