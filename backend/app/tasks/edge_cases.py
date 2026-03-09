"""Celery tasks for edge case handling.

These tasks support the EdgeCaseAgent for:
- Business relocation calculations
- Partial taking analysis
- Inverse condemnation detection
- Heritage property handling
- Workflow adaptations for special scenarios
"""

from celery import shared_task
from typing import Any
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def detect_edge_cases(self, parcel_id: str) -> dict[str, Any]:
    """Detect edge cases for a parcel.
    
    Args:
        parcel_id: Parcel to analyze
        
    Returns:
        Detected edge cases with confidence scores
    """
    try:
        from app.agents.edge_case_agent import EdgeCaseAgent
        
        agent = EdgeCaseAgent()
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            detected = loop.run_until_complete(
                agent.detect_edge_cases(parcel_id)
            )
            return {
                "parcel_id": parcel_id,
                "edge_cases": detected,
                "count": len(detected),
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Edge case detection failed for parcel {parcel_id}: {exc}")
        raise


@shared_task(bind=True)
def handle_business_relocation(self, parcel_id: str) -> dict[str, Any]:
    """Handle business relocation edge case.
    
    Args:
        parcel_id: Parcel with business
        
    Returns:
        Relocation costs and plan
    """
    try:
        from app.agents.edge_case_agent import EdgeCaseAgent, BusinessRelocationHandler
        from app.agents.orchestrator import AgentOrchestrator, AgentContext
        
        handler = BusinessRelocationHandler()
        orchestrator = AgentOrchestrator()
        
        context = AgentContext(
            parcel_id=parcel_id,
            edge_case_type="business_relocation",
        )
        
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                orchestrator.execute_with_oversight(handler, context)
            )
            return {
                "status": result.status,
                "data": result.result.data if result.result else None,
                "requires_review": result.status == "pending_review",
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Business relocation handling failed for parcel {parcel_id}: {exc}")
        raise


@shared_task(bind=True)
def handle_partial_taking(self, parcel_id: str) -> dict[str, Any]:
    """Handle partial taking edge case.
    
    Args:
        parcel_id: Parcel with partial taking
        
    Returns:
        Severance damages and remnant analysis
    """
    try:
        from app.agents.edge_case_agent import PartialTakingHandler
        from app.agents.orchestrator import AgentOrchestrator, AgentContext
        
        handler = PartialTakingHandler()
        orchestrator = AgentOrchestrator()
        
        context = AgentContext(
            parcel_id=parcel_id,
            edge_case_type="partial_taking",
        )
        
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                orchestrator.execute_with_oversight(handler, context)
            )
            return {
                "status": result.status,
                "data": result.result.data if result.result else None,
                "recommendation": result.result.data.get("recommendation") if result.result else None,
                "requires_review": result.status == "pending_review",
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Partial taking handling failed for parcel {parcel_id}: {exc}")
        raise


@shared_task(bind=True)
def handle_inverse_condemnation(self, parcel_id: str) -> dict[str, Any]:
    """Handle inverse condemnation claim detection.
    
    Args:
        parcel_id: Parcel to analyze
        
    Returns:
        Inverse condemnation analysis
    """
    try:
        from app.agents.edge_case_agent import InverseCondemnationHandler
        from app.agents.orchestrator import AgentOrchestrator, AgentContext
        
        handler = InverseCondemnationHandler()
        orchestrator = AgentOrchestrator()
        
        context = AgentContext(
            parcel_id=parcel_id,
            edge_case_type="inverse_condemnation",
        )
        
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                orchestrator.execute_with_oversight(handler, context)
            )
            return {
                "status": result.status,
                "data": result.result.data if result.result else None,
                "requires_review": True,  # Always review inverse claims
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Inverse condemnation handling failed for parcel {parcel_id}: {exc}")
        raise


@shared_task(bind=True)
def calculate_severance_damages(
    self,
    parcel_id: str,
    before_value: float,
    taking_area: float,
    after_conditions: dict[str, Any]
) -> dict[str, Any]:
    """Calculate severance damages for partial taking.
    
    Args:
        parcel_id: Parcel ID
        before_value: Value before taking
        taking_area: Area being taken
        after_conditions: Conditions affecting remainder
        
    Returns:
        Severance damage calculation
    """
    try:
        from app.agents.edge_case_agent import PartialTakingHandler
        
        handler = PartialTakingHandler()
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                handler.calculate_severance_damages(
                    parcel_id, before_value, taking_area, after_conditions
                )
            )
            return result
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Severance calculation failed for parcel {parcel_id}: {exc}")
        raise


@shared_task(bind=True)
def calculate_business_goodwill(
    self,
    parcel_id: str,
    jurisdiction: str,
    business_info: dict[str, Any]
) -> dict[str, Any]:
    """Calculate business goodwill compensation (CA, NV).
    
    Args:
        parcel_id: Parcel ID
        jurisdiction: State code (must support goodwill)
        business_info: Business financial data
        
    Returns:
        Goodwill calculation if applicable
    """
    try:
        from app.agents.edge_case_agent import BusinessRelocationHandler
        
        handler = BusinessRelocationHandler()
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                handler.calculate_goodwill(parcel_id, jurisdiction, business_info)
            )
            return result
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Goodwill calculation failed for parcel {parcel_id}: {exc}")
        raise


@shared_task(bind=True)
def adapt_workflow_for_edge_case(
    self,
    parcel_id: str,
    edge_case_type: str
) -> dict[str, Any]:
    """Adapt workflow based on detected edge case.
    
    Args:
        parcel_id: Parcel ID
        edge_case_type: Type of edge case detected
        
    Returns:
        Workflow adaptations applied
    """
    try:
        from app.agents.edge_case_agent import EdgeCaseAgent
        
        agent = EdgeCaseAgent()
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                agent.adapt_workflow(parcel_id, edge_case_type)
            )
            return {
                "parcel_id": parcel_id,
                "edge_case_type": edge_case_type,
                "adaptations": result.get("adaptations", []),
                "additional_documents": result.get("additional_documents", []),
                "workflow_steps_added": result.get("workflow_steps_added", []),
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Workflow adaptation failed for parcel {parcel_id}: {exc}")
        raise
