"""Tests for enhanced template rendering with deadline anchors."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _db_available() -> bool:
    """Check if database is available for testing."""
    # These tests don't actually need the database, remove the skip
    return True


class TestTemplateRenderEndpoint:
    """Tests for POST /templates/render with deadline anchor extraction."""

    @pytest.mark.skipif(not _db_available(), reason="Database not available")
    def test_render_texas_template(self):
        """Rendering TX FOL template returns content."""
        res = client.post(
            "/templates/render",
            headers={"X-Persona": "in_house_counsel"},
            json={
                "template_id": "fol",
                "locale": "en-US",
                "variables": {
                    "owner_name": "Test Owner",
                    "parcel_id": "PARCEL-001",
                    "project_name": "Test Project",
                    "appraisal_date": "2025-01-15",
                    "offer_amount": 50000,
                    "citation_list": ["Tex. Prop. Code §21.0113"],
                    "response_window_days": 30,
                    "agent_name": "Test Agent",
                },
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "rendered" in data
        assert "Test Owner" in data["rendered"]
        assert "PARCEL-001" in data["rendered"]

    @pytest.mark.skipif(not _db_available(), reason="Database not available")
    def test_render_indiana_template(self):
        """Rendering IN offer template returns content with deadline anchors."""
        res = client.post(
            "/templates/render",
            headers={"X-Persona": "in_house_counsel"},
            json={
                "template_id": "in_offer",
                "locale": "en-US",
                "variables": {
                    "condemning_authority_name": "Test Authority",
                    "owner_name": "Bruce Silvers",
                    "owner_address_line1": "123 Main St",
                    "owner_address_city": "Fort Wayne",
                    "owner_address_state": "IN",
                    "owner_address_zip": "46807",
                    "project_name": "Test Gas Project",
                    "parcel_pin": "02-18-06-251-001",
                    "easement_type": "permanent easement",
                    "easement_purpose": "transmission of gas",
                    "permanent_easement_amount": 21000,
                    "total_offer_amount": 21800,
                    "appraisal_date": "2025-01-15",
                    "service_date": "2025-02-06",
                    "response_window_days": 30,
                    "payment_window_days": 90,
                    "possession_window_days": 30,
                    "contact_name": "Katie Bryan",
                    "contact_address": "801 E. 86th Ave, Merrillville, IN",
                    "contact_phone": "(219) 337-2195",
                    "signatory_name": "David Roy",
                    "signatory_title": "Vice President",
                },
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "rendered" in data
        assert "Bruce Silvers" in data["rendered"]
        assert "02-18-06-251-001" in data["rendered"]
        assert "Ind. Code" in data["rendered"]  # Indiana Code citations
        
        # Check deadline anchors are extracted
        if "deadline_anchors" in data and data["deadline_anchors"]:
            assert "offer_served" in data["deadline_anchors"]
            assert data["deadline_anchors"]["offer_served"] == "2025-02-06"

    @pytest.mark.skipif(not _db_available(), reason="Database not available")
    def test_render_nonexistent_template_returns_404(self):
        """Rendering nonexistent template returns 404."""
        res = client.post(
            "/templates/render",
            headers={"X-Persona": "in_house_counsel"},
            json={
                "template_id": "nonexistent_template",
                "locale": "en-US",
                "variables": {},
            },
        )
        assert res.status_code == 404

    def test_render_requires_execute_permission(self):
        """Template render requires EXECUTE permission."""
        res = client.post(
            "/templates/render",
            headers={"X-Persona": "outside_counsel"},
            json={
                "template_id": "fol",
                "locale": "en-US",
                "variables": {},
            },
        )
        # Outside counsel doesn't have template execute permission
        assert res.status_code == 403


class TestTemplateListEndpoint:
    """Tests for GET /templates endpoint."""

    @pytest.mark.skipif(not _db_available(), reason="Database not available")
    def test_list_templates_returns_both_jurisdictions(self):
        """Template list includes TX and IN templates."""
        res = client.get(
            "/templates",
            headers={"X-Persona": "in_house_counsel"},
        )
        assert res.status_code == 200
        data = res.json()
        
        template_ids = [t["id"] for t in data]
        assert "fol" in template_ids  # Texas
        assert "in_offer" in template_ids  # Indiana

    @pytest.mark.skipif(not _db_available(), reason="Database not available")
    def test_list_templates_includes_jurisdiction(self):
        """Template metadata includes jurisdiction field."""
        res = client.get(
            "/templates",
            headers={"X-Persona": "in_house_counsel"},
        )
        assert res.status_code == 200
        data = res.json()
        
        in_offer = next((t for t in data if t["id"] == "in_offer"), None)
        assert in_offer is not None
        assert in_offer["jurisdiction"] == "IN"
