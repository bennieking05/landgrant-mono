"""Phase 2.1: agent stubs are replaced with real logic."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.agents.docgen_agent import DocGenAgent
from app.agents.filing_agent import FilingAgent, MockFilingAdapter
from app.agents.valuation_agent import ValuationAgent


@pytest.fixture()
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def test_render_to_pdf_produces_file(tmp_path):
    agent = DocGenAgent()
    result = asyncio.run(
        agent.render_to_pdf(
            document_id="doc-abc",
            content="Hello World\nPetition Body",
            storage_dir=str(tmp_path),
        )
    )
    path = Path(result["storage_path"])
    assert path.exists()
    assert path.stat().st_size > 0
    assert result["renderer"] in {"weasyprint", "reportlab", "text_fallback"}


def test_render_to_docx_produces_file(tmp_path):
    agent = DocGenAgent()
    result = asyncio.run(
        agent.render_to_docx(
            document_id="doc-xyz",
            content="party names\nlegal description",
            storage_dir=str(tmp_path),
        )
    )
    path = Path(result["storage_path"])
    assert path.exists()
    assert path.stat().st_size > 0


def test_filing_adapter_registry_falls_back_to_mock():
    agent = FilingAgent()
    adapter = agent._get_filing_adapter("TX-UNKNOWN-COURT")
    assert isinstance(adapter, MockFilingAdapter)


def test_filing_adapter_registry_uses_registered_factory():
    class FakeAdapter:
        def __init__(self, court_id):
            self.court_id = court_id

    FilingAgent.register_filing_adapter("TX-FAKE", lambda cid: FakeAdapter(cid))
    try:
        agent = FilingAgent()
        adapter = agent._get_filing_adapter("TX-FAKE-101")
        assert isinstance(adapter, FakeAdapter)
        assert adapter.court_id == "TX-FAKE-101"
    finally:
        FilingAgent._adapter_registry.pop("TX-FAKE", None)


def test_validate_for_court_flags_missing_fields():
    agent = FilingAgent()
    result = asyncio.run(
        agent._validate_for_court({"id": "", "doc_type": ""}, court_id="")
    )
    assert result["valid"] is False
    assert any("document.id missing" in i for i in result["issues"])
    assert any("document.doc_type missing" in i for i in result["issues"])
    assert any("court_id missing" in i for i in result["issues"])


def test_validate_for_court_accepts_well_formed_doc():
    agent = FilingAgent()
    result = asyncio.run(
        agent._validate_for_court(
            {"id": "doc-1", "doc_type": "petition"}, court_id="TX-COUNTY-1"
        )
    )
    assert result["valid"] is True
    assert result["issues"] == []


def test_calculate_severance_defaults_to_base():
    agent = ValuationAgent()
    severance = asyncio.run(
        agent._calculate_severance(
            {"appraisal_value": 1_000_000, "taking_percent": 20}
        )
    )
    # 20% taken * $1M = $200K; base severance 15% → $30K.
    assert 29_000 <= severance <= 31_000


def test_calculate_severance_adds_access_and_utility_penalties():
    agent = ValuationAgent()
    severance = asyncio.run(
        agent._calculate_severance(
            {
                "appraisal_value": 1_000_000,
                "taking_percent": 20,
                "access_impaired": True,
                "utility_corridor": True,
                "irregular_remainder": True,
            }
        )
    )
    # With all penalties: 0.15*200K + 0.05*1M + 0.10*200K + 0.05*200K
    # = 30K + 50K + 20K + 10K = 110K.
    assert 105_000 <= severance <= 115_000


def test_calculate_severance_caps_at_half_of_before_value():
    agent = ValuationAgent()
    severance = asyncio.run(
        agent._calculate_severance(
            {
                "appraisal_value": 100_000,
                "taking_percent": 95,
                "access_impaired": True,
                "utility_corridor": True,
                "irregular_remainder": True,
            }
        )
    )
    assert severance <= 50_000
