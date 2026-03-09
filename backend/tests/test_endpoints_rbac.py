from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@pytest.mark.parametrize(
    "path,method,persona,expected_status",
    [
        ("/health/live", "GET", "landowner", 200),
        ("/health/invite", "GET", "landowner", 200),
        ("/health/esign", "GET", "landowner", 200),
        ("/templates", "GET", "in_house_counsel", 200),
        ("/templates", "GET", "outside_counsel", 403),
        ("/workflows/approvals", "GET", "in_house_counsel", 200),
        ("/workflows/approvals", "GET", "land_agent", 403),
        ("/workflows/binder/export", "POST", "in_house_counsel", 200),
        ("/workflows/binder/export", "POST", "land_agent", 403),
        ("/communications?parcel_id=PARCEL-001", "GET", "land_agent", 200),
        ("/communications?parcel_id=PARCEL-001", "GET", "landowner", 403),
        ("/portal/decision/options", "GET", "landowner", 200),
        ("/portal/decision/options", "GET", "land_agent", 403),
    ],
)
def test_endpoints_rbac(path: str, method: str, persona: str, expected_status: int) -> None:
    headers = {"X-Persona": persona}
    if method == "GET":
        res = client.get(path, headers=headers)
    elif method == "POST":
        res = client.post(path, headers=headers, json={})
    else:
        raise AssertionError(f"unsupported method {method}")
    assert res.status_code == expected_status


def test_invalid_persona_header_rejected() -> None:
    # Choose an endpoint that depends on get_current_persona, otherwise X-Persona is ignored.
    res = client.get("/templates", headers={"X-Persona": "not_a_persona"})
    assert res.status_code == 401


def test_portal_invite_requires_payload() -> None:
    # This ensures request validation is active.
    res = client.post("/portal/invites", headers={"X-Persona": "landowner"}, json={})
    assert res.status_code == 422


