"""Automated Workflow Stage Progression Engine.

This module implements a state machine for parcel stage progression
with jurisdiction-aware guard conditions and AI confidence thresholds.

Features:
- Automatic stage advancement when conditions are met
- Event-driven progression via Pub/Sub
- Jurisdiction-specific rules for transitions
- Escalation to counsel when confidence is below threshold
- Comprehensive audit trail via StatusChange model
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional, Callable
from enum import Enum

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import (
    Parcel,
    ParcelStage,
    PARCEL_STAGE_TRANSITIONS,
    StatusChange,
    Project,
    OfferStatus,
    LitigationStatus,
    Persona,
)
from app.services.rules_engine import (
    get_jurisdiction_config,
    get_notice_requirements,
    is_quick_take_available,
)
from app.services.hashing import sha256_hex

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# Stage Transition Events
# =============================================================================

class TransitionEvent(str, Enum):
    """Events that can trigger stage transitions."""
    INTAKE_COMPLETE = "intake_complete"
    APPRAISAL_COMPLETE = "appraisal_complete"
    OFFER_PREPARED = "offer_prepared"
    OFFER_SENT = "offer_sent"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_REJECTED = "offer_rejected"
    COUNTER_RECEIVED = "counter_received"
    NEGOTIATION_COMPLETE = "negotiation_complete"
    SETTLEMENT_REACHED = "settlement_reached"
    LITIGATION_FILED = "litigation_filed"
    CASE_CLOSED = "case_closed"
    DEADLINE_EXPIRED = "deadline_expired"
    NO_RESPONSE_TIMEOUT = "no_response_timeout"


class TransitionReason(str, Enum):
    """Reasons for automatic transitions."""
    AUTO_PROGRESSION = "auto_progression"
    DEADLINE_TRIGGERED = "deadline_triggered"
    EVENT_TRIGGERED = "event_triggered"
    MANUAL_OVERRIDE = "manual_override"
    ESCALATION_RESOLVED = "escalation_resolved"
    AI_CONFIDENCE_HIGH = "ai_confidence_high"


# =============================================================================
# Guard Condition Results
# =============================================================================

@dataclass
class GuardResult:
    """Result of evaluating a guard condition."""
    allowed: bool
    reason: str
    confidence: float = 1.0
    requires_review: bool = False
    missing_conditions: list[str] = field(default_factory=list)
    
    @classmethod
    def allow(cls, reason: str = "All conditions met", confidence: float = 1.0) -> GuardResult:
        return cls(allowed=True, reason=reason, confidence=confidence)
    
    @classmethod
    def deny(cls, reason: str, missing: list[str] = None) -> GuardResult:
        return cls(allowed=False, reason=reason, missing_conditions=missing or [])
    
    @classmethod
    def escalate(cls, reason: str, confidence: float) -> GuardResult:
        return cls(
            allowed=True, 
            reason=reason, 
            confidence=confidence,
            requires_review=True,
        )


@dataclass
class TransitionResult:
    """Result of a stage transition attempt."""
    success: bool
    from_stage: ParcelStage
    to_stage: Optional[ParcelStage]
    reason: str
    status_change_id: Optional[str] = None
    requires_escalation: bool = False
    escalation_reason: Optional[str] = None


# =============================================================================
# Guard Conditions per Stage Transition
# =============================================================================

def guard_intake_to_appraisal(
    parcel: Parcel,
    project: Project,
    db: Session,
) -> GuardResult:
    """Guard for INTAKE -> APPRAISAL transition.
    
    Requires:
    - Title search initiated or complete
    - Owner identification complete
    - Property data fetched
    """
    missing = []
    
    # Check for parties (owner identification)
    if not parcel.parties:
        missing.append("owner_identification")
    
    # Check metadata for required flags
    metadata = parcel.metadata_json or {}
    
    if not metadata.get("title_search_initiated"):
        missing.append("title_search")
    
    if not metadata.get("property_data_fetched"):
        missing.append("property_data")
    
    if missing:
        return GuardResult.deny(
            f"Intake incomplete: missing {', '.join(missing)}",
            missing=missing,
        )
    
    return GuardResult.allow("Intake requirements satisfied")


def guard_appraisal_to_offer_pending(
    parcel: Parcel,
    project: Project,
    db: Session,
) -> GuardResult:
    """Guard for APPRAISAL -> OFFER_PENDING transition.
    
    Requires:
    - At least one completed appraisal
    - Appraisal value set
    """
    from app.db.models import Appraisal
    
    appraisal = db.query(Appraisal).filter(
        Appraisal.parcel_id == parcel.id,
        Appraisal.completed_at.isnot(None),
    ).first()
    
    if not appraisal:
        return GuardResult.deny(
            "No completed appraisal found",
            missing=["completed_appraisal"],
        )
    
    if not appraisal.value:
        return GuardResult.deny(
            "Appraisal value not set",
            missing=["appraisal_value"],
        )
    
    return GuardResult.allow(f"Appraisal complete: ${appraisal.value:,.2f}")


def guard_offer_pending_to_sent(
    parcel: Parcel,
    project: Project,
    db: Session,
) -> GuardResult:
    """Guard for OFFER_PENDING -> OFFER_SENT transition.
    
    Requires:
    - Offer created and approved
    - Jurisdiction notice requirements met
    - Landowner Bill of Rights sent (if required)
    """
    from app.db.models import Offer
    
    jurisdiction = project.jurisdiction_code
    notice_reqs = get_notice_requirements(jurisdiction)
    
    # Check for draft offer ready to send
    offer = db.query(Offer).filter(
        Offer.parcel_id == parcel.id,
        Offer.status == OfferStatus.DRAFT,
    ).first()
    
    if not offer:
        return GuardResult.deny(
            "No pending offer found",
            missing=["approved_offer"],
        )
    
    missing = []
    
    # Check Bill of Rights if required (TX, MO)
    if notice_reqs.get("landowner_bill_of_rights_required"):
        metadata = parcel.metadata_json or {}
        if not metadata.get("bill_of_rights_sent"):
            missing.append("landowner_bill_of_rights")
    
    if missing:
        return GuardResult.deny(
            f"Pre-offer requirements not met: {', '.join(missing)}",
            missing=missing,
        )
    
    return GuardResult.allow("Offer ready to send")


def guard_offer_sent_to_negotiation(
    parcel: Parcel,
    project: Project,
    db: Session,
) -> GuardResult:
    """Guard for OFFER_SENT -> NEGOTIATION transition.
    
    Requires:
    - Statutory notice period elapsed, OR
    - Response received from landowner
    """
    from app.db.models import Offer
    
    jurisdiction = project.jurisdiction_code
    notice_reqs = get_notice_requirements(jurisdiction)
    response_days = notice_reqs.get("response_window_days", 30)
    
    # Get most recent sent offer
    offer = db.query(Offer).filter(
        Offer.parcel_id == parcel.id,
        Offer.status == OfferStatus.SENT,
    ).order_by(Offer.created_at.desc()).first()
    
    if not offer:
        return GuardResult.deny("No sent offer found")
    
    # Check if response received
    if offer.response_date:
        return GuardResult.allow(f"Response received on {offer.response_date}")
    
    # Check if notice period elapsed
    if offer.sent_date:
        sent_date = datetime.fromisoformat(str(offer.sent_date))
        deadline = sent_date + timedelta(days=response_days)
        
        if datetime.utcnow() >= deadline:
            return GuardResult.allow(
                f"Notice period elapsed ({response_days} days)",
                confidence=0.9,  # Lower confidence for timeout-based transition
            )
    
    days_remaining = (deadline - datetime.utcnow()).days if offer.sent_date else response_days
    return GuardResult.deny(
        f"Waiting for response ({days_remaining} days remaining)",
        missing=["response_or_timeout"],
    )


def guard_negotiation_to_closing(
    parcel: Parcel,
    project: Project,
    db: Session,
) -> GuardResult:
    """Guard for NEGOTIATION -> CLOSING transition.
    
    Requires:
    - Settlement agreement signed, OR
    - Offer accepted
    """
    from app.db.models import Offer
    
    # Check for accepted offer
    accepted_offer = db.query(Offer).filter(
        Offer.parcel_id == parcel.id,
        Offer.status == OfferStatus.ACCEPTED,
    ).first()
    
    if accepted_offer:
        return GuardResult.allow(f"Offer accepted: ${accepted_offer.amount:,.2f}")
    
    # Check metadata for settlement
    metadata = parcel.metadata_json or {}
    if metadata.get("settlement_reached"):
        return GuardResult.allow("Settlement agreement reached")
    
    return GuardResult.deny(
        "No accepted offer or settlement",
        missing=["settlement_or_acceptance"],
    )


def guard_negotiation_to_litigation(
    parcel: Parcel,
    project: Project,
    db: Session,
) -> GuardResult:
    """Guard for NEGOTIATION -> LITIGATION transition.
    
    Requires:
    - Final offer rejected or expired, AND
    - Litigation case created
    """
    from app.db.models import LitigationCase
    
    # Check for litigation case
    lit_case = db.query(LitigationCase).filter(
        LitigationCase.parcel_id == parcel.id,
    ).first()
    
    if not lit_case:
        return GuardResult.deny(
            "No litigation case filed",
            missing=["litigation_case"],
        )
    
    return GuardResult.allow(
        f"Litigation filed: {lit_case.cause_number or lit_case.id}",
        confidence=0.95,  # High confidence but attorney should review
    )


def guard_closing_to_closed(
    parcel: Parcel,
    project: Project,
    db: Session,
) -> GuardResult:
    """Guard for CLOSING -> CLOSED transition.
    
    Requires:
    - Payment cleared
    - Deed recorded
    """
    metadata = parcel.metadata_json or {}
    missing = []
    
    if not metadata.get("payment_cleared"):
        missing.append("payment_cleared")
    
    if not metadata.get("deed_recorded"):
        missing.append("deed_recorded")
    
    if missing:
        return GuardResult.deny(
            f"Closing incomplete: {', '.join(missing)}",
            missing=missing,
        )
    
    return GuardResult.allow("Closing complete")


def guard_litigation_to_closed(
    parcel: Parcel,
    project: Project,
    db: Session,
) -> GuardResult:
    """Guard for LITIGATION -> CLOSED transition.
    
    Requires:
    - Judgment entered or settlement reached
    - Payment cleared
    """
    from app.db.models import LitigationCase
    
    lit_case = db.query(LitigationCase).filter(
        LitigationCase.parcel_id == parcel.id,
    ).first()
    
    if not lit_case:
        return GuardResult.deny("No litigation case found")
    
    # Valid final litigation statuses
    resolved_statuses = [
        LitigationStatus.SETTLED,
        LitigationStatus.CLOSED,
        LitigationStatus.ORDER_OF_POSSESSION,
    ]
    if lit_case.status not in resolved_statuses:
        return GuardResult.deny(
            f"Litigation not resolved (status: {lit_case.status})",
            missing=["litigation_resolution"],
        )
    
    metadata = parcel.metadata_json or {}
    if not metadata.get("payment_cleared"):
        return GuardResult.deny(
            "Payment not cleared",
            missing=["payment_cleared"],
        )
    
    return GuardResult.allow(f"Litigation resolved: {lit_case.status}")


# =============================================================================
# Guard Condition Registry
# =============================================================================

# Map (from_stage, to_stage) -> guard function
GUARD_CONDITIONS: dict[tuple[ParcelStage, ParcelStage], Callable] = {
    (ParcelStage.INTAKE, ParcelStage.APPRAISAL): guard_intake_to_appraisal,
    (ParcelStage.APPRAISAL, ParcelStage.OFFER_PENDING): guard_appraisal_to_offer_pending,
    (ParcelStage.OFFER_PENDING, ParcelStage.OFFER_SENT): guard_offer_pending_to_sent,
    (ParcelStage.OFFER_SENT, ParcelStage.NEGOTIATION): guard_offer_sent_to_negotiation,
    (ParcelStage.NEGOTIATION, ParcelStage.CLOSING): guard_negotiation_to_closing,
    (ParcelStage.NEGOTIATION, ParcelStage.LITIGATION): guard_negotiation_to_litigation,
    (ParcelStage.CLOSING, ParcelStage.CLOSED): guard_closing_to_closed,
    (ParcelStage.LITIGATION, ParcelStage.CLOSED): guard_litigation_to_closed,
}


# =============================================================================
# Workflow Engine Core
# =============================================================================

class WorkflowEngine:
    """Engine for managing parcel stage progressions."""
    
    # Minimum confidence threshold for auto-progression
    confidence_threshold: float = 0.85
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(f"{__name__}.WorkflowEngine")
    
    def get_valid_transitions(self, parcel: Parcel) -> list[ParcelStage]:
        """Get valid next stages for a parcel."""
        current_stage = ParcelStage(parcel.stage) if isinstance(parcel.stage, str) else parcel.stage
        return PARCEL_STAGE_TRANSITIONS.get(current_stage, [])
    
    def evaluate_transition(
        self,
        parcel: Parcel,
        to_stage: ParcelStage,
    ) -> GuardResult:
        """Evaluate if a transition is allowed.
        
        Args:
            parcel: Parcel to evaluate
            to_stage: Target stage
            
        Returns:
            GuardResult with evaluation outcome
        """
        current_stage = ParcelStage(parcel.stage) if isinstance(parcel.stage, str) else parcel.stage
        
        # Check if transition is valid
        valid_transitions = self.get_valid_transitions(parcel)
        if to_stage not in valid_transitions:
            return GuardResult.deny(
                f"Invalid transition: {current_stage.value} -> {to_stage.value}"
            )
        
        # Get project for jurisdiction
        project = self.db.query(Project).filter(Project.id == parcel.project_id).first()
        if not project:
            return GuardResult.deny("Project not found")
        
        # Get guard condition
        guard_fn = GUARD_CONDITIONS.get((current_stage, to_stage))
        if guard_fn is None:
            # No guard defined = allow
            return GuardResult.allow("No guard conditions defined")
        
        # Evaluate guard
        try:
            result = guard_fn(parcel, project, self.db)
            return result
        except Exception as e:
            self.logger.error(f"Guard evaluation failed: {e}")
            return GuardResult.deny(f"Guard evaluation error: {str(e)}")
    
    def execute_transition(
        self,
        parcel: Parcel,
        to_stage: ParcelStage,
        reason: TransitionReason = TransitionReason.AUTO_PROGRESSION,
        actor_persona: Persona = Persona.ADMIN,
        notes: str = None,
        skip_guards: bool = False,
    ) -> TransitionResult:
        """Execute a stage transition.
        
        Args:
            parcel: Parcel to transition
            to_stage: Target stage
            reason: Reason for transition
            actor_persona: Who initiated the transition
            notes: Optional notes
            skip_guards: Skip guard evaluation (for manual override)
            
        Returns:
            TransitionResult with outcome
        """
        from_stage = ParcelStage(parcel.stage) if isinstance(parcel.stage, str) else parcel.stage
        
        # Evaluate guards unless skipped
        if not skip_guards:
            guard_result = self.evaluate_transition(parcel, to_stage)
            
            if not guard_result.allowed:
                return TransitionResult(
                    success=False,
                    from_stage=from_stage,
                    to_stage=None,
                    reason=guard_result.reason,
                )
            
            # Check confidence threshold
            if guard_result.confidence < self.confidence_threshold:
                return TransitionResult(
                    success=False,
                    from_stage=from_stage,
                    to_stage=to_stage,
                    reason=f"Confidence {guard_result.confidence:.2f} below threshold {self.confidence_threshold}",
                    requires_escalation=True,
                    escalation_reason=guard_result.reason,
                )
            
            if guard_result.requires_review:
                return TransitionResult(
                    success=False,
                    from_stage=from_stage,
                    to_stage=to_stage,
                    reason="Guard requires attorney review",
                    requires_escalation=True,
                    escalation_reason=guard_result.reason,
                )
        
        # Execute transition
        try:
            import uuid
            
            # Lock the parcel row to prevent concurrent modifications
            locked_parcel = self.db.query(Parcel).filter(
                Parcel.id == parcel.id
            ).with_for_update().first()
            
            if not locked_parcel:
                return TransitionResult(
                    success=False,
                    from_stage=from_stage,
                    to_stage=to_stage,
                    reason="Parcel not found during transition",
                )
            
            # Verify stage hasn't changed since we started
            current_stage = ParcelStage(locked_parcel.stage) if isinstance(locked_parcel.stage, str) else locked_parcel.stage
            if current_stage != from_stage:
                return TransitionResult(
                    success=False,
                    from_stage=from_stage,
                    to_stage=to_stage,
                    reason=f"Parcel stage changed concurrently to {current_stage.value}",
                )
            
            # Update parcel stage
            locked_parcel.stage = to_stage
            locked_parcel.updated_at = datetime.utcnow()
            
            # Create status change record with tamper-evident hash
            status_change_id = str(uuid.uuid4())
            occurred_at = datetime.utcnow()
            status_change = StatusChange(
                id=status_change_id,
                parcel_id=locked_parcel.id,
                project_id=locked_parcel.project_id,
                old_status=from_stage.value,
                new_status=to_stage.value,
                reason=notes or reason.value,
                actor_persona=actor_persona,
                occurred_at=occurred_at,
                hash=sha256_hex({
                    "id": status_change_id,
                    "parcel_id": locked_parcel.id,
                    "old_status": from_stage.value,
                    "new_status": to_stage.value,
                    "reason": notes or reason.value,
                    "actor_persona": actor_persona.value,
                    "occurred_at": str(occurred_at),
                }),
            )
            self.db.add(status_change)
            self.db.commit()
            
            self.logger.info(
                f"Transitioned parcel {locked_parcel.id}: {from_stage.value} -> {to_stage.value}"
            )
            
            return TransitionResult(
                success=True,
                from_stage=from_stage,
                to_stage=to_stage,
                reason=reason.value,
                status_change_id=status_change.id,
            )
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Transition failed: {e}")
            return TransitionResult(
                success=False,
                from_stage=from_stage,
                to_stage=to_stage,
                reason=f"Transition error: {str(e)}",
            )
    
    def check_auto_progression(self, parcel: Parcel) -> Optional[TransitionResult]:
        """Check if parcel can auto-progress to next stage.
        
        Evaluates all valid transitions and executes the first one that passes.
        
        Args:
            parcel: Parcel to check
            
        Returns:
            TransitionResult if progression occurred, None otherwise
        """
        valid_transitions = self.get_valid_transitions(parcel)
        
        for target_stage in valid_transitions:
            guard_result = self.evaluate_transition(parcel, target_stage)
            
            if guard_result.allowed and guard_result.confidence >= self.confidence_threshold:
                if not guard_result.requires_review:
                    result = self.execute_transition(
                        parcel,
                        target_stage,
                        reason=TransitionReason.AUTO_PROGRESSION,
                    )
                    if result.success:
                        return result
        
        return None
    
    def get_pending_progressions(self, project_id: str = None) -> list[dict[str, Any]]:
        """Get parcels that are close to auto-progression.
        
        Returns parcels where guards pass but confidence < threshold,
        indicating they need attorney review before progression.
        """
        query = self.db.query(Parcel)
        if project_id:
            query = query.filter(Parcel.project_id == project_id)
        
        query = query.filter(Parcel.stage != ParcelStage.CLOSED)
        
        pending = []
        for parcel in query.all():
            valid_transitions = self.get_valid_transitions(parcel)
            
            for target_stage in valid_transitions:
                guard_result = self.evaluate_transition(parcel, target_stage)
                
                if guard_result.allowed and (
                    guard_result.requires_review or 
                    guard_result.confidence < self.confidence_threshold
                ):
                    pending.append({
                        "parcel_id": parcel.id,
                        "project_id": parcel.project_id,
                        "current_stage": parcel.stage,
                        "target_stage": target_stage.value,
                        "confidence": guard_result.confidence,
                        "reason": guard_result.reason,
                        "requires_review": guard_result.requires_review,
                    })
        
        return pending


def check_all_parcels_for_progression(db: Session) -> dict[str, Any]:
    """Check all active parcels for auto-progression.
    
    Called by scheduled Celery task.
    
    Returns:
        Stats dict with counts
    """
    engine = WorkflowEngine(db)
    
    # Get all non-closed parcels
    parcels = db.query(Parcel).filter(Parcel.stage != ParcelStage.CLOSED).all()
    
    stats = {
        "total_checked": len(parcels),
        "auto_progressed": 0,
        "pending_review": 0,
        "unchanged": 0,
        "transitions": [],
    }
    
    for parcel in parcels:
        result = engine.check_auto_progression(parcel)
        
        if result:
            if result.success:
                stats["auto_progressed"] += 1
                stats["transitions"].append({
                    "parcel_id": parcel.id,
                    "from": result.from_stage.value,
                    "to": result.to_stage.value if result.to_stage else None,
                })
            elif result.requires_escalation:
                stats["pending_review"] += 1
        else:
            stats["unchanged"] += 1
    
    logger.info(f"Workflow check complete: {stats}")
    return stats
