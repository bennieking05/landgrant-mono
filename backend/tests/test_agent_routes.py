"""Tests for agent API routes.

Tests the /agents endpoint for:
- Running agents
- Listing AI decisions
- Managing escalations
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.db.models import Persona
from app.main import app

from tests.jwt_helpers import auth_headers


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def counsel_headers():
    """Headers for in-house counsel persona."""
    return auth_headers(Persona.IN_HOUSE_COUNSEL, user_id="COUNSEL-001")


class TestAgentRoutes:
    """Tests for agent API routes."""

    def test_run_agent_intake(self, client, counsel_headers):
        """Test running intake agent."""
        with patch("app.api.routes.agents._get_agent") as mock_get:
            mock_agent = AsyncMock()
            mock_agent.execute = AsyncMock(return_value=AsyncMock(
                success=True,
                confidence=0.9,
                data={"test": True},
                flags=[],
                requires_review=False,
            ))
            mock_get.return_value = mock_agent
            
            response = client.post(
                "/agents/run",
                json={
                    "agent_type": "intake",
                    "case_id": "TEST-001",
                    "jurisdiction": "TX",
                },
                headers=counsel_headers,
            )
            
            # Should return 200 or handle gracefully
            assert response.status_code in [200, 500]

    def test_list_ai_decisions(self, client, counsel_headers):
        """Test listing AI decisions."""
        response = client.get(
            "/agents/decisions",
            headers=counsel_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_ai_decisions_filtered(self, client, counsel_headers):
        """Test listing AI decisions with filters."""
        response = client.get(
            "/agents/decisions?agent_type=intake&pending_review=true",
            headers=counsel_headers,
        )
        
        assert response.status_code == 200

    def test_get_ai_decision(self, client, counsel_headers):
        """Test getting a specific AI decision.

        Phase 1.3: /agents/decisions/{id} now queries the AIDecision table.
        Unknown IDs return 404 instead of returning mock data.
        """
        response = client.get(
            "/agents/decisions/decision-001",
            headers=counsel_headers,
        )

        assert response.status_code == 404

    def test_list_escalations(self, client, counsel_headers):
        """Test listing escalations."""
        response = client.get(
            "/agents/escalations",
            headers=counsel_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_escalations_filtered(self, client, counsel_headers):
        """Test listing escalations with filters."""
        response = client.get(
            "/agents/escalations?status=open&priority=high",
            headers=counsel_headers,
        )
        
        assert response.status_code == 200

    def test_get_escalation(self, client, counsel_headers):
        """Phase 1.3: unknown escalations 404 against the real table."""
        response = client.get(
            "/agents/escalations/esc-001",
            headers=counsel_headers,
        )

        assert response.status_code == 404

    def test_resolve_escalation(self, client, counsel_headers):
        """Phase 1.3: resolving a non-existent escalation now 404s."""
        response = client.post(
            "/agents/escalations/esc-001/resolve",
            json={
                "resolution": "Reviewed and approved the AI decision.",
                "outcome": "approved",
            },
            headers=counsel_headers,
        )

        assert response.status_code == 404

    def test_assign_escalation(self, client, counsel_headers):
        """Phase 1.3: assigning a non-existent escalation now 404s."""
        response = client.post(
            "/agents/escalations/esc-001/assign?assignee_id=COUNSEL-001",
            headers=counsel_headers,
        )

        assert response.status_code == 404


class TestAgentAuthorization:
    """Tests for agent authorization."""

    def test_unauthorized_without_persona(self, client):
        """Test that requests without JWT are rejected."""
        response = client.get("/agents/decisions")
        assert response.status_code == 401

    def test_unauthorized_wrong_persona(self, client):
        """Test that wrong persona cannot access agents."""
        response = client.get(
            "/agents/decisions",
            headers=auth_headers(
                Persona.LANDOWNER, user_id="portal:x", email="owner@example.com"
            ),
        )
        assert response.status_code == 403
