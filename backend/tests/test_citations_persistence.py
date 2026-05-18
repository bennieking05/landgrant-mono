"""Phase 1.5: persist Source/Citation; citation gate; QA counter population."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models  # noqa: F401
from app.db.session import Base
from app.services.citations import (
    CitationInput,
    CitationService,
    SourceInput,
    enforce_citation_gate,
    populate_qa_citation_counters,
)
from app.services.qa_checks import QACheckService


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_source_and_citation_persist_across_service_instances(db_session):
    svc = CitationService(db=db_session)
    source = svc.create_source(
        SourceInput(
            title="TX Property Code Ch. 21",
            jurisdiction="TX",
            authority_level="statute",
            citation_string="Tex. Prop. Code § 21.0113",
            raw_text="Condemnation statute text",
        )
    )
    citation = svc.create_citation(
        CitationInput(
            source_id=source["id"],
            used_in_type="ai_decision",
            used_in_id="dec_1",
            snippet="bona fide offer",
            section="§21.0113(a)",
        )
    )

    # New service instance, same DB → data is still there.
    svc2 = CitationService(db=db_session)
    reloaded = svc2.get_source(source["id"])
    assert reloaded is not None
    assert reloaded["title"] == "TX Property Code Ch. 21"

    cits = svc2.get_citations_for_entity("ai_decision", "dec_1")
    assert len(cits) == 1
    assert cits[0]["id"] == citation["id"]
    assert cits[0]["source"]["id"] == source["id"]


def test_citation_gate_blocks_missing_citations():
    ai_output = {
        "claims": [
            {"text": "A uses eminent domain.", "citations": []},
            {
                "text": "B requires a bona fide offer.",
                "citations": [
                    {
                        "source_id": "src_1",
                        "snippet_hash": "abc",
                        "authority_level": "statute",
                    }
                ],
            },
        ]
    }
    result = enforce_citation_gate(ai_output)
    assert result.passed is False
    assert result.blocking is True
    assert 0 in result.missing_citation_indices
    assert result.claims_with_citations == 1


def test_citation_gate_rejects_incomplete_citation():
    ai_output = {
        "claims": [
            {
                "text": "Statute requires offer.",
                "citations": [{"source_id": "src_1"}],  # missing snippet_hash
            }
        ]
    }
    result = enforce_citation_gate(ai_output)
    assert result.blocking is True
    assert 0 in result.invalid_citation_indices


def test_citation_gate_passes_when_all_claims_cited():
    ai_output = {
        "claims": [
            {
                "text": "TX requires bona fide offer.",
                "citations": [
                    {
                        "source_id": "src_1",
                        "snippet_hash": "abc",
                        "authority_level": "statute",
                    }
                ],
            }
        ]
    }
    result = enforce_citation_gate(ai_output)
    assert result.passed is True
    assert result.blocking is False
    assert result.claims_with_citations == 1


def test_qa_counters_populated_from_gate():
    svc = QACheckService()
    gate = enforce_citation_gate(
        {
            "claims": [
                {
                    "text": "ok",
                    "citations": [
                        {
                            "source_id": "s1",
                            "snippet_hash": "h",
                            "authority_level": "statute",
                        }
                    ],
                },
                {"text": "bad", "citations": []},
            ]
        }
    )
    report = svc.check_document(
        document_content="offer of $1,000,000; bona fide offer provided",
        document_id="doc_1",
        jurisdiction="TX",
        document_type="offer",
        context={"amounts": {"offer_amount": 1_000_000}},
        citation_gate=gate,
    )

    assert report.citations_validated == 1
    assert report.citations_invalid >= 1
    assert report.risk_level == "red"
    assert report.requires_counsel_review is True


def test_populate_qa_citation_counters_accepts_dict_result():
    svc = QACheckService()
    report = svc.check_document(
        document_content="",
        document_id="doc_2",
        jurisdiction="TX",
        document_type="offer",
    )
    populate_qa_citation_counters(
        report,
        {
            "claims_checked": 3,
            "claims_valid": 2,
            "results": [
                {"claim_index": 2, "is_valid": False, "issues": ["missing"]}
            ],
        },
    )
    assert report.citations_validated == 2
    assert report.citations_invalid == 1
    assert report.citation_issues[0]["claim_index"] == 2
