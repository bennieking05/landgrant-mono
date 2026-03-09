"""RAG Knowledge Base API endpoints.

Provides REST API for:
- Searching the legal knowledge base
- Ingesting documents
- Checking knowledge base health
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Any
import logging

from app.services.rag_service import (
    search,
    search_for_context,
    format_context_for_prompt,
    health_check,
    get_collection_stats,
    SearchRequest,
    DocumentType,
    RetrievalResult,
)
from app.tasks.ingest import (
    ingest_rule_pack_task,
    ingest_all_rule_packs,
    ingest_document_task,
    refresh_knowledge_base,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG Knowledge Base"])


# =============================================================================
# Request/Response Models
# =============================================================================

class SearchRequestModel(BaseModel):
    """Request model for knowledge base search."""
    query: str = Field(..., description="Search query (natural language)")
    jurisdiction: Optional[str] = Field(None, description="Filter by jurisdiction (e.g., TX, CA)")
    doc_types: Optional[list[str]] = Field(None, description="Filter by document types")
    top_k: int = Field(5, ge=1, le=20, description="Number of results to return")
    min_score: float = Field(0.7, ge=0.0, le=1.0, description="Minimum relevance score")


class SearchResultModel(BaseModel):
    """Response model for a single search result."""
    chunk_id: str
    content: str
    relevance_score: float
    doc_type: str
    jurisdiction: Optional[str]
    citation: Optional[str]
    metadata: dict[str, Any]


class SearchResponseModel(BaseModel):
    """Response model for search endpoint."""
    query: str
    result_count: int
    results: list[SearchResultModel]
    formatted_context: str


class IngestDocumentRequest(BaseModel):
    """Request model for document ingestion."""
    document_id: str = Field(..., description="Unique document identifier")
    content: str = Field(..., description="Document text content")
    doc_type: str = Field(..., description="Document type (statute, case_law, template, etc.)")
    jurisdiction: Optional[str] = Field(None, description="Jurisdiction code")
    citation: Optional[str] = Field(None, description="Legal citation")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")


class IngestResponse(BaseModel):
    """Response model for ingestion endpoints."""
    status: str
    message: str
    task_id: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Response model for health check."""
    rag_enabled: bool
    chroma_status: str
    embedding_status: str
    document_count: Optional[int] = None
    embedding_model: Optional[str] = None


# =============================================================================
# Search Endpoints
# =============================================================================

@router.post("/search", response_model=SearchResponseModel)
async def search_knowledge_base(request: SearchRequestModel):
    """Search the legal knowledge base.
    
    Returns relevant statutes, case law, and rule pack information
    based on the search query. Results can be filtered by jurisdiction
    and document type.
    """
    try:
        # Convert doc_types to enum
        doc_type_enums = None
        if request.doc_types:
            try:
                doc_type_enums = [DocumentType(dt) for dt in request.doc_types]
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid document type. Valid types: {[dt.value for dt in DocumentType]}"
                )
        
        search_req = SearchRequest(
            query=request.query,
            jurisdiction=request.jurisdiction,
            doc_types=doc_type_enums,
            top_k=request.top_k,
            min_score=request.min_score,
        )
        
        results = await search(search_req)
        
        # Format for prompt
        formatted = format_context_for_prompt(results)
        
        return SearchResponseModel(
            query=request.query,
            result_count=len(results),
            results=[
                SearchResultModel(
                    chunk_id=r.chunk_id,
                    content=r.content,
                    relevance_score=r.relevance_score,
                    doc_type=r.doc_type.value,
                    jurisdiction=r.jurisdiction,
                    citation=r.citation,
                    metadata=r.metadata,
                )
                for r in results
            ],
            formatted_context=formatted,
        )
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/context")
async def get_context_for_query(
    query: str,
    jurisdiction: Optional[str] = None,
    top_k: int = 5,
):
    """Simplified search endpoint for AI agents.
    
    Returns formatted context string suitable for inclusion in LLM prompts.
    """
    try:
        results = await search_for_context(query, jurisdiction, top_k)
        formatted = format_context_for_prompt(results)
        
        return {
            "query": query,
            "jurisdiction": jurisdiction,
            "result_count": len(results),
            "context": formatted,
            "citations": [r.citation for r in results if r.citation],
        }
        
    except Exception as e:
        logger.error(f"Context retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Ingestion Endpoints
# =============================================================================

@router.post("/ingest/document", response_model=IngestResponse)
async def ingest_document(
    request: IngestDocumentRequest,
    background_tasks: BackgroundTasks,
):
    """Ingest a single document into the knowledge base.
    
    Document is processed asynchronously via Celery task.
    """
    try:
        # Validate document type
        try:
            DocumentType(request.doc_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid document type. Valid types: {[dt.value for dt in DocumentType]}"
            )
        
        # Queue ingestion task
        task = ingest_document_task.delay(
            document_id=request.document_id,
            content=request.content,
            doc_type=request.doc_type,
            jurisdiction=request.jurisdiction,
            citation=request.citation,
            metadata=request.metadata,
        )
        
        return IngestResponse(
            status="queued",
            message=f"Document {request.document_id} queued for ingestion",
            task_id=task.id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document ingestion request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/rule-pack/{jurisdiction}", response_model=IngestResponse)
async def ingest_jurisdiction_rules(
    jurisdiction: str,
    background_tasks: BackgroundTasks,
):
    """Ingest a jurisdiction rule pack into the knowledge base.
    
    Processes the rule pack YAML file and creates searchable chunks
    for initiation procedures, compensation rules, owner rights, etc.
    """
    try:
        jurisdiction = jurisdiction.upper()
        
        # Queue ingestion task
        task = ingest_rule_pack_task.delay(jurisdiction)
        
        return IngestResponse(
            status="queued",
            message=f"Rule pack {jurisdiction} queued for ingestion",
            task_id=task.id,
        )
        
    except Exception as e:
        logger.error(f"Rule pack ingestion request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/all-rules", response_model=IngestResponse)
async def ingest_all_jurisdiction_rules(background_tasks: BackgroundTasks):
    """Ingest all available jurisdiction rule packs.
    
    Scans the rules directory and ingests all YAML rule packs.
    """
    try:
        task = ingest_all_rule_packs.delay()
        
        return IngestResponse(
            status="queued",
            message="All rule packs queued for ingestion",
            task_id=task.id,
        )
        
    except Exception as e:
        logger.error(f"Batch rule ingestion request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh", response_model=IngestResponse)
async def trigger_knowledge_base_refresh(background_tasks: BackgroundTasks):
    """Trigger a full knowledge base refresh.
    
    Re-ingests all rule packs and updates collection statistics.
    """
    try:
        task = refresh_knowledge_base.delay()
        
        return IngestResponse(
            status="queued",
            message="Knowledge base refresh queued",
            task_id=task.id,
        )
        
    except Exception as e:
        logger.error(f"Refresh request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Health & Stats Endpoints
# =============================================================================

@router.get("/health", response_model=HealthResponse)
async def check_rag_health():
    """Check RAG service health status.
    
    Returns status of ChromaDB, embedding model, and document counts.
    """
    try:
        health = await health_check()
        return HealthResponse(**health)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_knowledge_base_stats():
    """Get knowledge base statistics.
    
    Returns document counts, collection info, and configuration.
    """
    try:
        stats = get_collection_stats()
        return stats
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/doc-types")
async def list_document_types():
    """List available document types for the knowledge base."""
    return {
        "doc_types": [
            {"value": dt.value, "name": dt.name}
            for dt in DocumentType
        ]
    }
