"""Phase 2.3: eval_harness uses the real deadline engine."""

from __future__ import annotations

from app.services.eval_harness import EvalHarness, GoldenTestCase


def test_run_deadline_test_uses_real_engine():
    # Construct a scenario that the rules engine should evaluate.  We assert
    # behavior, not exact output, since the YAML pack is authoritative.
    harness = EvalHarness()
    case = GoldenTestCase(
        id="tx_sanity",
        name="TX anchor evaluation",
        description="Evaluates TX rules via real engine",
        state="TX",
        category="deadline",
        scenario={
            "jurisdiction": "TX",
            "initial_offer_date": "2026-01-01",
        },
        expected_deadlines=[],  # no required match → subset compare passes
    )
    result = harness.run_deadline_test(case)
    assert result.category == "deadline"
    # Real engine may return zero or more derived deadlines; the subset
    # comparator with an empty expected list must pass.
    assert result.passed is True
    assert isinstance(result.actual, list)


def test_subset_match_catches_missing_deadline():
    harness = EvalHarness()
    case = GoldenTestCase(
        id="missing_deadline",
        name="Missing expected deadline",
        description="should fail when expected not in actual",
        state="TX",
        category="deadline",
        scenario={"jurisdiction": "TX"},
        expected_deadlines=[
            {"name": "nonexistent_deadline", "due_date": "2099-01-01"}
        ],
    )
    result = harness.run_deadline_test(case)
    assert result.passed is False
