"""RAG (Retrieval-Augmented Generation) Knowledge Base Service.

Provides semantic search over legal statutes, case law, and historical case outcomes
using Vertex AI Embeddings and ChromaDB vector store.

Key features:
- Jurisdiction-aware document retrieval
- Statute/rule ingestion from YAML citations
- Case document embedding and search
- Caching and batch processing
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from enum import Enum

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentType(str, Enum):
    """Types of documents in the knowledge base."""
    STATUTE = "statute"
    CASE_LAW = "case_law"
    RULE_PACK = "rule_pack"
    TEMPLATE = "template"
    CASE_OUTCOME = "case_outcome"
    LEGAL_MEMO = "legal_memo"


@dataclass
class DocumentChunk:
    """A chunk of text with metadata for embedding."""
    id: str
    content: str
    doc_type: DocumentType
    jurisdiction: Optional[str] = None
    citation: Optional[str] = None
    source_path: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_metadata(self) -> dict[str, Any]:
        """Convert to ChromaDB metadata format."""
        return {
            "doc_type": self.doc_type.value,
            "jurisdiction": self.jurisdiction or "",
            "citation": self.citation or "",
            "source_path": self.source_path or "",
            **{k: str(v) if not isinstance(v, (str, int, float, bool)) else v 
               for k, v in self.metadata.items()}
        }


@dataclass
class RetrievalResult:
    """Result from a knowledge base search."""
    chunk_id: str
    content: str
    relevance_score: float
    doc_type: DocumentType
    jurisdiction: Optional[str]
    citation: Optional[str]
    metadata: dict[str, Any]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "relevance_score": self.relevance_score,
            "doc_type": self.doc_type.value,
            "jurisdiction": self.jurisdiction,
            "citation": self.citation,
            "metadata": self.metadata,
        }


@dataclass
class SearchRequest:
    """Request for knowledge base search."""
    query: str
    jurisdiction: Optional[str] = None
    doc_types: Optional[list[DocumentType]] = None
    top_k: int = 5
    min_score: float = 0.7


# Lazy-loaded clients
_chroma_client = None
_collection = None
_embedding_model = None


def _generate_chunk_id(content: str, source: str = "") -> str:
    """Generate deterministic ID for a document chunk."""
    hash_input = f"{source}:{content}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


def get_embedding_model():
    """Lazily initialize the Vertex AI embedding model."""
    global _embedding_model
    
    if _embedding_model is None and settings.rag_enabled:
        try:
            import vertexai
            from vertexai.language_models import TextEmbeddingModel
            
            vertexai.init(
                project=settings.gcp_project or None,
                location=settings.gemini_location,
            )
            
            _embedding_model = TextEmbeddingModel.from_pretrained(
                settings.rag_embedding_model
            )
            logger.info(f"Initialized embedding model: {settings.rag_embedding_model}")
            
        except Exception as e:
            logger.warning(f"Failed to initialize embedding model: {e}")
            _embedding_model = None
    
    return _embedding_model


def get_chroma_collection():
    """Lazily initialize ChromaDB collection."""
    global _chroma_client, _collection
    
    if _collection is None and settings.rag_enabled:
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            
            # Create persist directory if needed
            persist_dir = Path(settings.rag_persist_directory)
            persist_dir.mkdir(parents=True, exist_ok=True)
            
            _chroma_client = chromadb.Client(ChromaSettings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=str(persist_dir),
                anonymized_telemetry=False,
            ))
            
            _collection = _chroma_client.get_or_create_collection(
                name=settings.rag_collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info(f"Initialized ChromaDB collection: {settings.rag_collection_name}")
            
        except Exception as e:
            logger.warning(f"Failed to initialize ChromaDB: {e}")
            _collection = None
    
    return _collection


async def embed_text(text: str) -> Optional[list[float]]:
    """Generate embedding for a text using Vertex AI.
    
    Args:
        text: Text to embed
        
    Returns:
        Embedding vector or None if unavailable
    """
    model = get_embedding_model()
    if model is None:
        logger.debug("Embedding model not available")
        return None
    
    try:
        embeddings = model.get_embeddings([text])
        if embeddings and len(embeddings) > 0:
            return embeddings[0].values
        return None
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return None


async def embed_texts_batch(texts: list[str]) -> list[Optional[list[float]]]:
    """Generate embeddings for multiple texts in batch.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embedding vectors (None for failed embeddings)
    """
    model = get_embedding_model()
    if model is None:
        return [None] * len(texts)
    
    try:
        # Vertex AI supports batch embedding
        embeddings = model.get_embeddings(texts)
        return [e.values if e else None for e in embeddings]
    except Exception as e:
        logger.error(f"Batch embedding failed: {e}")
        return [None] * len(texts)


async def ingest_document(chunk: DocumentChunk) -> bool:
    """Ingest a single document chunk into the knowledge base.
    
    Args:
        chunk: Document chunk to ingest
        
    Returns:
        True if successful
    """
    collection = get_chroma_collection()
    if collection is None:
        logger.warning("ChromaDB not available, skipping ingestion")
        return False
    
    # Generate embedding
    embedding = await embed_text(chunk.content)
    if embedding is None:
        logger.warning(f"Failed to embed chunk {chunk.id}")
        return False
    
    try:
        collection.add(
            ids=[chunk.id],
            embeddings=[embedding],
            documents=[chunk.content],
            metadatas=[chunk.to_metadata()],
        )
        logger.debug(f"Ingested chunk {chunk.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to ingest chunk {chunk.id}: {e}")
        return False


async def ingest_documents_batch(chunks: list[DocumentChunk]) -> dict[str, int]:
    """Ingest multiple document chunks in batch.
    
    Args:
        chunks: List of document chunks to ingest
        
    Returns:
        Stats dict with success/failure counts
    """
    collection = get_chroma_collection()
    if collection is None:
        return {"success": 0, "failed": len(chunks), "skipped": 0}
    
    # Generate embeddings in batch
    texts = [c.content for c in chunks]
    embeddings = await embed_texts_batch(texts)
    
    # Filter out chunks with failed embeddings
    valid_chunks = []
    valid_embeddings = []
    failed_count = 0
    
    for chunk, embedding in zip(chunks, embeddings):
        if embedding is not None:
            valid_chunks.append(chunk)
            valid_embeddings.append(embedding)
        else:
            failed_count += 1
    
    if not valid_chunks:
        return {"success": 0, "failed": failed_count, "skipped": 0}
    
    try:
        collection.add(
            ids=[c.id for c in valid_chunks],
            embeddings=valid_embeddings,
            documents=[c.content for c in valid_chunks],
            metadatas=[c.to_metadata() for c in valid_chunks],
        )
        logger.info(f"Batch ingested {len(valid_chunks)} chunks")
        return {"success": len(valid_chunks), "failed": failed_count, "skipped": 0}
    except Exception as e:
        logger.error(f"Batch ingestion failed: {e}")
        return {"success": 0, "failed": len(chunks), "skipped": 0}


async def search(request: SearchRequest) -> list[RetrievalResult]:
    """Search the knowledge base for relevant documents.
    
    Args:
        request: Search request with query and filters
        
    Returns:
        List of retrieval results sorted by relevance
    """
    collection = get_chroma_collection()
    if collection is None:
        logger.warning("ChromaDB not available for search")
        return []
    
    # Generate query embedding
    query_embedding = await embed_text(request.query)
    if query_embedding is None:
        logger.warning("Failed to embed query")
        return []
    
    # Build where filter
    where_filter = {}
    if request.jurisdiction:
        where_filter["jurisdiction"] = request.jurisdiction
    if request.doc_types:
        # ChromaDB uses $in for multiple values
        if len(request.doc_types) == 1:
            where_filter["doc_type"] = request.doc_types[0].value
        else:
            where_filter["doc_type"] = {"$in": [dt.value for dt in request.doc_types]}
    
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=request.top_k,
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"],
        )
        
        retrieval_results = []
        
        if results and results["ids"] and len(results["ids"]) > 0:
            for i, chunk_id in enumerate(results["ids"][0]):
                # ChromaDB returns distance, convert to similarity score
                # For cosine distance: similarity = 1 - distance
                distance = results["distances"][0][i] if results["distances"] else 0
                score = 1 - distance
                
                # Filter by minimum score
                if score < request.min_score:
                    continue
                
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                content = results["documents"][0][i] if results["documents"] else ""
                
                retrieval_results.append(RetrievalResult(
                    chunk_id=chunk_id,
                    content=content,
                    relevance_score=score,
                    doc_type=DocumentType(metadata.get("doc_type", "statute")),
                    jurisdiction=metadata.get("jurisdiction") or None,
                    citation=metadata.get("citation") or None,
                    metadata=metadata,
                ))
        
        logger.debug(f"Search returned {len(retrieval_results)} results for: {request.query[:50]}...")
        return retrieval_results
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []


async def search_for_context(
    query: str,
    jurisdiction: Optional[str] = None,
    top_k: int = None,
) -> list[RetrievalResult]:
    """Convenience method for AI agents to retrieve context.
    
    Args:
        query: Search query (can be a case summary or question)
        jurisdiction: Optional jurisdiction filter
        top_k: Number of results (defaults to settings)
        
    Returns:
        List of relevant document chunks
    """
    request = SearchRequest(
        query=query,
        jurisdiction=jurisdiction,
        top_k=top_k or settings.rag_top_k,
        min_score=settings.rag_min_relevance_score,
    )
    return await search(request)


def format_context_for_prompt(results: list[RetrievalResult]) -> str:
    """Format retrieval results for inclusion in an LLM prompt.
    
    Args:
        results: List of retrieval results
        
    Returns:
        Formatted context string
    """
    if not results:
        return "No relevant legal context found."
    
    context_parts = []
    for i, result in enumerate(results, 1):
        citation = result.citation or "Unknown source"
        jurisdiction = f" [{result.jurisdiction}]" if result.jurisdiction else ""
        context_parts.append(
            f"[{i}] {citation}{jurisdiction} (relevance: {result.relevance_score:.2f}):\n"
            f"{result.content}\n"
        )
    
    return "RELEVANT LEGAL CONTEXT:\n" + "\n".join(context_parts)


# =============================================================================
# Rule Pack Ingestion
# =============================================================================

async def ingest_rule_pack(jurisdiction: str, rule_data: dict[str, Any]) -> dict[str, int]:
    """Ingest a jurisdiction rule pack into the knowledge base.
    
    Extracts and embeds:
    - Rule descriptions with citations
    - Deadline chain descriptions
    - Compensation rules
    - Notice requirements
    
    Args:
        jurisdiction: State code (TX, IN, etc.)
        rule_data: Parsed rule YAML data
        
    Returns:
        Ingestion stats
    """
    chunks = []
    
    # Extract citations section
    citations = rule_data.get("citations", {})
    primary_citation = citations.get("primary", "")
    constitution = citations.get("constitution", "")
    
    # Create chunk for initiation procedures
    initiation = rule_data.get("initiation", {})
    if initiation:
        init_text = _format_initiation_rules(initiation, jurisdiction)
        chunks.append(DocumentChunk(
            id=_generate_chunk_id(init_text, f"{jurisdiction}/initiation"),
            content=init_text,
            doc_type=DocumentType.RULE_PACK,
            jurisdiction=jurisdiction,
            citation=primary_citation,
            source_path=f"rules/{jurisdiction.lower()}.yaml",
            metadata={"section": "initiation"},
        ))
    
    # Create chunk for compensation rules
    compensation = rule_data.get("compensation", {})
    if compensation:
        comp_text = _format_compensation_rules(compensation, jurisdiction)
        chunks.append(DocumentChunk(
            id=_generate_chunk_id(comp_text, f"{jurisdiction}/compensation"),
            content=comp_text,
            doc_type=DocumentType.RULE_PACK,
            jurisdiction=jurisdiction,
            citation=primary_citation,
            source_path=f"rules/{jurisdiction.lower()}.yaml",
            metadata={"section": "compensation"},
        ))
    
    # Create chunk for owner rights
    owner_rights = rule_data.get("owner_rights", {})
    if owner_rights:
        rights_text = _format_owner_rights(owner_rights, jurisdiction)
        chunks.append(DocumentChunk(
            id=_generate_chunk_id(rights_text, f"{jurisdiction}/owner_rights"),
            content=rights_text,
            doc_type=DocumentType.RULE_PACK,
            jurisdiction=jurisdiction,
            citation=primary_citation,
            source_path=f"rules/{jurisdiction.lower()}.yaml",
            metadata={"section": "owner_rights"},
        ))
    
    # Create chunk for public use limitations
    public_use = rule_data.get("public_use", {})
    if public_use:
        pu_text = _format_public_use_rules(public_use, jurisdiction)
        chunks.append(DocumentChunk(
            id=_generate_chunk_id(pu_text, f"{jurisdiction}/public_use"),
            content=pu_text,
            doc_type=DocumentType.RULE_PACK,
            jurisdiction=jurisdiction,
            citation=citations.get("additional", [primary_citation])[0] if citations.get("additional") else primary_citation,
            source_path=f"rules/{jurisdiction.lower()}.yaml",
            metadata={"section": "public_use"},
        ))
    
    # Create chunks for deadline chains
    deadline_chains = rule_data.get("deadline_chains", [])
    for chain in deadline_chains:
        chain_text = _format_deadline_chain(chain, jurisdiction)
        anchor = chain.get("anchor_event", "unknown")
        chunks.append(DocumentChunk(
            id=_generate_chunk_id(chain_text, f"{jurisdiction}/deadline/{anchor}"),
            content=chain_text,
            doc_type=DocumentType.RULE_PACK,
            jurisdiction=jurisdiction,
            citation=primary_citation,
            source_path=f"rules/{jurisdiction.lower()}.yaml",
            metadata={"section": "deadline_chain", "anchor_event": anchor},
        ))
    
    if not chunks:
        return {"success": 0, "failed": 0, "skipped": 0}
    
    return await ingest_documents_batch(chunks)


def _format_initiation_rules(initiation: dict, jurisdiction: str) -> str:
    """Format initiation rules for embedding."""
    parts = [f"{jurisdiction} Eminent Domain Initiation Requirements:"]
    
    if initiation.get("landowner_bill_of_rights"):
        parts.append("- Landowner Bill of Rights document is REQUIRED")
    if initiation.get("pre_condemnation_offer_required"):
        parts.append("- Pre-condemnation offer is required")
    if initiation.get("appraisal_based_offer"):
        parts.append("- Offer must be based on professional appraisal")
    if initiation.get("resolution_required"):
        body = initiation.get("resolution_body", "governing body")
        parts.append(f"- Resolution required from {body}")
    
    initial_days = initiation.get("initial_offer_days")
    if initial_days:
        parts.append(f"- Initial offer wait period: {initial_days} days")
    
    final_days = initiation.get("final_offer_days")
    if final_days:
        parts.append(f"- Final offer consideration period: {final_days} days")
    
    quick_take = initiation.get("quick_take", {})
    if quick_take.get("available"):
        qt_type = quick_take.get("type", "deposit and possession")
        parts.append(f"- Quick-take is available via {qt_type}")
        if quick_take.get("court_approval_required"):
            parts.append("  - Court approval required for quick-take")
    
    return "\n".join(parts)


def _format_compensation_rules(compensation: dict, jurisdiction: str) -> str:
    """Format compensation rules for embedding."""
    parts = [f"{jurisdiction} Compensation Requirements:"]
    
    base = compensation.get("base", "fair_market_value")
    const_term = compensation.get("constitutional_term", "just compensation")
    parts.append(f"- Standard: {base} ({const_term})")
    
    if compensation.get("highest_and_best_use"):
        parts.append("- Valuation based on highest and best use")
    if compensation.get("includes_severance"):
        parts.append("- Severance damages to remainder property are compensable")
    
    # Multipliers
    res_mult = compensation.get("residence_multiplier")
    if res_mult:
        parts.append(f"- Owner-occupied residence multiplier: {res_mult}%")
    heritage_mult = compensation.get("heritage_multiplier")
    if heritage_mult:
        parts.append(f"- Heritage/long-term ownership multiplier: {heritage_mult}%")
    
    # Business compensation
    if compensation.get("business_goodwill"):
        parts.append("- Business goodwill IS compensable")
    else:
        parts.append("- Business goodwill is NOT compensable")
    
    # Attorney fees
    fees = compensation.get("attorney_fees", {})
    if fees.get("automatic"):
        parts.append("- Attorney fees are automatically awarded")
    elif fees.get("threshold_based"):
        desc = fees.get("threshold_description", "threshold exceeded")
        parts.append(f"- Attorney fees awarded if {desc}")
    else:
        parts.append("- No automatic attorney fee recovery")
    
    return "\n".join(parts)


def _format_owner_rights(owner_rights: dict, jurisdiction: str) -> str:
    """Format owner rights for embedding."""
    parts = [f"{jurisdiction} Owner Rights:"]
    
    if owner_rights.get("jury_trial"):
        parts.append("- Right to jury trial on compensation")
    
    panel = owner_rights.get("commissioners_panel")
    if panel:
        desc = owner_rights.get("commissioners_description", "appointed panel")
        parts.append(f"- Compensation determined by {panel} ({desc})")
    
    if owner_rights.get("public_use_challenge"):
        parts.append("- Owner can challenge public use determination")
    if owner_rights.get("necessity_challenge"):
        parts.append("- Owner can challenge necessity finding")
    
    notice = owner_rights.get("notice_periods", {})
    for period_name, days in notice.items():
        if days:
            parts.append(f"- {period_name.replace('_', ' ').title()}: {days} days")
    
    return "\n".join(parts)


def _format_public_use_rules(public_use: dict, jurisdiction: str) -> str:
    """Format public use limitations for embedding."""
    parts = [f"{jurisdiction} Public Use Limitations:"]
    
    if public_use.get("economic_development_banned"):
        parts.append("- Economic development takings are BANNED")
    if public_use.get("tax_revenue_purpose_banned"):
        parts.append("- Takings for tax revenue enhancement are BANNED")
    
    blight = public_use.get("blight_for_private")
    if blight == "restricted":
        parts.append("- Blight takings for private use are restricted")
    elif blight == "prohibited":
        parts.append("- Blight takings for private transfer are prohibited")
    
    if public_use.get("blight_parcel_specific"):
        parts.append("- Blight determination required on parcel-by-parcel basis")
    
    reform_year = public_use.get("post_kelo_reform_year")
    reform_type = public_use.get("reform_type")
    if reform_year:
        parts.append(f"- Post-Kelo reform enacted in {reform_year} ({reform_type})")
    
    return "\n".join(parts)


def _format_deadline_chain(chain: dict, jurisdiction: str) -> str:
    """Format a deadline chain for embedding."""
    anchor = chain.get("anchor_event", "unknown event")
    description = chain.get("description", "")
    
    parts = [f"{jurisdiction} Deadline Chain - {anchor}:"]
    if description:
        parts.append(f"Triggered when: {description}")
    
    deadlines = chain.get("deadlines", [])
    for dl in deadlines:
        dl_id = dl.get("id", "")
        dl_desc = dl.get("description", "")
        offset = dl.get("offset_days", 0)
        direction = dl.get("direction", "after")
        citation = dl.get("citation", "")
        
        deadline_str = f"- {dl_id}: {dl_desc} ({offset} days {direction})"
        if citation:
            deadline_str += f" [{citation}]"
        parts.append(deadline_str)
    
    return "\n".join(parts)


# =============================================================================
# Initialization and Health Check
# =============================================================================

def get_collection_stats() -> dict[str, Any]:
    """Get statistics about the knowledge base collection.
    
    Returns:
        Stats dict with document counts, etc.
    """
    collection = get_chroma_collection()
    if collection is None:
        return {"status": "unavailable", "count": 0}
    
    try:
        count = collection.count()
        return {
            "status": "healthy",
            "collection_name": settings.rag_collection_name,
            "document_count": count,
            "embedding_model": settings.rag_embedding_model,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def health_check() -> dict[str, Any]:
    """Perform health check on RAG service components.
    
    Returns:
        Health status dict
    """
    result = {
        "rag_enabled": settings.rag_enabled,
        "chroma_status": "unknown",
        "embedding_status": "unknown",
    }
    
    if not settings.rag_enabled:
        result["chroma_status"] = "disabled"
        result["embedding_status"] = "disabled"
        return result
    
    # Check ChromaDB
    collection = get_chroma_collection()
    if collection:
        result["chroma_status"] = "healthy"
        result["document_count"] = collection.count()
    else:
        result["chroma_status"] = "unavailable"
    
    # Check embedding model
    model = get_embedding_model()
    if model:
        result["embedding_status"] = "healthy"
        result["embedding_model"] = settings.rag_embedding_model
    else:
        result["embedding_status"] = "unavailable"
    
    return result
