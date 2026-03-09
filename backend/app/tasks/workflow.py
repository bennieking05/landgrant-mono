"""Celery tasks for automated workflow progression.

These tasks implement scheduled and event-driven stage transitions:
- Scheduled check every 15 minutes for auto-progression
- Event-triggered transitions via Pub/Sub
- Escalation creation for low-confidence transitions
"""

from celery import shared_task
from typing import Any
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def check_stage_transitions(self) -> dict[str, Any]:
    """Check all active parcels for potential stage progression.
    
    This task runs on a schedule (every 15 minutes) to automatically
    advance parcels that meet all guard conditions with high confidence.
    
    Returns:
        Stats dict with progression counts
    """
    from app.db.session import SessionLocal
    from app.services.workflow_engine import check_all_parcels_for_progression
    
    db = SessionLocal()
    try:
        stats = check_all_parcels_for_progression(db)
        
        # Log significant events
        if stats["auto_progressed"] > 0:
            logger.info(
                f"Auto-progressed {stats['auto_progressed']} parcels: "
                f"{stats['transitions']}"
            )
        
        if stats["pending_review"] > 0:
            logger.info(
                f"{stats['pending_review']} parcels pending attorney review"
            )
        
        return stats
        
    except Exception as e:
        logger.error(f"Stage transition check failed: {e}")
        raise
    finally:
        db.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_workflow_event(
    self,
    event_type: str,
    parcel_id: str,
    event_data: dict[str, Any] = None,
) -> dict[str, Any]:
    """Process a workflow event that may trigger a stage transition.
    
    Events include:
    - offer_accepted / offer_rejected
    - appraisal_complete
    - payment_cleared
    - litigation_filed
    - deadline_expired
    
    Args:
        event_type: Type of workflow event
        parcel_id: Parcel affected by the event
        event_data: Additional event data
        
    Returns:
        Result dict with transition outcome
    """
    from app.db.session import SessionLocal
    from app.db.models import Parcel, ParcelStage
    from app.services.workflow_engine import (
        WorkflowEngine,
        TransitionEvent,
        TransitionReason,
    )
    
    db = SessionLocal()
    try:
        parcel = db.query(Parcel).filter(Parcel.id == parcel_id).first()
        if not parcel:
            return {"success": False, "error": f"Parcel not found: {parcel_id}"}
        
        engine = WorkflowEngine(db)
        
        # Map event to potential target stage
        event_stage_map = {
            "intake_complete": ParcelStage.APPRAISAL,
            "appraisal_complete": ParcelStage.OFFER_PENDING,
            "offer_prepared": ParcelStage.OFFER_SENT,
            "offer_sent": ParcelStage.NEGOTIATION,
            "offer_accepted": ParcelStage.CLOSING,
            "settlement_reached": ParcelStage.CLOSING,
            "litigation_filed": ParcelStage.LITIGATION,
            "case_closed": ParcelStage.CLOSED,
            "payment_cleared": ParcelStage.CLOSED,
        }
        
        target_stage = event_stage_map.get(event_type)
        if not target_stage:
            logger.warning(f"Unknown event type: {event_type}")
            return {"success": False, "error": f"Unknown event: {event_type}"}
        
        # Update parcel metadata with event info
        if event_data:
            metadata = parcel.metadata_json or {}
            metadata[f"event_{event_type}"] = event_data
            metadata[f"event_{event_type}_at"] = str(event_data.get("timestamp", ""))
            parcel.metadata_json = metadata
            db.commit()
        
        # Attempt transition
        result = engine.execute_transition(
            parcel,
            target_stage,
            reason=TransitionReason.EVENT_TRIGGERED,
            notes=f"Triggered by event: {event_type}",
        )
        
        response = {
            "success": result.success,
            "parcel_id": parcel_id,
            "event_type": event_type,
            "from_stage": result.from_stage.value,
            "to_stage": result.to_stage.value if result.to_stage else None,
            "reason": result.reason,
        }
        
        if result.requires_escalation:
            # Create escalation
            escalation_id = create_workflow_escalation(
                db,
                parcel_id,
                result.escalation_reason or result.reason,
                target_stage.value,
            )
            response["escalation_id"] = escalation_id
        
        return response
        
    except Exception as e:
        logger.error(f"Workflow event processing failed: {e}")
        raise self.retry(exc=e)
    finally:
        db.close()


