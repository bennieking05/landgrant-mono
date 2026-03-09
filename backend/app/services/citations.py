"""Citation and Provenance Service.

Provides evidence-grade citation management:
- Source ingestion and hashing
- Citation linking to AI outputs
- Citation verification
- Claim checking

Every AI-generated legal assertion must be backed by a citation
to an authoritative source.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app.services.hashing import sha256_hex


@dataclass
class SourceInput:
    """Input for creating a new source."""
    title: str
    jurisdiction: str
    authority_level: str
    citation_string: Optional[str] = None
    url: Optional[str] = None
    raw_text: Optional[str] = None
    effective_date: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None


@dataclass
class CitationInput:
    """Input for creating a citation link."""
    source_id: str
    used_in_type: str  # ai_decision, document, rule_result
    used_in_id: str
    snippet: str
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    section: Optional[str] = None
    pin_cite: Optional[str] = None


@dataclass
class ClaimWithCitation:
    """An AI claim with its supporting citation."""
    text: str
    citations: list[dict[str, Any]]
    confidence: float
    verified: bool = False
    verification_notes: Optional[str] = None


@dataclass
class ClaimCheckResult:
    """Result of claim verification."""
    claim_text: str
    is_valid: bool
    citation_found: bool
    source_verified: bool
    snippet_matches: bool
    issues: list[str] = field(default_factory=list)


class CitationService:
    """Service for managing citations and source provenance."""

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize the service.
        
        Args:
            storage_path: Path for storing source text files
        """
        self.storage_path = storage_path or Path("/tmp/landright/sources")
        self._ensure_storage()
        
        # In-memory store for demo (would be DB in production)
        self._sources: dict[str, dict[str, Any]] = {}
        self._citations: dict[str, dict[str, Any]] = {}

    def _ensure_storage(self) -> None:
        """Ensure storage directories exist."""
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def create_source(self, input: SourceInput) -> dict[str, Any]:
        """Create a new source record.
        
        Args:
            input: Source input data
            
        Returns:
            Created source record
        """
        source_id = f"src_{uuid.uuid4().hex[:12]}"
        
        # Compute content hash
        content_hash = ""
        raw_text_path = None
        raw_text_snippet = None
        
        if input.raw_text:
            content_hash = sha256_hex(input.raw_text.encode())
            
            # Store full text if large
            if len(input.raw_text) > 10000:
                raw_text_path = str(self.storage_path / f"{source_id}.txt")
                Path(raw_text_path).write_text(input.raw_text)
                raw_text_snippet = input.raw_text[:10000]
            else:
                raw_text_snippet = input.raw_text
        else:
            # Hash the metadata as fallback
            content_hash = sha256_hex(
                f"{input.title}|{input.jurisdiction}|{input.citation_string}".encode()
            )

        source = {
            "id": source_id,
            "title": input.title,
            "jurisdiction": input.jurisdiction.upper(),
            "authority_level": input.authority_level,
            "citation_string": input.citation_string,
            "url": input.url,
            "content_hash": content_hash,
            "raw_text_path": raw_text_path,
            "raw_text_snippet": raw_text_snippet,
            "effective_date": input.effective_date.isoformat() if input.effective_date else None,
            "metadata_json": input.metadata or {},
            "verified": False,
            "retrieved_at": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
        }
        
        self._sources[source_id] = source
        return source

    def get_source(self, source_id: str) -> Optional[dict[str, Any]]:
        """Get a source by ID.
        
        Args:
            source_id: Source identifier
            
        Returns:
            Source record or None
        """
        return self._sources.get(source_id)

    def search_sources(
        self,
        jurisdiction: Optional[str] = None,
        authority_level: Optional[str] = None,
        query: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Search sources by criteria.
        
        Args:
            jurisdiction: Filter by jurisdiction
            authority_level: Filter by authority level
            query: Text search in title/citation
            
        Returns:
            Matching sources
        """
        results = []
        
        for source in self._sources.values():
            if jurisdiction and source["jurisdiction"] != jurisdiction.upper():
                continue
            if authority_level and source["authority_level"] != authority_level:
                continue
            if query:
                query_lower = query.lower()
                if (query_lower not in (source.get("title") or "").lower() and
                    query_lower not in (source.get("citation_string") or "").lower()):
                    continue
            results.append(source)
        
        return results

    def verify_source(
        self,
        source_id: str,
        user_id: str,
        notes: Optional[str] = None,
    ) -> dict[str, Any]:
        """Mark a source as verified.
        
        Args:
            source_id: Source identifier
            user_id: ID of verifying user
            notes: Optional verification notes
            
        Returns:
            Updated source
        """
        source = self._sources.get(source_id)
        if not source:
            raise ValueError(f"Source {source_id} not found")
        
        source["verified"] = True
        source["verified_by"] = user_id
        source["verified_at"] = datetime.utcnow().isoformat()
        if notes:
            source["verification_notes"] = notes
        
        return source

    def create_citation(self, input: CitationInput) -> dict[str, Any]:
        """Create a citation linking content to a source.
        
        Args:
            input: Citation input data
            
        Returns:
            Created citation record
        """
        # Verify source exists
        source = self.get_source(input.source_id)
        if not source:
            raise ValueError(f"Source {input.source_id} not found")
        
        citation_id = f"cit_{uuid.uuid4().hex[:12]}"
        snippet_hash = sha256_hex(input.snippet.encode())
        
        citation = {
            "id": citation_id,
            "source_id": input.source_id,
            "used_in_type": input.used_in_type,
            "used_in_id": input.used_in_id,
            "snippet": input.snippet,
            "snippet_hash": snippet_hash,
            "span_start": input.span_start,
            "span_end": input.span_end,
            "section": input.section,
            "pin_cite": input.pin_cite,
            "verified": False,
            "verification_status": "pending",
            "created_at": datetime.utcnow().isoformat(),
        }
        
        self._citations[citation_id] = citation
        return citation

    def get_citations_for_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> list[dict[str, Any]]:
        """Get all citations for an entity.
        
        Args:
            entity_type: Type of entity (ai_decision, document, etc.)
            entity_id: Entity identifier
            
        Returns:
            List of citations with source info
        """
        citations = []
        
        for citation in self._citations.values():
            if (citation["used_in_type"] == entity_type and 
                citation["used_in_id"] == entity_id):
                # Enrich with source info
                source = self.get_source(citation["source_id"])
                enriched = {**citation, "source": source}
                citations.append(enriched)
        
        return citations

    def verify_citation(
        self,
        citation_id: str,
        status: str,
        notes: Optional[str] = None,
    ) -> dict[str, Any]:
        """Update citation verification status.
        
        Args:
            citation_id: Citation identifier
            status: New status (verified, disputed)
            notes: Optional notes
            
        Returns:
            Updated citation
        """
        citation = self._citations.get(citation_id)
        if not citation:
            raise ValueError(f"Citation {citation_id} not found")
        
        citation["verification_status"] = status
        citation["verified"] = status == "verified"
        if notes:
            citation["verification_notes"] = notes
        
        return citation


class ClaimChecker:
    """Verifies AI claims against cited sources."""

    def __init__(self, citation_service: CitationService):
        """Initialize the checker.
        
        Args:
            citation_service: Citation service instance
        """
        self.citation_service = citation_service

    def check_claim(
        self,
        claim: ClaimWithCitation,
    ) -> ClaimCheckResult:
        """Verify a claim against its citations.
        
        Args:
            claim: Claim with citation references
            
        Returns:
            Verification result
        """
        issues = []
        citation_found = False
        source_verified = False
        snippet_matches = False
        
        if not claim.citations:
            issues.append("No citations provided for claim")
            return ClaimCheckResult(
                claim_text=claim.text,
                is_valid=False,
                citation_found=False,
                source_verified=False,
                snippet_matches=False,
                issues=issues,
            )
        
        for cit in claim.citations:
            source_id = cit.get("source_id")
            snippet_hash = cit.get("snippet_hash")
            
            if not source_id:
                issues.append("Citation missing source_id")
                continue
            
            source = self.citation_service.get_source(source_id)
            if not source:
                issues.append(f"Source {source_id} not found")
                continue
            
            citation_found = True
            
            if source.get("verified"):
                source_verified = True
            else:
                issues.append(f"Source {source_id} not verified")
            
            # Check snippet hash if provided
            if snippet_hash:
                snippet = cit.get("snippet", "")
                computed_hash = sha256_hex(snippet.encode())
                if computed_hash == snippet_hash:
                    snippet_matches = True
                else:
                    issues.append("Snippet hash mismatch")
            
            # Check if snippet exists in source text
            source_text = source.get("raw_text_snippet", "")
            snippet = cit.get("snippet", "")
            if snippet and source_text and snippet in source_text:
                snippet_matches = True
            elif snippet and source_text:
                issues.append("Snippet not found in source text")
        
        is_valid = citation_found and (source_verified or snippet_matches)
        
        return ClaimCheckResult(
            claim_text=claim.text,
            is_valid=is_valid,
            citation_found=citation_found,
            source_verified=source_verified,
            snippet_matches=snippet_matches,
            issues=issues,
        )

    def check_ai_output(
        self,
        output: dict[str, Any],
    ) -> dict[str, Any]:
        """Check all claims in an AI output.
        
        Expected output format:
        {
            "claims": [
                {
                    "text": "...",
                    "citations": [{"source_id": "...", "snippet_hash": "..."}],
                    "confidence": 0.95
                }
            ]
        }
        
        Args:
            output: AI output with claims
            
        Returns:
            Verification results for all claims
        """
        claims = output.get("claims", [])
        results = []
        all_valid = True
        missing_citations = []
        
        for i, claim_data in enumerate(claims):
            claim = ClaimWithCitation(
                text=claim_data.get("text", ""),
                citations=claim_data.get("citations", []),
                confidence=claim_data.get("confidence", 0.0),
            )
            
            result = self.check_claim(claim)
            results.append({
                "claim_index": i,
                "claim_text": result.claim_text[:100],
                "is_valid": result.is_valid,
                "citation_found": result.citation_found,
                "source_verified": result.source_verified,
                "snippet_matches": result.snippet_matches,
                "issues": result.issues,
            })
            
            if not result.is_valid:
                all_valid = False
            if not result.citation_found:
                missing_citations.append(i)
        
        return {
            "all_valid": all_valid,
            "claims_checked": len(claims),
            "claims_valid": sum(1 for r in results if r["is_valid"]),
            "missing_citations": missing_citations,
            "results": results,
        }


def require_citations(output: dict[str, Any]) -> bool:
    """Check if AI output has required citations.
    
    Rejects outputs that have legal assertions without citations.
    
    Args:
        output: AI output to check
        
    Returns:
        True if citations are present, False otherwise
    """
    claims = output.get("claims", [])
    
    for claim in claims:
        citations = claim.get("citations", [])
        if not citations:
            return False
        
        # Each citation must have source_id and snippet_hash
        for cit in citations:
            if not cit.get("source_id") or not cit.get("snippet_hash"):
                return False
    
    return True


def create_source_pack(
    sources: list[SourceInput],
    citation_service: CitationService,
) -> dict[str, Any]:
    """Create a pack of sources for a jurisdiction/topic.
    
    Args:
        sources: List of source inputs
        citation_service: Citation service instance
        
    Returns:
        Pack info with created source IDs
    """
    pack_id = f"srcpack_{uuid.uuid4().hex[:8]}"
    created_sources = []
    
    for source_input in sources:
        source = citation_service.create_source(source_input)
        created_sources.append(source)
    
    return {
        "pack_id": pack_id,
        "sources_created": len(created_sources),
        "source_ids": [s["id"] for s in created_sources],
        "sources": created_sources,
        "created_at": datetime.utcnow().isoformat(),
    }
