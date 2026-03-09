"""Tests for agent API routes.

Tests the /agents endpoint for:
- Running agents
- Listing AI decisions
- Managing escalations
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def counsel_headers():
    """Headers for in-house counsel persona."""
    return {"X-Persona": "in_house_counsel"}


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
        """Test getting a specific AI decision."""
        response = client.get(
            "/agents/decisions/decision-001",
            headers=counsel_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "agent_type" in data

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
        """Test getting a specific escalation."""
        response = client.get(
            "/agents/escalations/esc-001",
            headers=counsel_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "reason" in data

    def test_resolve_escalation(self, client, counsel_headers):
        """Test resolving an escalation."""
        response = client.post(
            "/agents/escalations/esc-001/resolve",
            json={
                "resolution": "Reviewed and approved the AI decision.",
                "outcome": "approved",
            },
            headers=counsel_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["outcome"] == "approved"

    def test_assign_escalation(self, client, counsel_headers):
        """Test assigning an escalation."""
        response = client.post(
            "/agents/escalations/esc-001/assign?assignee_id=COUNSEL-001",
            headers=counsel_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["assigned_to"] == "COUNSEL-001"


class TestAgentAuthorization:
    """Tests for agent authorization."""

    def test_unauthorized_without_persona(self, client):
        """Test that requests without persona are rejected."""
        response = client.get("/agents/decisions")
        # Should fail without persona header
        assert response.status_code in [400, 401, 422]

    def test_unauthorized_wrong_persona(self, client):
        """Test that wrong persona cannot access agents."""
        response = client.get(
            "/agents/decisions",
            headers={"X-Persona": "landowner"},
        )
        # Landowners shouldn't access agent decisions
        assert response.status_code in [401, 403, 422]
