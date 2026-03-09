"""Base agent classes and data structures for LandRight AI agents.

This module provides the foundation for all AI agents including:
- AgentResult: Standardized result structure with confidence scoring
- AgentContext: Input context for agent execution
- BaseAgent: Abstract base class with escalation logic
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Types of AI agents in the system."""
    INTAKE = "intake"
    COMPLIANCE = "compliance"
    VALUATION = "valuation"
    DOCGEN = "docgen"
    FILING = "filing"
    TITLE = "title"
    EDGE_CASE = "edge_case"


class EscalationReason(str, Enum):
    """Reasons for escalating to human review."""
    LOW_CONFIDENCE = "low_confidence"
    HIGH_RISK_FLAG = "high_risk_flag"
    CROSS_VERIFICATION_DISAGREEMENT = "cross_verification_disagreement"
    CONSTITUTIONAL_ISSUE = "constitutional_issue"
    LITIGATION_REQUIRED = "litigation_required"
    EDGE_CASE_DETECTED = "edge_case_detected"
    COMPLIANCE_VIOLATION = "compliance_violation"
    SYSTEM_ERROR = "system_error"


@dataclass
class AgentContext:
    """Input context for agent execution.
    
    Provides all necessary data for an agent to perform its task.
    Different agents use different subsets of these fields.
    """
    # Identifiers
    case_id: Optional[str] = None
    project_id: Optional[str] = None
    parcel_id: Optional[str] = None
    document_id: Optional[str] = None
    
    # Property identification
    apn: Optional[str] = None
    county_fips: Optional[str] = None
    
    # Jurisdiction
    jurisdiction: Optional[str] = None
    
    # Action/template context
    action: Optional[str] = None
    template_id: Optional[str] = None
    variables: Optional[dict[str, Any]] = None
    
    # Edge case context
    edge_case_type: Optional[str] = None
    
    # Filing context
    court_id: Optional[str] = None
    case_number: Optional[str] = None
    
    # Additional payload
    payload: Optional[dict[str, Any]] = None
    
    # Request metadata
    requested_by: Optional[str] = None
    requested_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for serialization."""
        return {
            k: v for k, v in {
                "case_id": self.case_id,
                "project_id": self.project_id,
                "parcel_id": self.parcel_id,
                "document_id": self.document_id,
                "apn": self.apn,
                "county_fips": self.county_fips,
                "jurisdiction": self.jurisdiction,
                "action": self.action,
                "template_id": self.template_id,
                "variables": self.variables,
                "edge_case_type": self.edge_case_type,
                "court_id": self.court_id,
                "case_number": self.case_number,
                "payload": self.payload,
                "requested_by": self.requested_by,
                "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            }.items() if v is not None
        }


@dataclass
class AgentResult:
    """Standardized result from agent execution.
    
    All agents return this structure to enable consistent
    handling by the orchestrator and audit logging.
    """
    # Execution status
    success: bool
    
    # Confidence scoring (0.0-1.0)
    confidence: float
    
    # Result data (agent-specific)
    data: dict[str, Any]
    
    # Escalation triggers
    flags: list[str] = field(default_factory=list)
    
    # Whether human review is required
    requires_review: bool = False
    
    # Audit/explanation payload
    audit_payload: dict[str, Any] = field(default_factory=dict)
    
    # Error information (if success=False)
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    # Execution metadata
    agent_type: Optional[str] = None
    execution_time_ms: Optional[int] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "success": self.success,
            "confidence": self.confidence,
            "data": self.data,
            "flags": self.flags,
            "requires_review": self.requires_review,
            "audit_payload": self.audit_payload,
            "error": self.error,
            "error_code": self.error_code,
            "agent_type": self.agent_type,
            "execution_time_ms": self.execution_time_ms,
        }
    
    @classmethod
    def success_result(
        cls,
        data: dict[str, Any],
        confidence: float = 1.0,
        flags: list[str] = None,
        requires_review: bool = False,
        audit_payload: dict[str, Any] = None,
    ) -> AgentResult:
        """Factory method for successful results."""
        return cls(
            success=True,
            confidence=confidence,
            data=data,
            flags=flags or [],
            requires_review=requires_review,
            audit_payload=audit_payload or {},
        )
    
    @classmethod
    def failure_result(
        cls,
        error: str,
        error_code: str = "AGENT_ERROR",
        data: dict[str, Any] = None,
    ) -> AgentResult:
        """Factory method for failed results."""
        return cls(
            success=False,
            confidence=0.0,
            data=data or {},
            flags=["execution_failed"],
            requires_review=True,
            error=error,
            error_code=error_code,
        )


class BaseAgent(ABC):
    """Abstract base class for all LandRight AI agents.
    
    Provides common functionality for:
    - Confidence threshold checking
    - Escalation determination
    - AI service integration
    - Audit logging
    
    Subclasses must implement the execute() method.
    """
    
    # Default confidence threshold for auto-approval
    confidence_threshold: float = 0.85
    
    # Agent type identifier
    agent_type: AgentType = None
    
    # Flags that always trigger escalation regardless of confidence
    critical_flags: list[str] = [
        "constitutional_issue",
        "litigation_required",
        "compliance_violation",
        "significant_discrepancy",
        "uneconomic_remnant_detected",
    ]
    
    def __init__(self, confidence_threshold: float = None):
        """Initialize the agent.
        
        Args:
            confidence_threshold: Override default threshold
        """
        if confidence_threshold is not None:
            self.confidence_threshold = confidence_threshold
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute the agent's primary task.
        
        Args:
            context: Input context for execution
            
        Returns:
            AgentResult with outcomes and confidence
        """
        pass
    
    def should_escalate(self, result: AgentResult) -> bool:
        """Determine if result should be escalated for human review.
        
        Escalation triggers:
        1. Confidence below threshold
        2. Result already marked for review
        3. Critical flags present
        
        Args:
            result: Agent execution result
            
        Returns:
            True if escalation needed
        """
        # Always escalate if explicitly required
        if result.requires_review:
            return True
        
        # Escalate if confidence is below threshold
        if result.confidence < self.confidence_threshold:
            self.logger.info(
                f"Escalating due to low confidence: {result.confidence:.2f} < {self.confidence_threshold:.2f}"
            )
            return True
        
        # Escalate if any critical flags are present
        for flag in result.flags:
            if flag in self.critical_flags:
                self.logger.info(f"Escalating due to critical flag: {flag}")
                return True
        
        return False
    
    def get_escalation_reason(self, result: AgentResult) -> EscalationReason:
        """Determine the primary reason for escalation.
        
        Args:
            result: Agent execution result
            
        Returns:
            Primary escalation reason
        """
        if not result.success:
            return EscalationReason.SYSTEM_ERROR
        
        for flag in result.flags:
            if flag == "constitutional_issue":
                return EscalationReason.CONSTITUTIONAL_ISSUE
            if flag == "litigation_required":
                return EscalationReason.LITIGATION_REQUIRED
            if flag == "compliance_violation":
                return EscalationReason.COMPLIANCE_VIOLATION
            if flag in ["edge_case_detected", "business_relocation", "partial_taking"]:
                return EscalationReason.EDGE_CASE_DETECTED
            if flag == "significant_discrepancy":
                return EscalationReason.HIGH_RISK_FLAG
        
        if result.confidence < self.confidence_threshold:
            return EscalationReason.LOW_CONFIDENCE
        
        return EscalationReason.HIGH_RISK_FLAG
    
    async def retrieve_context(
        self,
        query: str,
        jurisdiction: str = None,
        top_k: int = 5,
    ) -> str:
        """Retrieve relevant legal context from the RAG knowledge base.
        
        Args:
            query: Search query (case summary or question)
            jurisdiction: Optional jurisdiction filter
            top_k: Number of results to retrieve
            
        Returns:
            Formatted context string for use in prompts
        """
        try:
            from app.services.rag_service import search_for_context, format_context_for_prompt
            
            results = await search_for_context(query, jurisdiction, top_k)
            return format_context_for_prompt(results)
            
        except Exception as e:
            self.logger.warning(f"RAG context retrieval failed: {e}")
            return "No legal context available."
    
    async def call_ai(
        self,
        prompt: str,
        task_type: str = "analysis",
        temperature: float = None,
        jurisdiction: str = None,
        include_rag_context: bool = True,
    ) -> Optional[dict[str, Any]]:
        """Call Gemini AI for analysis with optional RAG context.
        
        Args:
            prompt: Prompt to send to AI
            task_type: Type of task for logging
            temperature: Override default temperature
            jurisdiction: Jurisdiction for RAG filtering
            include_rag_context: Whether to include RAG context
            
        Returns:
            AI response as dict, or None if unavailable
        """
        try:
            from app.services.ai_pipeline import call_gemini, GeminiRequest
            
            # Retrieve RAG context if requested
            rag_context = None
            if include_rag_context:
                rag_context = await self.retrieve_context(prompt[:500], jurisdiction)
            
            request = GeminiRequest(
                jurisdiction=jurisdiction or "",
                payload={"prompt": prompt},
                rule_results=[],
                task_type=task_type,
                rag_context=rag_context,
                skip_rag=True,  # We already retrieved context
            )
            
            response = await call_gemini(request)
            return response
            
        except Exception as e:
            self.logger.warning(f"AI call failed: {e}")
            return None
    
    def _create_audit_payload(
        self,
        context: AgentContext,
        result: AgentResult,
        additional: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Create audit payload for logging.
        
        Args:
            context: Execution context
            result: Execution result
            additional: Additional audit data
            
        Returns:
            Complete audit payload
        """
        payload = {
            "agent_type": self.agent_type.value if self.agent_type else self.__class__.__name__,
            "context": context.to_dict(),
            "confidence": result.confidence,
            "flags": result.flags,
            "escalated": self.should_escalate(result),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if additional:
            payload.update(additional)
        
        # Add explanation if available
        if "explanation" in result.audit_payload:
            payload["explanation"] = result.audit_payload["explanation"]
        
        return payload