@shared_task(bind=True)
def check_deadline_expirations(self) -> dict[str, Any]:
    """Check for expired deadlines that should trigger transitions.
    
    Looks for:
    - Offer response deadlines that have passed
    - Notice periods that have elapsed
    - Filing deadlines
    
    Returns:
        Stats dict with expiration counts
    """
    from datetime import datetime
    from app.db.session import SessionLocal
    from app.db.models import Parcel, ParcelStage, Deadline
    from app.services.workflow_engine import (
        WorkflowEngine,
        TransitionReason,
    )
    
    db = SessionLocal()
    try:
        stats = {
            "deadlines_checked": 0,
            "expirations_found": 0,
            "transitions_triggered": 0,
        }
        
        # Find expired deadlines
        now = datetime.utcnow()
        expired_deadlines = db.query(Deadline).filter(
            Deadline.due_at <= now,
            Deadline.parcel_id.isnot(None),
        ).all()
        
        stats["deadlines_checked"] = len(expired_deadlines)
        engine = WorkflowEngine(db)
        
        for deadline in expired_deadlines:
            parcel = db.query(Parcel).filter(
                Parcel.id == deadline.parcel_id
            ).first()
            
            if not parcel or parcel.stage == ParcelStage.CLOSED:
                continue
            
            stats["expirations_found"] += 1
            
            # Check if this deadline enables a transition
            result = engine.check_auto_progression(parcel)
            if result and result.success:
                stats["transitions_triggered"] += 1
        
        return stats
        
    except Exception as e:
        logger.error(f"Deadline expiration check failed: {e}")
        raise
    finally:
        db.close()


@shared_task
def notify_pending_progressions() -> dict[str, Any]:
    """Notify attorneys of parcels pending review for progression.
    
    Generates a summary of parcels that could progress but need
    human review due to low confidence or explicit review flags.
    
    Returns:
        Notification stats
    """
    from app.db.session import SessionLocal
    from app.services.workflow_engine import WorkflowEngine
    
    db = SessionLocal()
    try:
        engine = WorkflowEngine(db)
        pending = engine.get_pending_progressions()
        
        if not pending:
            return {"pending_count": 0, "notifications_sent": 0}
        
        # Group by project
        by_project: dict[str, list] = {}
        for item in pending:
            project_id = item["project_id"]
            if project_id not in by_project:
                by_project[project_id] = []
            by_project[project_id].append(item)
        
        # TODO: Send actual notifications via NotificationsService
        # For now, just log and return stats
        
        logger.info(
            f"Found {len(pending)} parcels pending review across "
            f"{len(by_project)} projects"
        )
        
        return {
            "pending_count": len(pending),
            "projects_affected": len(by_project),
            "notifications_sent": 0,  # TODO: Implement
            "pending_items": pending[:10],  # First 10 for visibility
        }
        
    finally:
        db.close()


def create_workflow_escalation(
    db,
    parcel_id: str,
    reason: str,
    target_stage: str,
) -> str:
    """Create an escalation for workflow progression review.
    
    Returns:
        Escalation ID
    """
    import uuid
    from app.db.models import WorkflowEscalation, EscalationPriority
    
    escalation = WorkflowEscalation(
        id=str(uuid.uuid4()),
        parcel_id=parcel_id,
        reason=f"Workflow progression to {target_stage}: {reason}",
        priority=EscalationPriority.MEDIUM,
        status="pending",
        target_stage=target_stage,
        context_summary=f"Auto-progression blocked for parcel {parcel_id}",
    )
    db.add(escalation)
    db.commit()
    
    logger.info(f"Created workflow escalation {escalation.id} for parcel {parcel_id}")
    return escalation.id
