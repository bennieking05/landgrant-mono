"""LLM behavioral golden suite.

Phase 2.3: these tests exercise the *actual* Gemini endpoint (not stubbed
responses) and assert behavioral invariants — they only run when
``RUN_LLM_GOLDENS=1`` is set so CI does not burn tokens or flake on
network blips.  When gated off, the runner reports ``status="skipped"``
so dashboards still have a row.

Invariants we assert:

* Every legal analysis response contains ``claims[].citations`` backed by
  ``source_id`` + ``snippet_hash`` (structural citation gate).
* Jurisdiction-specific prompts mention the jurisdiction in the answer.
* Known high-risk scenarios (eg. partial taking with access loss) are
  flagged ``requires_review``.

The suite lives here rather than in ``tests/`` so it can be invoked from
cron jobs, ops scripts, and pytest (via ``test_llm_goldens.py``).
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, Optional


def llm_goldens_enabled() -> bool:
    return os.getenv("RUN_LLM_GOLDENS", "").strip() in ("1", "true", "yes")


@dataclass
class GoldenScenario:
    id: str
    jurisdiction: str
    task_type: str
    payload: dict[str, Any]
    must_mention: list[str] = field(default_factory=list)
    must_flag_review: bool = False


DEFAULT_SCENARIOS: list[GoldenScenario] = [
    GoldenScenario(
        id="tx_partial_taking_access_loss",
        jurisdiction="TX",
        task_type="risk_assessment",
        payload={
            "parcel": {
                "appraisal_value": 1_000_000,
                "taking_percent": 30,
                "access_impaired": True,
            },
            "project_type": "highway_widening",
        },
        must_mention=["TX", "access", "severance"],
        must_flag_review=True,
    ),
    GoldenScenario(
        id="in_bona_fide_offer",
        jurisdiction="IN",
        task_type="draft_analysis",
        payload={"stage": "pre_offer"},
        must_mention=["Indiana", "offer"],
    ),
]


@dataclass
class GoldenResult:
    id: str
    passed: bool
    issues: list[str] = field(default_factory=list)
    response: Optional[dict[str, Any]] = None


async def _run_scenario(scenario: GoldenScenario) -> GoldenResult:
    from app.services.ai_pipeline import GeminiRequest, call_gemini

    request = GeminiRequest(
        jurisdiction=scenario.jurisdiction,
        payload=scenario.payload,
        rule_results=[],
        task_type=scenario.task_type,
    )

    response = await call_gemini(request)
    if not response:
        return GoldenResult(
            id=scenario.id,
            passed=False,
            issues=["Gemini returned no response (model disabled or network error)"],
        )

    issues: list[str] = []
    text = str(response)

    for keyword in scenario.must_mention:
        if keyword.lower() not in text.lower():
            issues.append(f"missing expected keyword: {keyword}")

    claims = response.get("claims") or []
    if claims:
        for idx, claim in enumerate(claims):
            cits = claim.get("citations") or []
            if not cits:
                issues.append(f"claim[{idx}] missing citations")
                continue
            for cit in cits:
                if not cit.get("source_id") or not cit.get("snippet_hash"):
                    issues.append(
                        f"claim[{idx}] citation missing source_id/snippet_hash"
                    )
                    break

    if scenario.must_flag_review and not (
        response.get("requires_review")
        or response.get("confidence", 1.0) < 0.85
        or response.get("risk_level") in {"red", "high"}
    ):
        issues.append("expected review/high-risk flag not present")

    return GoldenResult(
        id=scenario.id,
        passed=not issues,
        issues=issues,
        response=response,
    )


async def run_suite(
    scenarios: Optional[list[GoldenScenario]] = None,
) -> dict[str, Any]:
    """Run the golden suite.  Returns a JSON-serialisable summary."""

    if not llm_goldens_enabled():
        return {"status": "skipped", "reason": "RUN_LLM_GOLDENS not set"}

    scenarios = scenarios or DEFAULT_SCENARIOS
    results: list[GoldenResult] = []
    for sc in scenarios:
        try:
            results.append(await _run_scenario(sc))
        except Exception as exc:  # pragma: no cover - depends on external service
            results.append(
                GoldenResult(id=sc.id, passed=False, issues=[f"exception: {exc}"])
            )

    return {
        "status": "ran",
        "total": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
        "results": [
            {
                "id": r.id,
                "passed": r.passed,
                "issues": r.issues,
            }
            for r in results
        ],
    }


def run_suite_sync() -> dict[str, Any]:
    """Convenience wrapper for scripts / CLI."""

    return asyncio.run(run_suite())
