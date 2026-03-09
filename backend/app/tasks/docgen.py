"""Celery tasks for document generation and template processing.

These tasks support the DocGenAgent for:
- Generating legal documents from templates
- AI-enhanced document drafting
- PDF/DOCX rendering
- Creating review tasks for counsel
"""

from celery import shared_task
from typing import Any
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def generate_document(
    self, 
    template_id: str, 
    variables: dict[str, Any],
    jurisdiction: str,
    parcel_id: str | None = None,
    project_id: str | None = None
) -> dict[str, Any]:
    """Generate a legal document from a template.
    
    Args:
        template_id: Template identifier
        variables: Template variables
        jurisdiction: State code
        parcel_id: Optional parcel association
        project_id: Optional project association
        
    Returns:
        Generated document with review task ID
    """
    try:
        from app.agents.docgen_agent import DocGenAgent
        from app.agents.orchestrator import AgentOrchestrator, AgentContext
        
        agent = DocGenAgent()
        orchestrator = AgentOrchestrator()
        
        context = AgentContext(
            template_id=template_id,
            variables=variables,
            jurisdiction=jurisdiction,
            parcel_id=parcel_id,
            project_id=project_id,
        )
        
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                orchestrator.execute_with_oversight(agent, context)
            )
            return {
                "status": result.status,
                "document_id": result.result.data.get("document_id") if result.result else None,
                "review_task_id": result.result.data.get("review_task_id") if result.result else None,
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Document generation failed for template {template_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2)
def enhance_document_with_ai(
    self,
    document_id: str,
    jurisdiction: str
) -> dict[str, Any]:
    """Enhance a document draft with AI suggestions.
    
    Args:
        document_id: Document to enhance
        jurisdiction: State code for citations
        
    Returns:
        Enhanced document with suggestions
    """
    try:
        from app.agents.docgen_agent import DocGenAgent
        
        agent = DocGenAgent()
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                agent.enhance_with_ai(document_id, jurisdiction)
            )
            return result
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"AI enhancement failed for document {document_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True)
def render_document_pdf(self, document_id: str) -> dict[str, Any]:
    """Render a document to PDF format.
    
    Args:
        document_id: Document to render
        
    Returns:
        PDF storage path and metadata
    """
    try:
        from app.agents.docgen_agent import DocGenAgent
        
        agent = DocGenAgent()
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                agent.render_to_pdf(document_id)
            )
            return {
                "document_id": document_id,
                "pdf_path": result.get("storage_path"),
                "page_count": result.get("page_count"),
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"PDF rendering failed for document {document_id}: {exc}")
        raise


@shared_task(bind=True)
def render_document_docx(self, document_id: str) -> dict[str, Any]:
    """Render a document to DOCX format.
    
    Args:
        document_id: Document to render
        
    Returns:
        DOCX storage path and metadata
    """
    try:
        from app.agents.docgen_agent import DocGenAgent
        
        agent = DocGenAgent()
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                agent.render_to_docx(document_id)
            )
            return {
                "document_id": document_id,
                "docx_path": result.get("storage_path"),
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"DOCX rendering failed for document {document_id}: {exc}")
        raise


@shared_task(bind=True)
def generate_court_petition(
    self,
    project_id: str,
    parcel_id: str,
    petition_type: str = "condemnation"
) -> dict[str, Any]:
    """Generate a court petition document.
    
    Args:
        project_id: Project ID
        parcel_id: Parcel ID
        petition_type: Type of petition (condemnation, motion, etc.)
        
    Returns:
        Generated petition with review task
    """
    try:
        from app.agents.docgen_agent import DocGenAgent
        
        agent = DocGenAgent()
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                agent.generate_court_petition(project_id, parcel_id, petition_type)
            )
            return result
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Petition generation failed for project {project_id}: {exc}")
        raise
