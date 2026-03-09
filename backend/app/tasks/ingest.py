"""Celery tasks for RAG document ingestion.

These tasks support the knowledge base by:
- Ingesting jurisdiction rule packs from YAML files
- Processing uploaded documents for embedding
- Batch ingestion of case outcomes
- Scheduled refreshes of the knowledge base
"""

from celery import shared_task
from typing import Any
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to rules directory (relative to repo root)
RULES_DIR = Path(__file__).resolve().parents[3] / "rules"


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def ingest_rule_pack_task(self, jurisdiction: str) -> dict[str, Any]:
    """Ingest a single jurisdiction rule pack into the RAG knowledge base.
    
    Args:
        jurisdiction: State code (TX, IN, CA, etc.)
        
    Returns:
        Ingestion stats with success/failure counts
    """
    import yaml
    import asyncio
    from app.services.rag_service import ingest_rule_pack
    
    try:
        # Load rule pack YAML
        rule_path = RULES_DIR / f"{jurisdiction.lower()}.yaml"
        if not rule_path.exists():
            logger.error(f"Rule pack not found: {rule_path}")
            return {"success": 0, "failed": 0, "error": f"Rule pack not found: {jurisdiction}"}
        
        with open(rule_path) as f:
            rule_data = yaml.safe_load(f)
        
        if not rule_data:
            return {"success": 0, "failed": 0, "error": "Empty rule pack"}
        
        # Run async ingestion
        loop = asyncio.new_event_loop()
        try:
            stats = loop.run_until_complete(ingest_rule_pack(jurisdiction, rule_data))
            logger.info(f"Ingested rule pack {jurisdiction}: {stats}")
            return stats
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Rule pack ingestion failed for {jurisdiction}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3)
def ingest_all_rule_packs(self) -> dict[str, Any]:
    """Ingest all available jurisdiction rule packs.
    
    Returns:
        Aggregated stats for all jurisdictions
    """
    import yaml
    import asyncio
    from app.services.rag_service import ingest_rule_pack
    
    results = {
        "jurisdictions_processed": 0,
        "total_success": 0,
        "total_failed": 0,
        "errors": [],
    }
    
    try:
        # Find all rule pack YAML files
        rule_files = list(RULES_DIR.glob("*.yaml"))
        
        # Exclude schema files and base
        rule_files = [
            f for f in rule_files 
            if f.stem not in ("base", "schema") and not f.stem.startswith("_")
        ]
        
        loop = asyncio.new_event_loop()
        try:
            for rule_file in rule_files:
                jurisdiction = rule_file.stem.upper()
                
                try:
                    with open(rule_file) as f:
                        rule_data = yaml.safe_load(f)
                    
                    if rule_data:
                        stats = loop.run_until_complete(
                            ingest_rule_pack(jurisdiction, rule_data)
                        )
                        results["jurisdictions_processed"] += 1
                        results["total_success"] += stats.get("success", 0)
                        results["total_failed"] += stats.get("failed", 0)
                        
                except Exception as e:
                    logger.error(f"Failed to ingest {jurisdiction}: {e}")
                    results["errors"].append(f"{jurisdiction}: {str(e)}")
        finally:
            loop.close()
        
        logger.info(f"Ingested all rule packs: {results}")
        return results
        
    except Exception as exc:
        logger.error(f"Batch rule pack ingestion failed: {exc}")
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def ingest_document_task(
    self,
    document_id: str,
    content: str,
    doc_type: str,
    jurisdiction: str = None,
    citation: str = None,
    metadata: dict = None,
) -> dict[str, Any]:
    """Ingest a single document into the RAG knowledge base.
    
    Args:
        document_id: Unique document identifier
        content: Document text content
        doc_type: Document type (statute, case_law, template, etc.)
        jurisdiction: Optional jurisdiction code
        citation: Optional legal citation
        metadata: Optional additional metadata
        
    Returns:
        Ingestion result
    """
    import asyncio
    from app.services.rag_service import (
        ingest_document, 
        DocumentChunk, 
        DocumentType,
        _generate_chunk_id,
    )
    
    try:
        # Create document chunk
        chunk = DocumentChunk(
            id=_generate_chunk_id(content, document_id),
            content=content,
            doc_type=DocumentType(doc_type),
            jurisdiction=jurisdiction,
            citation=citation,
            source_path=document_id,
            metadata=metadata or {},
        )
        
        loop = asyncio.new_event_loop()
        try:
            success = loop.run_until_complete(ingest_document(chunk))
            return {
                "success": success,
                "document_id": document_id,
                "chunk_id": chunk.id,
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Document ingestion failed for {document_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True)
def ingest_case_outcome(
    self,
    case_id: str,
    jurisdiction: str,
    outcome_data: dict[str, Any],
) -> dict[str, Any]:
    """Ingest a case outcome for learning and prediction.
    
    This creates searchable context from historical case outcomes
    to inform AI predictions and recommendations.
    
    Args:
        case_id: Case identifier
        jurisdiction: State code
        outcome_data: Case outcome details including:
            - property_type: Type of property
            - assessed_value: Initial assessed value
            - offer_amount: Initial offer
            - final_settlement: Final settlement amount
            - timeline_days: Days from offer to settlement
            - went_to_litigation: Boolean
            - litigation_outcome: If applicable
            - factors: Key factors that influenced outcome
            
    Returns:
        Ingestion result
    """
    import asyncio
    from app.services.rag_service import (
        ingest_document,
        DocumentChunk,
        DocumentType,
        _generate_chunk_id,
    )
    
    try:
        # Format outcome as searchable text
        content_parts = [
            f"Case Outcome - {jurisdiction} ({case_id})",
            f"Property Type: {outcome_data.get('property_type', 'Unknown')}",
            f"Assessed Value: ${outcome_data.get('assessed_value', 0):,.2f}",
            f"Initial Offer: ${outcome_data.get('offer_amount', 0):,.2f}",
            f"Final Settlement: ${outcome_data.get('final_settlement', 0):,.2f}",
        ]
        
        # Calculate settlement ratio
        assessed = outcome_data.get("assessed_value", 0)
        final = outcome_data.get("final_settlement", 0)
        if assessed > 0:
            ratio = final / assessed
            content_parts.append(f"Settlement Ratio: {ratio:.2%} of assessed value")
        
        # Timeline
        timeline = outcome_data.get("timeline_days")
        if timeline:
            content_parts.append(f"Timeline: {timeline} days from offer to settlement")
        
        # Litigation
        if outcome_data.get("went_to_litigation"):
            lit_outcome = outcome_data.get("litigation_outcome", "Unknown")
            content_parts.append(f"Litigation: Yes - {lit_outcome}")
        else:
            content_parts.append("Litigation: No (settled voluntarily)")
        
        # Key factors
        factors = outcome_data.get("factors", [])
        if factors:
            content_parts.append("Key Factors: " + ", ".join(factors))
        
        content = "\n".join(content_parts)
        
        chunk = DocumentChunk(
            id=_generate_chunk_id(content, f"outcome/{case_id}"),
            content=content,
            doc_type=DocumentType.CASE_OUTCOME,
            jurisdiction=jurisdiction,
            source_path=f"case_outcomes/{case_id}",
            metadata={
                "case_id": case_id,
                "property_type": outcome_data.get("property_type", ""),
                "went_to_litigation": str(outcome_data.get("went_to_litigation", False)),
                "settlement_ratio": str(ratio) if assessed > 0 else "",
            },
        )
        
        loop = asyncio.new_event_loop()
        try:
            success = loop.run_until_complete(ingest_document(chunk))
            return {
                "success": success,
                "case_id": case_id,
                "chunk_id": chunk.id,
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Case outcome ingestion failed for {case_id}: {exc}")
        raise


@shared_task
def refresh_knowledge_base() -> dict[str, Any]:
    """Scheduled task to refresh the knowledge base.
    
    This task:
    1. Re-ingests all rule packs to pick up changes
    2. Prunes stale documents
    3. Reports collection statistics
    
    Returns:
        Refresh stats
    """
    import asyncio
    from app.services.rag_service import get_collection_stats
    
    logger.info("Starting knowledge base refresh")
    
    # Re-ingest all rule packs
    rule_stats = ingest_all_rule_packs()
    
    # Get collection stats
    collection_stats = get_collection_stats()
    
    return {
        "rule_ingestion": rule_stats,
        "collection": collection_stats,
        "status": "completed",
    }
