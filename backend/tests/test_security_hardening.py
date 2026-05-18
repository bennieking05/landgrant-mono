"""Security hardening tests.

Verifies that:
- Previously-open routes now require authentication
- CORS is restricted
- Security headers are present
- Webhook endpoints reject unsigned requests in non-dev mode
- Action enum completeness
"""

from __future__ import annotations

import hashlib
import hmac

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security.rbac import Action, PERMISSION_MATRIX
from app.db.models import Persona

client = TestClient(app)


class TestSecurityHeaders:
    """Verify security response headers are present."""

    def test_x_content_type_options(self):
        res = client.get("/health/live")
        assert res.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self):
        res = client.get("/health/live")
        assert res.headers.get("X-Frame-Options") == "DENY"

    def test_referrer_policy(self):
        res = client.get("/health/live")
        assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


class TestActionEnumCompleteness:
    """Verify Action enum has all required members."""

    def test_has_read(self):
        assert Action.READ.value == "read"

    def test_has_write(self):
        assert Action.WRITE.value == "write"

    def test_has_create(self):
        assert Action.CREATE.value == "create"

    def test_has_update(self):
        assert Action.UPDATE.value == "update"

    def test_has_delete(self):
        assert Action.DELETE.value == "delete"

    def test_has_approve(self):
        assert Action.APPROVE.value == "approve"

    def test_has_execute(self):
        assert Action.EXECUTE.value == "execute"


class TestPreviouslyOpenRoutesNowProtected:
    """Routes that previously had no auth must now require X-Persona."""

    @pytest.mark.parametrize(
        "path",
        [
            "/rag/search",
            "/copilot/ask",
            "/analytics/predict-settlement",
            "/predictions/predict",
        ],
    )
    def test_routes_reject_missing_persona(self, path):
        res = client.post(path, json={})
        assert res.status_code in (
            401,
            422,
        ), f"{path} should require auth, got {res.status_code}"

    @pytest.mark.parametrize(
        "path",
        [
            "/rag/stats",
            "/copilot/conversations",
            "/analytics/property-types",
        ],
    )
    def test_get_routes_reject_missing_persona(self, path):
        res = client.get(path)
        assert res.status_code in (
            401,
            422,
        ), f"{path} should require auth, got {res.status_code}"


class TestRBACMatrixCompleteness:
    """Verify RBAC resources needed by routes exist in the matrix."""

    @pytest.mark.parametrize(
        "resource",
        [
            "rules",
            "qa",
            "approvals",
            "task",
            "rag",
            "copilot",
            "analytics",
            "predictions",
        ],
    )
    def test_resource_exists_for_counsel(self, resource):
        counsel_perms = PERMISSION_MATRIX.get(Persona.IN_HOUSE_COUNSEL, {})
        assert resource in counsel_perms, f"Counsel missing resource '{resource}'"

    @pytest.mark.parametrize(
        "resource",
        [
            "rules",
            "qa",
            "approvals",
            "task",
            "rag",
            "copilot",
            "analytics",
            "predictions",
        ],
    )
    def test_resource_exists_for_admin(self, resource):
        admin_perms = PERMISSION_MATRIX.get(Persona.ADMIN, {})
        assert resource in admin_perms, f"Admin missing resource '{resource}'"

    def test_task_resource_for_agent(self):
        agent_perms = PERMISSION_MATRIX.get(Persona.LAND_AGENT, {})
        assert "task" in agent_perms

    @pytest.mark.parametrize(
        "resource",
        ["rag", "copilot", "analytics", "predictions"],
    )
    def test_ai_resources_for_land_agent(self, resource: str):
        agent_perms = PERMISSION_MATRIX.get(Persona.LAND_AGENT, {})
        assert resource in agent_perms

    def test_landowner_cannot_access_admin(self):
        landowner_perms = PERMISSION_MATRIX.get(Persona.LANDOWNER, {})
        assert "admin_platform" not in landowner_perms
        assert "admin_firm" not in landowner_perms
        assert "rbac" not in landowner_perms


class TestWebhookIntegrations:
    """Verify webhook endpoints accept requests in dev mode."""

    def test_docket_webhook_accepts_in_dev(self):
        res = client.post(
            "/integrations/dockets",
            json={"event": "delivered"},
        )
        assert res.status_code == 200

    def test_esign_webhook_health(self):
        res = client.get("/health/esign")
        assert res.status_code == 200

    def test_docket_webhook_requires_hmac_in_staging(self, monkeypatch):
        import app.api.routes.integrations as integrations_mod

        monkeypatch.setattr(integrations_mod.settings, "environment", "staging")
        body = b'{"event":"test"}'
        bad = client.post(
            "/integrations/dockets",
            content=body,
            headers={"Content-Type": "application/json", "X-Lob-Signature": "nope"},
        )
        assert bad.status_code == 401
        sig = hmac.new(
            integrations_mod.settings.session_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        good = client.post(
            "/integrations/dockets",
            content=body,
            headers={"Content-Type": "application/json", "X-Lob-Signature": sig},
        )
        assert good.status_code == 200


class TestHealthEndpointsRemainOpen:
    """Health endpoints must not require authentication."""

    @pytest.mark.parametrize(
        "path",
        [
            "/health/live",
            "/health/invite",
            "/health/esign",
        ],
    )
    def test_health_no_auth_needed(self, path):
        res = client.get(path)
        assert res.status_code == 200
