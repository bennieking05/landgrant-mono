"""AI Agent package for LandRight.

This package contains specialized agents for automating eminent domain workflows:

- IntakeAgent: Case intake and eligibility evaluation
- ComplianceAgent: State-specific compliance checking
- ValuationAgent: Appraisal cross-checking and compensation calculation
- DocGenAgent: Document generation with AI enhancement
- FilingAgent: Deadline monitoring and e-filing
- TitleAgent: Title search and OCR analysis
- EdgeCaseAgent: Special scenario handling

All agents follow the attorney-in-the-loop pattern with:
- Confidence thresholds for escalation
- Comprehensive audit logging
- Human review gates for critical decisions
"""

from app.agents.base import (
    BaseAgent,
    AgentResult,
    AgentContext,
)
from app.agents.orchestrator import AgentOrchestrator, OrchestratedResult

__all__ = [
    "BaseAgent",
    "AgentResult",
    "AgentContext",
    "AgentOrchestrator",
    "OrchestratedResult",
]
