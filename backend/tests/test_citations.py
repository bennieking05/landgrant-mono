"""Tests for Citation and Provenance Service."""

import pytest

from app.services.citations import (
    CitationService,
    ClaimChecker,
    SourceInput,
    CitationInput,
    ClaimWithCitation,
    require_citations,
)


@pytest.fixture
def citation_service(tmp_path):
    """Create a citation service with temp storage."""
    return CitationService(storage_path=tmp_path)


@pytest.fixture
def claim_checker(citation_service):
    """Create a claim checker."""
    return ClaimChecker(citation_service)


def test_create_source(citation_service):
    """Test creating a source."""
    source = citation_service.create_source(SourceInput(
        title="Texas Property Code Chapter 21",
        jurisdiction="TX",
        authority_level="statute",
        citation_string="Tex. Prop. Code Ch. 21",
        raw_text="Section 21.0112. Landowner's Bill of Rights...",
    ))
    
    assert source["id"].startswith("src_")
    assert source["title"] == "Texas Property Code Chapter 21"
    assert source["jurisdiction"] == "TX"
    assert source["authority_level"] == "statute"
    assert source["content_hash"]  # Should have hash
    assert source["raw_text_snippet"]  # Should store snippet


def test_get_source(citation_service):
    """Test retrieving a source."""
    created = citation_service.create_source(SourceInput(
        title="Test Statute",
        jurisdiction="TX",
        authority_level="statute",
    ))
    
    retrieved = citation_service.get_source(created["id"])
    
    assert retrieved is not None
    assert retrieved["id"] == created["id"]
    assert retrieved["title"] == "Test Statute"


def test_search_sources(citation_service):
    """Test searching sources."""
    # Create multiple sources
    citation_service.create_source(SourceInput(
        title="Texas Property Code",
        jurisdiction="TX",
        authority_level="statute",
    ))
    citation_service.create_source(SourceInput(
        title="California Code of Civil Procedure",
        jurisdiction="CA",
        authority_level="statute",
    ))
    
    # Search by jurisdiction
    tx_sources = citation_service.search_sources(jurisdiction="TX")
    assert len(tx_sources) == 1
    assert tx_sources[0]["jurisdiction"] == "TX"
    
    # Search by query
    ca_sources = citation_service.search_sources(query="California")
    assert len(ca_sources) == 1


def test_verify_source(citation_service):
    """Test verifying a source."""
    source = citation_service.create_source(SourceInput(
        title="Test Statute",
        jurisdiction="TX",
        authority_level="statute",
    ))
    
    assert not source["verified"]
    
    verified = citation_service.verify_source(
        source_id=source["id"],
        user_id="test-user",
        notes="Verified against official publication",
    )
    
    assert verified["verified"]
    assert verified["verified_by"] == "test-user"


def test_create_citation(citation_service):
    """Test creating a citation."""
    # First create a source
    source = citation_service.create_source(SourceInput(
        title="Test Statute",
        jurisdiction="TX",
        authority_level="statute",
        raw_text="The owner shall receive adequate compensation.",
    ))
    
    # Create citation
    citation = citation_service.create_citation(CitationInput(
        source_id=source["id"],
        used_in_type="ai_decision",
        used_in_id="decision-123",
        snippet="adequate compensation",
        span_start=27,
        span_end=49,
        section="§21.042",
    ))
    
    assert citation["id"].startswith("cit_")
    assert citation["source_id"] == source["id"]
    assert citation["snippet"] == "adequate compensation"
    assert citation["snippet_hash"]  # Should have hash


def test_get_citations_for_entity(citation_service):
    """Test getting citations for an entity."""
    source = citation_service.create_source(SourceInput(
        title="Test Statute",
        jurisdiction="TX",
        authority_level="statute",
    ))
    
    citation_service.create_citation(CitationInput(
        source_id=source["id"],
        used_in_type="ai_decision",
        used_in_id="decision-123",
        snippet="test snippet",
    ))
    
    citations = citation_service.get_citations_for_entity(
        entity_type="ai_decision",
        entity_id="decision-123",
    )
    
    assert len(citations) == 1
    assert citations[0]["source"] is not None


def test_claim_checker_valid(citation_service, claim_checker):
    """Test claim checking with valid citations."""
    source = citation_service.create_source(SourceInput(
        title="Test Statute",
        jurisdiction="TX",
        authority_level="statute",
        raw_text="The owner shall receive adequate compensation for the taking.",
    ))
    citation_service.verify_source(source["id"], "test-user")
    
    claim = ClaimWithCitation(
        text="The owner is entitled to adequate compensation.",
        citations=[{
            "source_id": source["id"],
            "snippet": "adequate compensation",
            "snippet_hash": "dummy",  # Would be computed
        }],
        confidence=0.95,
    )
    
    result = claim_checker.check_claim(claim)
    
    assert result.citation_found
    assert result.source_verified


def test_claim_checker_no_citations(claim_checker):
    """Test claim checking with no citations."""
    claim = ClaimWithCitation(
        text="The owner is entitled to compensation.",
        citations=[],
        confidence=0.95,
    )
    
    result = claim_checker.check_claim(claim)
    
    assert not result.is_valid
    assert not result.citation_found
    assert "No citations provided" in result.issues


def test_claim_checker_missing_source(claim_checker):
    """Test claim checking with non-existent source."""
    claim = ClaimWithCitation(
        text="Test claim",
        citations=[{
            "source_id": "nonexistent",
            "snippet": "test",
        }],
        confidence=0.95,
    )
    
    result = claim_checker.check_claim(claim)
    
    assert not result.is_valid
    assert "not found" in " ".join(result.issues)


def test_check_ai_output(citation_service, claim_checker):
    """Test checking a full AI output."""
    source = citation_service.create_source(SourceInput(
        title="Test Statute",
        jurisdiction="TX",
        authority_level="statute",
    ))
    citation_service.verify_source(source["id"], "test-user")
    
    output = {
        "claims": [
            {
                "text": "Claim 1",
                "citations": [{"source_id": source["id"], "snippet_hash": "hash1"}],
                "confidence": 0.9,
            },
            {
                "text": "Claim 2 without citations",
                "citations": [],
                "confidence": 0.8,
            },
        ]
    }
    
    result = claim_checker.check_ai_output(output)
    
    assert not result["all_valid"]  # One claim has no citations
    assert result["claims_checked"] == 2
    assert len(result["missing_citations"]) == 1
    assert 1 in result["missing_citations"]


def test_require_citations():
    """Test citation requirement check."""
    valid_output = {
        "claims": [
            {
                "text": "Test claim",
                "citations": [{"source_id": "src1", "snippet_hash": "hash1"}],
            }
        ]
    }
    
    invalid_output = {
        "claims": [
            {
                "text": "Test claim",
                "citations": [],
            }
        ]
    }
    
    assert require_citations(valid_output)
    assert not require_citations(invalid_output)
