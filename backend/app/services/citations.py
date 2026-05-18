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

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

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
    """Service for managing citations and source provenance.

    Phase 1.5: when ``db`` is provided, records are persisted to the
    ``sources`` and ``citations`` tables.  Without a session we fall back to
    a per-instance in-memory store so existing unit tests keep running and
    the in-memory path is available for synthetic replay.
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        db: Optional[Session] = None,
    ):
        self.storage_path = storage_path or Path("/tmp/landgrant/sources")
        self._ensure_storage()
        self.db = db

        self._sources: dict[str, dict[str, Any]] = {}
        self._citations: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _source_row_to_dict(row: Any) -> dict[str, Any]:
        return {
            "id": row.id,
            "title": row.title,
            "jurisdiction": row.jurisdiction,
            "authority_level": (
                row.authority_level.value
                if hasattr(row.authority_level, "value")
                else row.authority_level
            ),
            "citation_string": row.citation_string,
            "url": row.url,
            "content_hash": row.content_hash,
            "raw_text_path": row.raw_text_path,
            "raw_text_snippet": row.raw_text_snippet,
            "effective_date": (
                row.effective_date.isoformat() if row.effective_date else None
            ),
            "metadata_json": row.metadata_json or {},
            "verified": bool(row.verified),
            "retrieved_at": (
                row.retrieved_at.isoformat() if row.retrieved_at else None
            ),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    @staticmethod
    def _citation_row_to_dict(row: Any) -> dict[str, Any]:
        return {
            "id": row.id,
            "source_id": row.source_id,
            "used_in_type": row.used_in_type,
            "used_in_id": row.used_in_id,
            "snippet": row.snippet,
            "snippet_hash": row.snippet_hash,
            "span_start": row.span_start,
            "span_end": row.span_end,
            "section": row.section,
            "pin_cite": row.pin_cite,
            "verified": bool(row.verified),
            "verification_status": row.verification_status,
            "verification_notes": row.verification_notes,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

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
            "effective_date": (
                input.effective_date.isoformat() if input.effective_date else None
            ),
            "metadata_json": input.metadata or {},
            "verified": False,
            "retrieved_at": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
        }

        if self.db is not None:
            from app.db import models

            row = models.Source(
                id=source_id,
                title=input.title,
                jurisdiction=input.jurisdiction.upper(),
                authority_level=input.authority_level,
                citation_string=input.citation_string,
                url=input.url,
                content_hash=content_hash,
                raw_text_path=raw_text_path,
                raw_text_snippet=raw_text_snippet,
                effective_date=input.effective_date,
                metadata_json=input.metadata or {},
                verified=False,
                retrieved_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            self.db.add(row)
            self.db.commit()
            return self._source_row_to_dict(row)

        self._sources[source_id] = source
        return source

    def get_source(self, source_id: str) -> Optional[dict[str, Any]]:
        if self.db is not None:
            from app.db import models

            row = self.db.get(models.Source, source_id)
            return self._source_row_to_dict(row) if row else None
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
        if self.db is not None:
            from app.db import models

            q = self.db.query(models.Source)
            if jurisdiction:
                q = q.filter(models.Source.jurisdiction == jurisdiction.upper())
            if authority_level:
                q = q.filter(models.Source.authority_level == authority_level)
            rows = q.order_by(models.Source.created_at.desc()).all()
            results = [self._source_row_to_dict(r) for r in rows]
            if query:
                ql = query.lower()
                results = [
                    r
                    for r in results
                    if ql in (r.get("title") or "").lower()
                    or ql in (r.get("citation_string") or "").lower()
                ]
            return results

        results = []
        for source in self._sources.values():
            if jurisdiction and source["jurisdiction"] != jurisdiction.upper():
                continue
            if authority_level and source["authority_level"] != authority_level:
                continue
            if query:
                query_lower = query.lower()
                if (
                    query_lower not in (source.get("title") or "").lower()
                    and query_lower not in (source.get("citation_string") or "").lower()
                ):
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
        if self.db is not None:
            from app.db import models

            row = self.db.get(models.Source, source_id)
            if not row:
                raise ValueError(f"Source {source_id} not found")
            row.verified = True
            row.verified_by = user_id
            row.verified_at = datetime.utcnow()
            self.db.commit()
            d = self._source_row_to_dict(row)
            d["verified_by"] = user_id
            if notes:
                d["verification_notes"] = notes
            return d

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
        source = self.get_source(input.source_id)
        if not source:
            raise ValueError(f"Source {input.source_id} not found")

        citation_id = f"cit_{uuid.uuid4().hex[:12]}"
        snippet_hash = sha256_hex(input.snippet.encode())

        if self.db is not None:
            from app.db import models

            row = models.Citation(
                id=citation_id,
                source_id=input.source_id,
                used_in_type=input.used_in_type,
                used_in_id=input.used_in_id,
                snippet=input.snippet,
                snippet_hash=snippet_hash,
                span_start=input.span_start,
                span_end=input.span_end,
                section=input.section,
                pin_cite=input.pin_cite,
                verified=False,
                verification_status="pending",
                created_at=datetime.utcnow(),
            )
            self.db.add(row)
            self.db.commit()
            return self._citation_row_to_dict(row)

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

        if self.db is not None:
            from app.db import models

            rows = (
                self.db.query(models.Citation)
                .filter(models.Citation.used_in_type == entity_type)
                .filter(models.Citation.used_in_id == entity_id)
                .all()
            )
            for row in rows:
                c = self._citation_row_to_dict(row)
                c["source"] = self.get_source(c["source_id"])
                citations.append(c)
            return citations

        for citation in self._citations.values():
            if (
                citation["used_in_type"] == entity_type
                and citation["used_in_id"] == entity_id
            ):
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
        if self.db is not None:
            from app.db import models

            row = self.db.get(models.Citation, citation_id)
            if not row:
                raise ValueError(f"Citation {citation_id} not found")
            row.verification_status = status
            row.verified = status == "verified"
            if notes:
                row.verification_notes = notes
            self.db.commit()
            return self._citation_row_to_dict(row)

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
            results.append(
                {
                    "claim_index": i,
                    "claim_text": result.claim_text[:100],
                    "is_valid": result.is_valid,
                    "citation_found": result.citation_found,
                    "source_verified": result.source_verified,
                    "snippet_matches": result.snippet_matches,
                    "issues": result.issues,
                }
            )

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
    """Back-compat boolean gate: are citations structurally present?"""

    claims = output.get("claims", [])

    for claim in claims:
        citations = claim.get("citations", [])
        if not citations:
            return False

        for cit in citations:
            if not cit.get("source_id") or not cit.get("snippet_hash"):
                return False

    return True


@dataclass
class CitationGateResult:
    """Result of the pre-send citation gate.

    ``blocking`` means the output MUST NOT be persisted / sent to a
    downstream party (filing, offer, binder).  The list of issues mirrors
    the Audit-UI surface so counsel can see why.
    """

    passed: bool
    blocking: bool
    claims_total: int
    claims_with_citations: int
    missing_citation_indices: list[int] = field(default_factory=list)
    invalid_citation_indices: list[int] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "blocking": self.blocking,
            "claims_total": self.claims_total,
            "claims_with_citations": self.claims_with_citations,
            "missing_citation_indices": self.missing_citation_indices,
            "invalid_citation_indices": self.invalid_citation_indices,
            "issues": self.issues,
        }


def enforce_citation_gate(
    output: dict[str, Any],
    *,
    authority_required: bool = True,
) -> CitationGateResult:
    """Strict citation gate for legal outputs.

    Unlike :func:`require_citations` which only returns a bool, this returns
    a structured result that routes / QA can persist and show in the UI.

    A claim is considered valid only when it carries at least one citation
    with both ``source_id`` and ``snippet_hash``.  When
    ``authority_required`` is true, citations must additionally include an
    ``authority_level`` (statute / case / regulation / treatise).
    """

    claims = output.get("claims", []) or []
    missing: list[int] = []
    invalid: list[int] = []
    issues: list[str] = []
    with_citations = 0

    for idx, claim in enumerate(claims):
        cits = claim.get("citations") or []
        if not cits:
            missing.append(idx)
            issues.append(f"claim[{idx}]: no citation provided")
            continue
        bad = False
        for cit in cits:
            if not cit.get("source_id") or not cit.get("snippet_hash"):
                bad = True
                issues.append(
                    f"claim[{idx}]: citation missing source_id/snippet_hash"
                )
                break
            if authority_required and not cit.get("authority_level"):
                bad = True
                issues.append(f"claim[{idx}]: citation missing authority_level")
                break
        if bad:
            invalid.append(idx)
        else:
            with_citations += 1

    passed = not missing and not invalid and bool(claims)
    blocking = bool(missing or invalid)
    return CitationGateResult(
        passed=passed,
        blocking=blocking,
        claims_total=len(claims),
        claims_with_citations=with_citations,
        missing_citation_indices=missing,
        invalid_citation_indices=invalid,
        issues=issues,
    )


def populate_qa_citation_counters(
    qa_report: Any,
    gate_or_check: Any,
) -> None:
    """Fill ``QAReport.citations_validated`` / ``citations_invalid`` from
    either a :class:`CitationGateResult` or a ``check_ai_output`` dict.

    Both :class:`QACheckService` and the binder/filing flows should invoke
    this so Document QA surfaces citation coverage consistently.
    """

    if gate_or_check is None or qa_report is None:
        return

    if isinstance(gate_or_check, CitationGateResult):
        qa_report.citations_validated = gate_or_check.claims_with_citations
        qa_report.citations_invalid = (
            len(gate_or_check.missing_citation_indices)
            + len(gate_or_check.invalid_citation_indices)
        )
        qa_report.citation_issues = [
            {"message": msg} for msg in gate_or_check.issues
        ]
        return

    if isinstance(gate_or_check, dict):
        valid = int(gate_or_check.get("claims_valid", 0))
        total = int(gate_or_check.get("claims_checked", 0))
        qa_report.citations_validated = valid
        qa_report.citations_invalid = max(total - valid, 0)
        results = gate_or_check.get("results") or []
        qa_report.citation_issues = [
            {"claim_index": r.get("claim_index"), "issues": r.get("issues", [])}
            for r in results
            if not r.get("is_valid", True)
        ]


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
