"""Tests for deadline derivation service and API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.deadline_rules import derive_deadlines, load_jurisdiction_rules


client = TestClient(app)


class TestDeadlineRulesService:
    """Tests for the deadline_rules service module."""

    def test_load_indiana_rules(self):
        """IN rules file should load and have expected structure."""
        rules = load_jurisdiction_rules("IN")
        assert rules is not None
        assert rules["jurisdiction"] == "IN"
        assert "deadline_chains" in rules
        assert len(rules["deadline_chains"]) > 0

    def test_load_texas_rules(self):
        """TX rules file should load and have expected structure."""
        rules = load_jurisdiction_rules("TX")
        assert rules is not None
        assert rules["jurisdiction"] == "TX"
        assert "triggers" in rules

    def test_load_nonexistent_jurisdiction_returns_none(self):
        """Loading unknown jurisdiction returns None."""
        rules = load_jurisdiction_rules("ZZ")
        assert rules is None

    def test_derive_indiana_deadlines_from_offer_served(self):
        """Deriving deadlines from offer_served should produce expected deadlines."""
        result = derive_deadlines(
            jurisdiction="IN",
            anchor_events={"offer_served": "2025-02-06"},
        )
        
        assert result.jurisdiction == "IN"
        assert len(result.errors) == 0
        assert len(result.deadlines) >= 2
        
        # Check for expected deadlines
        deadline_ids = [d.id for d in result.deadlines]
        assert "earliest_complaint_filing" in deadline_ids
        assert "owner_response_window" in deadline_ids
        
        # Verify offset calculation
        for d in result.deadlines:
            if d.id == "earliest_complaint_filing":
                assert str(d.due_date) == "2025-03-08"  # +30 days from Feb 6
            elif d.id == "owner_response_window":
                assert str(d.due_date) == "2025-03-08"  # +30 days

    def test_derive_indiana_deadlines_multiple_anchors(self):
        """Multiple anchor events should produce full deadline chain."""
        result = derive_deadlines(
            jurisdiction="IN",
            anchor_events={
                "offer_served": "2025-02-06",
                "notice_served": "2025-03-20",
                "appraisers_report_mailed": "2025-05-01",
            },
        )
        
        assert len(result.errors) == 0
        assert len(result.deadlines) >= 4  # At least deadlines from 3 chains
        
        deadline_ids = [d.id for d in result.deadlines]
        assert "defendant_objection_deadline" in deadline_ids
        assert "exceptions_deadline" in deadline_ids

    def test_derive_with_empty_anchors_returns_no_deadlines(self):
        """Empty anchor events should return no deadlines."""
        result = derive_deadlines(
            jurisdiction="IN",
            anchor_events={},
        )
        
        assert len(result.deadlines) == 0

    def test_derive_with_invalid_date_adds_error(self):
        """Invalid date format should add error."""
        result = derive_deadlines(
            jurisdiction="IN",
            anchor_events={"offer_served": "not-a-date"},
        )
        
        assert len(result.errors) > 0


class TestDeadlinesDeriveEndpoint:
    """Tests for POST /deadlines/derive API endpoint."""

    def test_derive_endpoint_requires_auth(self):
        """Derive endpoint requires valid persona."""
        res = client.post(
            "/deadlines/derive",
            headers={"X-Persona": "invalid"},
            json={
                "project_id": "PRJ-001",
                "jurisdiction": "IN",
                "anchor_events": {"offer_served": "2025-02-06"},
            },
        )
        assert res.status_code == 401

    def test_derive_endpoint_with_counsel_persona(self):
        """In-house counsel can call derive endpoint."""
        res = client.post(
            "/deadlines/derive",
            headers={"X-Persona": "in_house_counsel"},
            json={
                "project_id": "PRJ-001",
                "jurisdiction": "IN",
                "anchor_events": {"offer_served": "2025-02-06"},
                "persist": False,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["jurisdiction"] == "IN"
        assert data["derived_count"] >= 2
        assert len(data["deadlines"]) >= 2

    def test_derive_endpoint_with_unknown_jurisdiction(self):
        """Unknown jurisdiction should return errors."""
        res = client.post(
            "/deadlines/derive",
            headers={"X-Persona": "in_house_counsel"},
            json={
                "project_id": "PRJ-001",
                "jurisdiction": "ZZ",
                "anchor_events": {"offer_served": "2025-02-06"},
                "persist": False,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["errors"]) > 0
        assert data["derived_count"] == 0

    def test_derive_endpoint_landowner_forbidden(self):
        """Landowner persona cannot call derive endpoint."""
        res = client.post(
            "/deadlines/derive",
            headers={"X-Persona": "landowner"},
            json={
                "project_id": "PRJ-001",
                "jurisdiction": "IN",
                "anchor_events": {"offer_served": "2025-02-06"},
            },
        )
        assert res.status_code == 403
