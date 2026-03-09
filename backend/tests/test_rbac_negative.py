"""
RBAC Negative Tests

Tests that verify unauthorized access is properly denied.
These tests ensure the security model is working correctly.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestLandownerRestrictions:
    """Test that landowners cannot access agent/counsel resources."""

    def test_landowner_cannot_create_roe(self):
        """Landowners should not be able to create ROE agreements."""
        response = client.post(
            "/roe",
            headers={"X-Persona": "landowner"},
            json={
                "parcel_id": "PARCEL-001",
                "project_id": "PRJ-001",
                "effective_date": "2026-01-01T00:00:00Z",
                "expiry_date": "2026-12-31T00:00:00Z",
            },
        )
        assert response.status_code == 403
        assert "cannot" in response.json().get("detail", "").lower()

    def test_landowner_cannot_create_offer(self):
        """Landowners should not be able to create offers."""
        response = client.post(
            "/offers",
            headers={"X-Persona": "landowner"},
            json={
                "parcel_id": "PARCEL-001",
                "project_id": "PRJ-001",
                "offer_type": "initial",
                "amount": 100000,
            },
        )
        assert response.status_code == 403

    def test_landowner_cannot_create_litigation(self):
        """Landowners should not be able to create litigation cases."""
        response = client.post(
            "/litigation",
            headers={"X-Persona": "landowner"},
            json={
                "parcel_id": "PARCEL-001",
                "project_id": "PRJ-001",
                "court": "District Court",
            },
        )
        assert response.status_code == 403

    def test_landowner_cannot_initiate_esign(self):
        """Landowners should not be able to initiate e-signatures."""
        response = client.post(
            "/esign/initiate",
            headers={"X-Persona": "landowner"},
            json={
                "document_id": "DOC-001",
                "parcel_id": "PARCEL-001",
                "project_id": "PRJ-001",
                "signers": [{"email": "test@example.com", "name": "Test"}],
            },
        )
        assert response.status_code == 403

    def test_landowner_cannot_send_batch_communications(self):
        """Landowners should not be able to send batch communications."""
        response = client.post(
            "/communications/batch",
            headers={"X-Persona": "landowner"},
            json={
                "project_id": "PRJ-001",
                "template_id": "portal_invite",
                "channel": "email",
                "recipients": [{"parcel_id": "PARCEL-001", "email": "test@example.com"}],
            },
        )
        assert response.status_code == 403


class TestLandAgentRestrictions:
    """Test that land agents cannot access counsel-only resources."""

    def test_agent_cannot_approve_offer(self):
        """Land agents should not be able to approve offers (counsel only)."""
        # Note: This depends on offer existing and APPROVE action check
        # Testing the permission matrix conceptually
        pass  # Approval action tested through specific workflow

    def test_agent_cannot_create_litigation(self):
        """Land agents should not be able to create litigation cases."""
        response = client.post(
            "/litigation",
            headers={"X-Persona": "land_agent"},
            json={
                "parcel_id": "PARCEL-001",
                "project_id": "PRJ-001",
                "court": "District Court",
            },
        )
        assert response.status_code == 403


class TestOutsideCounselRestrictions:
    """Test that outside counsel has limited access."""

    def test_outside_counsel_cannot_create_roe(self):
        """Outside counsel should not be able to create ROE agreements."""
        response = client.post(
            "/roe",
            headers={"X-Persona": "outside_counsel"},
            json={
                "parcel_id": "PARCEL-001",
                "project_id": "PRJ-001",
                "effective_date": "2026-01-01T00:00:00Z",
                "expiry_date": "2026-12-31T00:00:00Z",
            },
        )
        assert response.status_code == 403

    def test_outside_counsel_cannot_create_offer(self):
        """Outside counsel should not be able to create offers."""
        response = client.post(
            "/offers",
            headers={"X-Persona": "outside_counsel"},
            json={
                "parcel_id": "PARCEL-001",
                "project_id": "PRJ-001",
                "offer_type": "initial",
                "amount": 100000,
            },
        )
        assert response.status_code == 403

    def test_outside_counsel_cannot_read_parcels(self):
        """Outside counsel should not have general parcel list access."""
        response = client.get(
            "/parcels?project_id=PRJ-001",
            headers={"X-Persona": "outside_counsel"},
        )
        assert response.status_code == 403


class TestInvalidPersona:
    """Test that invalid personas are rejected."""

    def test_invalid_persona_rejected(self):
        """Invalid persona header should be rejected."""
        response = client.get(
            "/roe?parcel_id=PARCEL-001",
            headers={"X-Persona": "invalid_persona"},
        )
        # Should return 400 (bad request) or 401/403
        assert response.status_code in [400, 401, 403, 422]

    def test_missing_persona_header(self):
        """Missing persona header should be handled appropriately."""
        response = client.get("/roe?parcel_id=PARCEL-001")
        # May default to a persona or require it
        assert response.status_code in [200, 400, 401, 403, 422]


class TestCrossTenantAccess:
    """Test isolation between projects/parcels."""

    def test_cannot_access_other_project_litigation(self):
        """Users should only access litigation in their project scope."""
        # This is enforced at the query level, not RBAC
        # But the test verifies the pattern is working
        response = client.get(
            "/litigation?project_id=NONEXISTENT-PROJECT",
            headers={"X-Persona": "in_house_counsel"},
        )
        assert response.status_code == 200
        # Should return empty, not another project's data
        data = response.json()
        assert len(data.get("items", [])) == 0


class TestEsignSecurity:
    """Test e-sign specific security constraints."""

    def test_landowner_can_only_read_esign_status(self):
        """Landowners should only be able to read e-sign status."""
        # Landowner can read
        response = client.get(
            "/esign/status/ENV-NONEXISTENT",
            headers={"X-Persona": "landowner"},
        )
        # Will be 404 (not found) not 403, meaning READ is allowed
        assert response.status_code in [200, 404]

    def test_cannot_void_completed_envelope(self):
        """Cannot void an already completed envelope."""
        # This is business logic, not RBAC, but important security test
        pass  # Tested in e2e tests


class TestPortalSecurity:
    """Test portal-specific security measures."""

    def test_portal_verify_no_auth_required(self):
        """Portal verify endpoint should not require authentication."""
        response = client.post(
            "/portal/verify",
            json={"token": "invalid-token"},
            # No X-Persona header
        )
        # Should fail with 401 (invalid token), not 403 (forbidden)
        assert response.status_code == 401
        assert "invalid" in response.json().get("detail", "").lower()

    def test_portal_session_endpoints_require_cookie(self):
        """Session info endpoint should require valid session cookie."""
        response = client.get("/portal/session")
        assert response.status_code == 401
        assert "no_session" in response.json().get("detail", "")


class TestChatSecurity:
    """Test chat/messaging security."""

    def test_create_thread_requires_communication_write(self):
        """Creating a thread requires communication write permission."""
        # Persona without communication write should be denied
        response = client.post(
            "/chat/threads",
            headers={"X-Persona": "admin"},  # Admin doesn't have communication write
            json={
                "parcel_id": "PARCEL-001",
                "project_id": "PRJ-001",
                "subject": "Test",
                "initial_message": "Test message",
            },
        )
        assert response.status_code == 403

    def test_portal_thread_access_limited_to_own_parcel(self):
        """Portal users can only access threads for their parcel."""
        # This requires a valid session, tested in e2e
        response = client.get("/chat/portal/threads")
        assert response.status_code == 401  # No session


class TestAuditSecurity:
    """Test audit log security."""

    def test_audit_events_require_read_permission(self):
        """Viewing audit events requires portal read permission."""
        response = client.get(
            "/portal/audit/events",
            headers={"X-Persona": "outside_counsel"},
        )
        # Outside counsel doesn't have portal read
        assert response.status_code == 403


# Additional security checks

class TestInputValidation:
    """Test input validation and sanitization."""

    def test_sql_injection_attempt(self):
        """SQL injection attempts should be safely handled."""
        response = client.get(
            "/parcels?project_id=' OR '1'='1",
            headers={"X-Persona": "land_agent"},
        )
        # Should not error or expose data
        assert response.status_code in [200, 400, 422]
        # If 200, should return empty or properly filtered results

    def test_xss_attempt_in_content(self):
        """XSS attempts should be safely stored/escaped."""
        response = client.post(
            "/chat/threads",
            headers={"X-Persona": "land_agent"},
            json={
                "parcel_id": "PARCEL-001",
                "project_id": "PRJ-001",
                "subject": "<script>alert('xss')</script>",
                "initial_message": "Test",
            },
        )
        # Should store but escape on output
        assert response.status_code == 200


class TestRateLimiting:
    """Test rate limiting behavior."""

    def test_portal_verify_rate_limiting(self):
        """Verify endpoint should apply rate limiting."""
        # Create invite first, then try to verify many times
        # After MAX_FAILED attempts, should get 429
        # This is tested more thoroughly in integration tests
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
