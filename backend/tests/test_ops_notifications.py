"""Tests for operations and notifications endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _db_available() -> bool:
    """Check if database is available for testing."""
    try:
        from sqlalchemy import text
        from app.db.session import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


class TestOpsRoutePlanEndpoint:
    """Tests for GET /ops/routes/plan endpoint."""

    @pytest.mark.skipif(not _db_available(), reason="Database not available")
    def test_route_plan_returns_ordered_parcels(self):
        """Route plan endpoint returns parcels ordered by risk/deadline."""
        res = client.get(
            "/ops/routes/plan?project_id=PRJ-001",
            headers={"X-Persona": "land_agent"},
        )
        assert res.status_code == 200
        data = res.json()
        
        assert data["project_id"] == "PRJ-001"
        assert "parcel_ids" in data
        assert isinstance(data["parcel_ids"], list)
        assert "csv" in data

    @pytest.mark.skipif(not _db_available(), reason="Database not available")
    def test_route_plan_csv_format(self):
        """Route plan CSV has expected format."""
        res = client.get(
            "/ops/routes/plan?project_id=PRJ-001",
            headers={"X-Persona": "land_agent"},
        )
        assert res.status_code == 200
        data = res.json()
        
        csv_lines = data["csv"].strip().split("\n")
        assert csv_lines[0] == "stop,parcel_id"  # Header

    def test_route_plan_requires_land_agent_or_higher(self):
        """Route plan requires appropriate persona."""
        res = client.get(
            "/ops/routes/plan?project_id=PRJ-001",
            headers={"X-Persona": "landowner"},
        )
        assert res.status_code == 403

    @pytest.mark.skipif(not _db_available(), reason="Database not available")
    def test_route_plan_with_counsel_persona(self):
        """In-house counsel can access route plan."""
        res = client.get(
            "/ops/routes/plan?project_id=PRJ-001",
            headers={"X-Persona": "in_house_counsel"},
        )
        assert res.status_code == 200


class TestNotificationsPreviewEndpoint:
    """Tests for POST /notifications/preview endpoint."""

    @pytest.mark.skip(reason="Requires full user/audit setup - integration test")
    def test_notification_preview_returns_body(self):
        """Notification preview returns rendered body."""
        res = client.post(
            "/notifications/preview",
            headers={"X-Persona": "in_house_counsel"},
            json={
                "template_id": "portal_invite",
                "channel": "email",
                "to": "owner@example.com",
                "project_id": "PRJ-001",
                "parcel_id": "PARCEL-001",
                "variables": {},
            },
        )
        assert res.status_code == 200
        data = res.json()
        
        assert "body" in data
        assert "channel" in data
        assert data["channel"] == "email"
        assert "to" in data
        assert data["to"] == "owner@example.com"

    @pytest.mark.skip(reason="Requires full user/audit setup - integration test")
    def test_notification_preview_sms_channel(self):
        """Notification preview works for SMS channel."""
        res = client.post(
            "/notifications/preview",
            headers={"X-Persona": "land_agent"},
            json={
                "template_id": "deadline_reminder",
                "channel": "sms",
                "to": "+15551234567",
                "project_id": "PRJ-001",
                "parcel_id": "PARCEL-001",
                "variables": {},
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["channel"] == "sms"

    def test_notification_preview_requires_write_permission(self):
        """Notification preview requires communication write permission."""
        res = client.post(
            "/notifications/preview",
            headers={"X-Persona": "landowner"},
            json={
                "template_id": "portal_invite",
                "channel": "email",
                "to": "owner@example.com",
                "project_id": "PRJ-001",
                "parcel_id": "PARCEL-001",
            },
        )
        assert res.status_code == 403


class TestIntegrationsDocketWebhook:
    """Tests for POST /integrations/dockets webhook endpoint."""

    def test_docket_webhook_accepts_payload(self):
        """Docket webhook accepts and echoes payload."""
        payload = {
            "event": "status_change",
            "case_id": "CASE-001",
            "new_status": "filed",
        }
        res = client.post(
            "/integrations/dockets",
            json=payload,
        )
        assert res.status_code == 200
        data = res.json()
        
        assert data["received"] is True
        assert data["payload"] == payload

    def test_docket_webhook_detects_signature_header(self):
        """Docket webhook detects presence of signature header."""
        res = client.post(
            "/integrations/dockets",
            headers={"X-Lob-Signature": "test-signature"},
            json={"event": "test"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["signature_present"] is True

    def test_docket_webhook_without_signature(self):
        """Docket webhook works without signature header."""
        res = client.post(
            "/integrations/dockets",
            json={"event": "test"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["signature_present"] is False
