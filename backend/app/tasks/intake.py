"""Celery tasks for case intake and property data fetching.

These tasks support the IntakeAgent for:
- Fetching property data from external APIs
- Evaluating case eligibility
- Computing risk scores
- Caching external data
"""

from celery import shared_task
from typing import Any
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_property_data(self, apn: str, county_fips: str) -> dict[str, Any]:
    """Fetch property data from external APIs (CoreLogic, ATTOM, etc.).
    
    Args:
        apn: Assessor's Parcel Number
        county_fips: County FIPS code
        
    Returns:
        Property data dictionary with owner info, liens, tax records
    """
    try:
        from app.agents.intake_agent import IntakeAgent
        
        agent = IntakeAgent()
        # Note: This wraps the async method for Celery
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                agent.fetch_property_data(apn, county_fips)
            )
            return result
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Property data fetch failed for {apn}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3)
def evaluate_case_eligibility(
    self, 
    case_id: str, 
    jurisdiction: str, 
    property_data: dict[str, Any]
) -> dict[str, Any]:
    """Evaluate legal eligibility for an eminent domain case.
    
    Args:
        case_id: Case/project ID
        jurisdiction: State code (TX, CA, etc.)
        property_data: Property data from fetch_property_data
        
    Returns:
        Eligibility evaluation with confidence score and flags
    """
    try:
        from app.agents.intake_agent import IntakeAgent
        
        agent = IntakeAgent()
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                agent.evaluate_eligibility(jurisdiction, property_data)
            )
            return result.__dict__ if hasattr(result, '__dict__') else result
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Eligibility evaluation failed for case {case_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True)
def run_intake_pipeline(self, case_id: str, apn: str, county_fips: str, jurisdiction: str) -> dict[str, Any]:
    """Run the complete intake pipeline for a new case.
    
    This is the main entry point that orchestrates:
    1. Property data fetch
    2. Eligibility evaluation
    3. Risk score calculation
    4. AI summary generation
    
    Args:
        case_id: New case ID
        apn: Property APN
        county_fips: County FIPS code
        jurisdiction: State code
        
    Returns:
        Complete intake result with property data, eligibility, and risk
    """
    try:
        from app.agents.intake_agent import IntakeAgent
        from app.agents.orchestrator import AgentOrchestrator, AgentContext
        
        context = AgentContext(
            case_id=case_id,
            apn=apn,
            county_fips=county_fips,
            jurisdiction=jurisdiction,
        )
        
        agent = IntakeAgent()
        orchestrator = AgentOrchestrator()
        
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                orchestrator.execute_with_oversight(agent, context)
            )
            return {
                "status": result.status,
                "result": result.result.data if result.result else None,
                "escalation_id": result.escalation.id if result.escalation else None,
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Intake pipeline failed for case {case_id}: {exc}")
        raise


@shared_task
def cleanup_stale_cache() -> dict[str, int]:
    """Remove stale entries from the external data cache.
    
    Scheduled task that runs daily to clean up old cached
    property data and API responses.
    
    Returns:
        Count of cleaned entries by type
    """
    logger.info("Running external data cache cleanup")
    
    # TODO: Implement cache cleanup logic
    # This will clean ExternalDataCache entries older than TTL
    
    return {"property_data": 0, "avm_data": 0, "title_data": 0}
