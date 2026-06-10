from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.models import Persona
from app.main import app

from tests.jwt_helpers import auth_headers

client = TestClient(app)


def _h(
    persona: Persona,
    *,
    user_id: str = "u-test",
    firm_id: str | None = "firm_default",
    email: str | None = None,
) -> dict[str, str]:
    return auth_headers(
        persona=persona, user_id=user_id, firm_id=firm_id, email=email
    )


@pytest.mark.parametrize(
    "path,method,persona,expected_status,token_kwargs",
    [
        ("/health/live", "GET", None, 200, {}),
        ("/health/invite", "GET", Persona.IN_HOUSE_COUNSEL, 200, {}),
        ("/health/esign", "GET", Persona.IN_HOUSE_COUNSEL, 200, {}),
        ("/health/invite", "GET", Persona.LANDOWNER, 403, {"email": "owner@example.com"}),
        ("/health/esign", "GET", Persona.LANDOWNER, 403, {"email": "owner@example.com"}),
        ("/templates", "GET", Persona.IN_HOUSE_COUNSEL, 200, {}),
        ("/templates", "GET", Persona.OUTSIDE_COUNSEL, 403, {}),
        ("/workflows/approvals", "GET", Persona.IN_HOUSE_COUNSEL, 200, {}),
        ("/workflows/approvals", "GET", Persona.LAND_AGENT, 403, {}),
        ("/workflows/binder/export", "POST", Persona.IN_HOUSE_COUNSEL, 500, {}),
        ("/workflows/binder/export", "POST", Persona.LAND_AGENT, 403, {}),
        ("/communications?parcel_id=PARCEL-001", "GET", Persona.LAND_AGENT, 200, {}),
        (
            "/communications?parcel_id=PARCEL-002",
            "GET",
            Persona.LANDOWNER,
            403,
            {"email": "owner@example.com"},
        ),
        (
            "/communications?parcel_id=PARCEL-001",
            "GET",
            Persona.LANDOWNER,
            200,
            {"email": "owner@example.com"},
        ),
        ("/portal/decision/options", "GET", Persona.LANDOWNER, 200, {"email": "x@y.com"}),
        ("/portal/decision/options", "GET", Persona.LAND_AGENT, 200, {}),
        ("/rag/health", "GET", Persona.IN_HOUSE_COUNSEL, 200, {}),
        ("/rag/health", "GET", Persona.LANDOWNER, 403, {"email": "owner@example.com"}),
        ("/copilot/conversations", "GET", Persona.IN_HOUSE_COUNSEL, 200, {}),
        ("/copilot/conversations", "GET", Persona.LANDOWNER, 403, {"email": "owner@example.com"}),
        ("/analytics/property-types", "GET", Persona.LAND_AGENT, 200, {}),
        ("/analytics/property-types", "GET", Persona.LANDOWNER, 403, {"email": "owner@example.com"}),
        ("/predictions/health", "GET", Persona.IN_HOUSE_COUNSEL, 200, {}),
        ("/predictions/health", "GET", Persona.LANDOWNER, 403, {"email": "owner@example.com"}),
        ("/rules/results?parcel_id=PARCEL-001", "GET", Persona.LAND_AGENT, 200, {}),
        ("/rules/summary/common", "GET", Persona.IN_HOUSE_COUNSEL, 200, {}),
    ],
)
def test_endpoints_rbac(
    path: str,
    method: str,
    persona: Persona | None,
    expected_status: int,
    token_kwargs: dict,
) -> None:
    headers = _h(persona, **token_kwargs) if persona is not None else {}
    if method == "GET":
        res = client.get(path, headers=headers)
    elif method == "POST":
        body: dict = {}
        if "binder/export" in path:
            body = {"project_id": "PRJ-001"}
        res = client.post(path, headers=headers, json=body)
    else:
        raise AssertionError(f"unsupported method {method}")
    assert res.status_code == expected_status


def test_missing_bearer_rejected() -> None:
    res = client.get("/templates")
    assert res.status_code == 401


def test_portal_invite_requires_payload() -> None:
    res = client.post(
        "/portal/invites",
        headers=_h(Persona.LAND_AGENT, user_id="AGENT-001"),
        json={},
    )
    assert res.status_code == 422
