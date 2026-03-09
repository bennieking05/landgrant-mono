"""Celery tasks for title search and OCR processing.

These tasks support the TitleAgent for:
- OCR processing of title documents
- Entity extraction from title records
- Chain of title analysis
- Public data integration (GIS, tax, zoning)
"""

from celery import shared_task
from typing import Any
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_title_document_ocr(self, document_id: str) -> dict[str, Any]:
    """Process a title document with OCR.
    
    Args:
        document_id: Document to process
        
    Returns:
        OCR result with extracted text
    """
    try:
        from app.agents.title_agent import TitleAgent
        
        agent = TitleAgent()
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                agent.ocr_document(document_id)
            )
            return result
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"OCR processing failed for document {document_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2)
def analyze_title_document(self, document_id: str) -> dict[str, Any]:
    """Analyze a title document for entities and issues.
    
    Args:
        document_id: Document to analyze
        
    Returns:
        Analysis with extracted entities and flagged issues
    """
    try:
        from app.agents.title_agent import TitleAgent
        from app.agents.orchestrator import AgentOrchestrator, AgentContext
        
        agent = TitleAgent()
        orchestrator = AgentOrchestrator()
        
        context = AgentContext(
            document_id=document_id,
            action="analyze_document",
        )
        
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                orchestrator.execute_with_oversight(agent, context)
            )
            return {
                "status": result.status,
                "data": result.result.data if result.result else None,
                "requires_review": result.status == "pending_review",
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Title analysis failed for document {document_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True)
def build_chain_of_title(self, parcel_id: str) -> dict[str, Any]:
    """Build chain of title from all parcel instruments.
    
    Args:
        parcel_id: Parcel to analyze
        
    Returns:
        Chain of title with gaps and issues identified
    """
    try:
        from app.agents.title_agent import TitleAgent
        from app.agents.orchestrator import AgentOrchestrator, AgentContext
        
        agent = TitleAgent()
        orchestrator = AgentOrchestrator()
        
        context = AgentContext(
            parcel_id=parcel_id,
            action="build_chain",
        )
        
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                orchestrator.execute_with_oversight(agent, context)
            )
            return {
                "status": result.status,
                "chain": result.result.data.get("chain_of_title") if result.result else None,
                "issues": result.result.data.get("issues") if result.result else [],
                "requires_review": result.status == "pending_review",
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Chain of title build failed for parcel {parcel_id}: {exc}")
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_public_records(self, parcel_id: str, county_fips: str) -> dict[str, Any]:
    """Fetch public records for a parcel (tax, GIS, zoning).
    
    Args:
        parcel_id: Parcel ID
        county_fips: County FIPS code
        
    Returns:
        Public records data
    """
    try:
        from app.agents.title_agent import TitleAgent
        
        agent = TitleAgent()
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            # Fetch multiple data sources in parallel
            result = loop.run_until_complete(
                agent.fetch_all_public_data(parcel_id, county_fips)
            )
            return result
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Public records fetch failed for parcel {parcel_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True)
def extract_title_entities(self, ocr_text: str, document_type: str) -> dict[str, Any]:
    """Extract entities from OCR text using NLP.
    
    Args:
        ocr_text: Text from OCR processing
        document_type: Type of title document
        
    Returns:
        Extracted entities (parties, dates, amounts, etc.)
    """
    try:
        from app.agents.title_agent import TitleAgent
        
        agent = TitleAgent()
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                agent.extract_entities(ocr_text, document_type)
            )
            return result
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Entity extraction failed: {exc}")
        raise


@shared_task(bind=True)
def identify_title_issues(self, parcel_id: str, chain_data: dict[str, Any]) -> dict[str, Any]:
    """Use AI to identify potential title issues.
    
    Args:
        parcel_id: Parcel ID
        chain_data: Chain of title data
        
    Returns:
        Identified issues with severity and recommendations
    """
    try:
        from app.agents.title_agent import TitleAgent
        
        agent = TitleAgent()
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                agent.identify_issues_with_ai(parcel_id, chain_data)
            )
            return result
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Title issue identification failed for parcel {parcel_id}: {exc}")
        raise
