"""Agent orchestrator for coordinating AI agent execution with oversight.

This module provides:
- Central coordination of agent execution
- Confidence-based escalation management
- Cross-verification between agents
- Audit logging of all AI decisions
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING
from uuid import uuid4

from app.agents.base import (
    BaseAgent,
    AgentContext,
    AgentResult,
    EscalationReason,
)
from app.services.hashing import sha256_hex

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class OrchestratedResult:
    """Result from orchestrated agent execution.
    
    Wraps the agent result with orchestration metadata
    including escalation status and audit information.
    """
    # Agent result
    result: Optional[AgentResult]
    
    # Orchestration status
    status: str  # "approved", "pending_review", "failed"
    
    # Escalation info (if applicable)
    escalation: Optional[EscalationInfo] = None
    
    # Decision ID for audit trail
    decision_id: Optional[str] = None
    
    # Cross-verification results (if applicable)
    verification_results: Optional[list[AgentResult]] = None
    
    # Consensus status for cross-verification
    consensus: Optional[ConsensusResult] = None


@dataclass
class EscalationInfo:
    """Information about an escalation request."""
    id: str
    reason: EscalationReason
    priority: str  # "low", "medium", "high", "critical"
    assigned_to: Optional[str] = None
    context_summary: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConsensusResult:
    """Result of cross-verification consensus check."""
    agreed: bool
    agreement_score: float  # 0.0-1.0
    primary_confidence: float
    verification_confidences: list[float]
    disagreement_points: list[str] = field(default_factory=list)


class AgentOrchestrator:
    """Central coordinator for AI agent execution with oversight.
    
    Responsibilities:
    - Execute agents with standardized handling
    - Manage confidence-based escalation
    - Coordinate cross-verification between agents
    - Log all AI decisions for audit
    - Create escalation requests for human review
    
    Usage:
        orchestrator = AgentOrchestrator()
        result = await orchestrator.execute_with_oversight(
            agent=IntakeAgent(),
            context=AgentContext(case_id="...", jurisdiction="TX"),
            verification_agents=[ComplianceAgent()],  # Optional
        )
    """
    
    def __init__(self, db_session: AsyncSession = None):
        """Initialize orchestrator.
        
        Args:
            db_session: Optional async database session for persistence
        """
        self.db = db_session
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def execute_with_oversight(
        self,
        primary_agent: BaseAgent,
        context: AgentContext,
        verification_agents: list[BaseAgent] = None,
        require_consensus: bool = False,
    ) -> OrchestratedResult:
        """Execute an agent with full oversight and optional cross-verification.
        
        Args:
            primary_agent: Main agent to execute
            context: Execution context
            verification_agents: Optional agents for cross-verification
            require_consensus: If True, disagreement blocks auto-approval
            
        Returns:
            OrchestratedResult with status and escalation info
        """
        start_time = datetime.utcnow()
        
        try:
            # 1. Execute primary agent
            self.logger.info(f"Executing {primary_agent.__class__.__name__}")
            primary_result = await primary_agent.execute(context)
            primary_result.agent_type = primary_agent.__class__.__name__
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            primary_result.execution_time_ms = int(execution_time)
            
            # 2. Log the decision
            decision_id = await self._log_decision(primary_agent, context, primary_result)
            
            # 3. Check if escalation is needed
            if primary_result.requires_review or primary_agent.should_escalate(primary_result):
                escalation = await self._create_escalation(
                    decision_id=decision_id,
                    result=primary_result,
                    agent=primary_agent,
                    context=context,
                )
                return OrchestratedResult(
                    result=primary_result,
                    status="pending_review",
                    escalation=escalation,
                    decision_id=decision_id,
                )
            
            # 4. Cross-verification (if configured)
            if verification_agents:
                consensus = await self._cross_verify(
                    primary_result=primary_result,
                    verification_agents=verification_agents,
                    context=context,
                )
                
                if not consensus.agreed and require_consensus:
                    escalation = await self._create_escalation(
                        decision_id=decision_id,
                        result=primary_result,
                        agent=primary_agent,
                        context=context,
                        reason=EscalationReason.CROSS_VERIFICATION_DISAGREEMENT,
                    )
                    return OrchestratedResult(
                        result=primary_result,
                        status="pending_review",
                        escalation=escalation,
                        decision_id=decision_id,
                        consensus=consensus,
                    )
            
            # 5. Auto-approved
            self.logger.info(
                f"Agent {primary_agent.__class__.__name__} auto-approved "
                f"(confidence={primary_result.confidence:.2f})"
            )
            return OrchestratedResult(
                result=primary_result,
                status="approved",
                decision_id=decision_id,
            )
            
        except Exception as e:
            self.logger.error(f"Agent execution failed: {e}", exc_info=True)
            
            # Create failure result
            failure_result = AgentResult.failure_result(
                error=str(e),
                error_code="EXECUTION_ERROR",
            )
            
            # Log the failure
            decision_id = await self._log_decision(primary_agent, context, failure_result)
            
            # Create escalation for failure
            escalation = await self._create_escalation(
                decision_id=decision_id,
                result=failure_result,
                agent=primary_agent,
                context=context,
                reason=EscalationReason.SYSTEM_ERROR,
                priority="high",
            )
            
            return OrchestratedResult(
                result=failure_result,
                status="failed",
                escalation=escalation,
                decision_id=decision_id,
            )
    
    async def _log_decision(
        self,
        agent: BaseAgent,
        context: AgentContext,
        result: AgentResult,
    ) -> str:
        """Create audit-grade decision log.
        
        Args:
            agent: Agent that executed
            context: Execution context
            result: Execution result
            
        Returns:
            Decision ID
        """
        decision_id = str(uuid4())
        
        # Create decision record
        decision_data = {
            "id": decision_id,
            "agent_type": agent.__class__.__name__,
            "context": context.to_dict(),
            "result": result.to_dict(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Compute hash for tamper evidence
        decision_hash = sha256_hex(json.dumps(decision_data, sort_keys=True, default=str))
        
        # Persist to database if session available
        if self.db:
            try:
                from app.db.models import AIDecision
                
                ai_decision = AIDecision(
                    id=decision_id,
                    agent_type=agent.__class__.__name__,
                    project_id=context.project_id,
                    parcel_id=context.parcel_id,
                    context_hash=sha256_hex(json.dumps(context.to_dict(), default=str)),
                    result_data=result.to_dict(),
                    confidence=result.confidence,
                    flags=result.flags,
                    explanation=result.audit_payload.get("explanation"),
                    occurred_at=datetime.utcnow(),
                    hash=decision_hash,
                )
                self.db.add(ai_decision)
                await self.db.commit()
                
            except Exception as e:
                self.logger.warning(f"Failed to persist decision: {e}")
        
        self.logger.info(f"Logged AI decision: {decision_id} (hash={decision_hash[:16]}...)")
        return decision_id
    
    async def _create_escalation(
        self,
        decision_id: str,
        result: AgentResult,
        agent: BaseAgent,
        context: AgentContext,
        reason: EscalationReason = None,
        priority: str = None,
    ) -> EscalationInfo:
        """Create an escalation request for human review.
        
        Args:
            decision_id: Related AI decision ID
            result: Agent result
            agent: Agent that executed
            context: Execution context
            reason: Override escalation reason
            priority: Override priority
            
        Returns:
            EscalationInfo with request details
        """
        escalation_id = str(uuid4())
        
        # Determine reason and priority
        if reason is None:
            reason = agent.get_escalation_reason(result)
        
        if priority is None:
            priority = self._determine_priority(reason, result)
        
        # Generate context summary
        context_summary = self._generate_context_summary(context, result)
        
        escalation = EscalationInfo(
            id=escalation_id,
            reason=reason,
            priority=priority,
            context_summary=context_summary,
            created_at=datetime.utcnow(),
        )
        
        # Persist to database if session available
        if self.db:
            try:
                from app.db.models import EscalationRequest
                
                escalation_record = EscalationRequest(
                    id=escalation_id,
                    ai_decision_id=decision_id,
                    reason=reason.value,
                    priority=priority,
                    status="open",
                    created_at=datetime.utcnow(),
                )
                self.db.add(escalation_record)
                await self.db.commit()
                
            except Exception as e:
                self.logger.warning(f"Failed to persist escalation: {e}")
        
        self.logger.info(
            f"Created escalation: {escalation_id} "
            f"(reason={reason.value}, priority={priority})"
        )
        
        # Trigger notification to reviewers
        await self._notify_escalation(escalation, context, result)
        
        return escalation
    
    async def _notify_escalation(
        self,
        escalation: EscalationInfo,
        context: AgentContext,
        result: AgentResult,
    ) -> None:
        """Send notifications for a new escalation.
        
        Triggers alerts via:
        - Celery task for email/SMS
        - Real-time websocket (if available)
        
        Args:
            escalation: Escalation info
            context: Execution context
            result: Agent result
        """
        try:
            from app.tasks.notifications import send_escalation_alert
            
            # Get reviewers based on priority and context
            reviewer_ids = await self._get_escalation_reviewers(
                escalation.priority,
                context.project_id,
            )
            
            if reviewer_ids:
                # Queue notification task (async, non-blocking)
                send_escalation_alert.delay(
                    escalation_id=escalation.id,
                    recipient_ids=reviewer_ids,
                    priority=escalation.priority,
                )
                
                self.logger.info(
                    f"Queued escalation notification for {len(reviewer_ids)} reviewers"
                )
            else:
                self.logger.warning("No reviewers found for escalation notification")
                
        except Exception as e:
            # Don't fail the escalation if notification fails
            self.logger.warning(f"Failed to send escalation notification: {e}")
    
    async def _get_escalation_reviewers(
        self,
        priority: str,
        project_id: str = None,
    ) -> list[str]:
        """Get list of reviewer IDs for an escalation.
        
        Args:
            priority: Escalation priority
            project_id: Optional project to scope reviewers
            
        Returns:
            List of user IDs to notify
        """
        if not self.db:
            return []
        
        try:
            from app.db.models import User, Persona
            from sqlalchemy import select
            
            # Get in-house counsel users
            query = select(User).where(User.persona == Persona.IN_HOUSE_COUNSEL)
            
            result = await self.db.execute(query)
            users = result.scalars().all()
            
            reviewer_ids = [u.id for u in users]
            
            # For critical escalations, also notify admin/supervisors
            if priority == "critical":
                admin_query = select(User).where(User.persona == Persona.ADMIN)
                admin_result = await self.db.execute(admin_query)
                admins = admin_result.scalars().all()
                reviewer_ids.extend([a.id for a in admins])
            
            return list(set(reviewer_ids))  # Dedupe
            
        except Exception as e:
            self.logger.warning(f"Failed to get reviewers: {e}")
            return []
    
    async def _cross_verify(
        self,
        primary_result: AgentResult,
        verification_agents: list[BaseAgent],
        context: AgentContext,
    ) -> ConsensusResult:
        """Run cross-verification with multiple agents.
        
        Args:
            primary_result: Result from primary agent
            verification_agents: Agents for verification
            context: Execution context
            
        Returns:
            ConsensusResult with agreement status
        """
        self.logger.info(f"Running cross-verification with {len(verification_agents)} agents")
        
        # Execute verification agents in parallel
        verification_results = await asyncio.gather(*[
            agent.execute(context) for agent in verification_agents
        ], return_exceptions=True)
        
        # Filter out exceptions
        valid_results = [
            r for r in verification_results 
            if isinstance(r, AgentResult)
        ]
        
        if not valid_results:
            return ConsensusResult(
                agreed=False,
                agreement_score=0.0,
                primary_confidence=primary_result.confidence,
                verification_confidences=[],
                disagreement_points=["All verification agents failed"],
            )
        
        # Check for consensus
        verification_confidences = [r.confidence for r in valid_results]
        avg_verification_confidence = sum(verification_confidences) / len(verification_confidences)
        
        # Check if all agents agree on success/failure
        all_success = primary_result.success and all(r.success for r in valid_results)
        
        # Check if confidences are similar (within 0.15)
        confidence_spread = abs(primary_result.confidence - avg_verification_confidence)
        confidence_similar = confidence_spread < 0.15
        
        # Check for conflicting flags
        primary_flags = set(primary_result.flags)
        verification_flags = set()
        for r in valid_results:
            verification_flags.update(r.flags)
        conflicting_flags = primary_flags.symmetric_difference(verification_flags)
        
        # Determine agreement
        agreed = all_success and confidence_similar and len(conflicting_flags) == 0
        
        # Calculate agreement score
        agreement_score = 1.0
        if not all_success:
            agreement_score -= 0.3
        if not confidence_similar:
            agreement_score -= 0.3
        if conflicting_flags:
            agreement_score -= 0.1 * len(conflicting_flags)
        agreement_score = max(0.0, agreement_score)
        
        return ConsensusResult(
            agreed=agreed,
            agreement_score=agreement_score,
            primary_confidence=primary_result.confidence,
            verification_confidences=verification_confidences,
            disagreement_points=list(conflicting_flags) if conflicting_flags else [],
        )
    
    def _determine_priority(self, reason: EscalationReason, result: AgentResult) -> str:
        """Determine escalation priority based on reason and result.
        
        Args:
            reason: Escalation reason
            result: Agent result
            
        Returns:
            Priority level: "low", "medium", "high", "critical"
        """
        # Critical priorities
        if reason in [
            EscalationReason.CONSTITUTIONAL_ISSUE,
            EscalationReason.SYSTEM_ERROR,
        ]:
            return "critical"
        
        # High priorities
        if reason in [
            EscalationReason.LITIGATION_REQUIRED,
            EscalationReason.COMPLIANCE_VIOLATION,
        ]:
            return "high"
        
        # Medium priorities
        if reason in [
            EscalationReason.CROSS_VERIFICATION_DISAGREEMENT,
            EscalationReason.EDGE_CASE_DETECTED,
            EscalationReason.HIGH_RISK_FLAG,
        ]:
            return "medium"
        
        # Default to low for confidence-based escalations
        return "low"
    
    def _generate_context_summary(
        self,
        context: AgentContext,
        result: AgentResult,
    ) -> str:
        """Generate human-readable summary for escalation.
        
        Args:
            context: Execution context
            result: Agent result
            
        Returns:
            Summary string
        """
        parts = []
        
        if context.case_id:
            parts.append(f"Case: {context.case_id}")
        if context.parcel_id:
            parts.append(f"Parcel: {context.parcel_id}")
        if context.jurisdiction:
            parts.append(f"Jurisdiction: {context.jurisdiction}")
        
        parts.append(f"Confidence: {result.confidence:.2f}")
        
        if result.flags:
            parts.append(f"Flags: {', '.join(result.flags)}")
        
        if result.error:
            parts.append(f"Error: {result.error}")
        
        return " | ".join(parts)
    
    async def resolve_escalation(
        self,
        escalation_id: str,
        resolution: str,
        reviewer_id: str,
        outcome: str = "approved",
    ) -> bool:
        """Resolve an escalation request.
        
        Args:
            escalation_id: Escalation to resolve
            resolution: Resolution notes
            reviewer_id: User who reviewed
            outcome: "approved", "rejected", "modified"
            
        Returns:
            Success status
        """
        if not self.db:
            self.logger.warning("No database session for escalation resolution")
            return False
        
        try:
            from app.db.models import EscalationRequest, AIDecision
            from sqlalchemy import select
            
            # Update escalation
            result = await self.db.execute(
                select(EscalationRequest).where(EscalationRequest.id == escalation_id)
            )
            escalation = result.scalar_one_or_none()
            
            if escalation:
                escalation.status = "resolved"
                escalation.resolution = resolution
                escalation.resolved_at = datetime.utcnow()
                
                # Update related AI decision
                decision_result = await self.db.execute(
                    select(AIDecision).where(AIDecision.id == escalation.ai_decision_id)
                )
                decision = decision_result.scalar_one_or_none()
                
                if decision:
                    decision.reviewed_by = reviewer_id
                    decision.reviewed_at = datetime.utcnow()
                    decision.review_outcome = outcome
                
                await self.db.commit()
                
                self.logger.info(
                    f"Resolved escalation {escalation_id}: {outcome} by {reviewer_id}"
                )
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to resolve escalation: {e}")
            return False
