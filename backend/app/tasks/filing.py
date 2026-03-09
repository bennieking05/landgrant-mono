"""Celery tasks for deadline monitoring and e-filing.

These tasks support the FilingAgent for:
- Monitoring approaching deadlines
- Sending reminder notifications
- E-filing court documents
- Recording deeds
- Interpreting filing errors
"""

from celery import shared_task
from typing import Any
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@shared_task
def check_all_deadlines() -> dict[str, Any]:
    """Check all upcoming deadlines across projects.
    
    Scheduled task that runs hourly to:
    - Identify approaching deadlines
    - Send reminders at 7, 3, 1 day marks
    - Escalate missed deadlines immediately
    - Execute auto-actions if configured
    
    Returns:
        Summary of deadline actions taken
    """
    logger.info("Checking all project deadlines")
    
    try:
        from app.agents.filing_agent import FilingAgent
        
        agent = FilingAgent()
        
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(agent.check_deadlines())
            
            reminders_sent = sum(1 for r in results if r.get("action") == "reminder")
            escalations = sum(1 for r in results if r.get("action") == "escalate")
            auto_actions = sum(1 for r in results if r.get("action") == "auto_action")
            
            return {
                "deadlines_checked": len(results),
                "reminders_sent": reminders_sent,
                "escalations_created": escalations,
                "auto_actions_executed": auto_actions,
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Deadline check failed: {exc}")
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def file_document_with_court(
    self,
    document_id: str,
    court_id: str,
    case_number: str | None = None
) -> dict[str, Any]:
    """File a document with the court e-filing system.
    
    Args:
        document_id: Document to file
        court_id: Target court identifier
        case_number: Existing case number (if applicable)
        
    Returns:
        Filing result with confirmation or error details
    """
    try:
        from app.agents.filing_agent import FilingAgent
        from app.agents.orchestrator import AgentOrchestrator, AgentContext
        
        agent = FilingAgent()
        orchestrator = AgentOrchestrator()
        
        context = AgentContext(
            document_id=document_id,
            court_id=court_id,
            case_number=case_number,
            action="file_document",
        )
        
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                orchestrator.execute_with_oversight(agent, context)
            )
            return {
                "status": result.status,
                "filing_result": result.result.data if result.result else None,
                "requires_review": result.status == "pending_review",
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"E-filing failed for document {document_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def record_deed(
    self,
    document_id: str,
    county_fips: str
) -> dict[str, Any]:
    """Record a deed with the county clerk.
    
    Args:
        document_id: Deed document to record
        county_fips: County FIPS code
        
    Returns:
        Recording result with instrument number
    """
    try:
        from app.agents.filing_agent import FilingAgent
        
        agent = FilingAgent()
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                agent.record_deed(document_id, county_fips)
            )
            return result
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Deed recording failed for document {document_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True)
def send_deadline_reminder(
    self,
    deadline_id: str,
    days_remaining: int,
    recipient_ids: list[str]
) -> dict[str, Any]:
    """Send deadline reminder notification.
    
    Args:
        deadline_id: Deadline to remind about
        days_remaining: Days until deadline
        recipient_ids: Users to notify
        
    Returns:
        Notification result
    """
    try:
        from app.agents.filing_agent import FilingAgent
        
        agent = FilingAgent()
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                agent.send_reminder(deadline_id, days_remaining, recipient_ids)
            )
            return {
                "deadline_id": deadline_id,
                "notifications_sent": len(recipient_ids),
                "channels": result.get("channels", []),
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Reminder failed for deadline {deadline_id}: {exc}")
        raise


@shared_task(bind=True)
def interpret_filing_error(
    self,
    error_response: dict[str, Any],
    document_type: str,
    court_name: str
) -> dict[str, Any]:
    """Use AI to interpret a court e-filing error.
    
    Args:
        error_response: Error from e-filing system
        document_type: Type of document filed
        court_name: Name of court
        
    Returns:
        Interpreted error with suggested actions
    """
    try:
        from app.agents.filing_agent import FilingAgent
        
        agent = FilingAgent()
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                agent.interpret_filing_error(error_response, document_type, court_name)
            )
            return result
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Error interpretation failed: {exc}")
        raise


@shared_task(bind=True)
def escalate_missed_deadline(self, deadline_id: str) -> dict[str, Any]:
    """Create escalation for a missed deadline.
    
    Args:
        deadline_id: Missed deadline
        
    Returns:
        Escalation result
    """
    try:
        from app.agents.filing_agent import FilingAgent
        
        agent = FilingAgent()
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                agent.escalate_missed_deadline(deadline_id)
            )
            return result
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Escalation failed for deadline {deadline_id}: {exc}")
        raise
