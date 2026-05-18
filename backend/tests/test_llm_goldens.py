"""LLM behavioral goldens.

Gated behind ``RUN_LLM_GOLDENS=1`` so normal CI doesn't burn tokens.  When
disabled we still validate that the runner returns the ``skipped`` marker
so the wiring itself is covered.
"""

from __future__ import annotations

import asyncio
import os

import pytest

from app.services import llm_golden_suite


def test_suite_is_skipped_by_default(monkeypatch):
    monkeypatch.delenv("RUN_LLM_GOLDENS", raising=False)
    result = asyncio.run(llm_golden_suite.run_suite())
    assert result["status"] == "skipped"


def test_llm_goldens_enabled_reads_env(monkeypatch):
    monkeypatch.setenv("RUN_LLM_GOLDENS", "1")
    assert llm_golden_suite.llm_goldens_enabled() is True
    monkeypatch.delenv("RUN_LLM_GOLDENS", raising=False)
    assert llm_golden_suite.llm_goldens_enabled() is False


@pytest.mark.skipif(
    not os.getenv("RUN_LLM_GOLDENS"), reason="RUN_LLM_GOLDENS not set"
)
def test_suite_runs_live_when_enabled():
    # Only executed in the nightly / manual pipeline.
    result = asyncio.run(llm_golden_suite.run_suite())
    assert result["status"] == "ran"
    assert result["total"] >= 1
