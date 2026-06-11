"""Golden statutory deadline expectations for Indiana (contract Milestone 1)."""

from __future__ import annotations

from datetime import date

from app.services.deadline_rules import derive_deadlines, validate_anchor_chronology


def test_in_golden_offer_served_2026_06_01():
    """Anchor offer_served 2026-06-01 → IC 32-24-1-5 30-day windows land on 2026-07-01."""

    result = derive_deadlines(
        jurisdiction="IN",
        anchor_events={"offer_served": "2026-06-01"},
    )
    assert result.errors == []
    by_id = {d.id: d for d in result.deadlines}
    assert by_id["earliest_complaint_filing"].due_date == date(2026, 7, 1)
    assert by_id["owner_response_window"].due_date == date(2026, 7, 1)


def test_in_settlement_sequence_relative_anchor():
    """Trial date drives settlement offer; response chains off synthetic served date."""

    result = derive_deadlines(
        jurisdiction="IN",
        anchor_events={"trial_date_set": "2026-09-15"},
    )
    assert result.errors == []
    by_id = {d.id: d for d in result.deadlines}
    assert by_id["settlement_offer_deadline"].due_date == date(2026, 8, 1)
    assert by_id["settlement_response_deadline"].due_date == date(2026, 8, 6)


def test_validate_complaint_before_minimum_after_offer():
    errs = validate_anchor_chronology(
        "IN",
        {"offer_served": "2026-06-01", "complaint_filed": "2026-06-15"},
    )
    assert any("30-day minimum" in e for e in errs)
