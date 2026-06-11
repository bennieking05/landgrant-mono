"""RBAC and scope checks for comms feed, notices, and complaint-parcel validation."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.models import Persona
from app.main import app

from tests.jwt_helpers import auth_headers

client = TestClient(app)


def _landowner_headers() -> dict[str, str]:
    return auth_headers(
        Persona.LANDOWNER,
        user_id="LANDOWNER-001",
        email="owner@example.com",
    )


def test_communications_feed_land_agent_ok() -> None:
    h = auth_headers(Persona.LAND_AGENT, user_id="AGENT-001")
    res = client.get("/communications/feed?project_id=PRJ-001", headers=h)
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body.get("items"), list)


def test_communications_feed_landowner_no_parcel_filter_ok() -> None:
    res = client.get("/communications/feed?project_id=PRJ-001", headers=_landowner_headers())
    assert res.status_code == 200


def test_communications_feed_landowner_scoped_parcel_allowed() -> None:
    """Grant covers PARCEL-001 only (see dev seed)."""
    res = client.get(
        "/communications/feed?project_id=PRJ-001&parcel_id=PARCEL-001",
        headers=_landowner_headers(),
    )
    assert res.status_code == 200


def test_communications_feed_landowner_scoped_parcel_denied() -> None:
    res = client.get(
        "/communications/feed?project_id=PRJ-001&parcel_id=PARCEL-002",
        headers=_landowner_headers(),
    )
    assert res.status_code == 403
    assert res.json().get("detail") == "parcel_access_denied"


def test_notices_list_landowner_read() -> None:
    res = client.get("/notices?parcel_id=PARCEL-001", headers=_landowner_headers())
    assert res.status_code == 200
    assert res.json().get("parcel_id") == "PARCEL-001"


def test_notices_create_landowner_forbidden() -> None:
    res = client.post(
        "/notices",
        headers=_landowner_headers(),
        json={
            "parcel_id": "PARCEL-001",
            "project_id": "PRJ-001",
            "notice_type": "statutory",
            "method": "certified_mail",
            "jurisdiction": "TX",
        },
    )
    assert res.status_code == 403
    assert "cannot" in (res.json().get("detail") or "")


def test_notices_create_land_agent_ok() -> None:
    h = auth_headers(Persona.LAND_AGENT, user_id="AGENT-001")
    res = client.post(
        "/notices",
        headers=h,
        json={
            "parcel_id": "PARCEL-001",
            "project_id": "PRJ-001",
            "notice_type": "statutory",
            "method": "certified_mail",
            "jurisdiction": "TX",
        },
    )
    assert res.status_code == 200
    assert "notice_id" in res.json()


def test_complaint_parcels_validate_same_county_ok() -> None:
    h = auth_headers(Persona.IN_HOUSE_COUNSEL, user_id="COUNSEL-001")
    res = client.post(
        "/litigation/complaint-parcels/validate",
        headers=h,
        json={"project_id": "PRJ-001", "parcel_ids": ["PARCEL-001", "PARCEL-002"]},
    )
    assert res.status_code == 200
    assert res.json().get("ok") is True
    assert res.json().get("errors") == []


def test_complaint_parcels_validate_different_county_fails() -> None:
    h = auth_headers(Persona.IN_HOUSE_COUNSEL, user_id="COUNSEL-001")
    res = client.post(
        "/litigation/complaint-parcels/validate",
        headers=h,
        json={"project_id": "PRJ-001", "parcel_ids": ["PARCEL-001", "PARCEL-004"]},
    )
    assert res.status_code == 200
    body = res.json()
    assert body.get("ok") is False
    assert "parcels_must_share_county" in body.get("errors", [])


def test_complaint_parcels_validate_landowner_forbidden() -> None:
    res = client.post(
        "/litigation/complaint-parcels/validate",
        headers=_landowner_headers(),
        json={"project_id": "PRJ-001", "parcel_ids": ["PARCEL-001", "PARCEL-002"]},
    )
    assert res.status_code == 403
    assert "cannot" in (res.json().get("detail") or "")


def test_litigation_tracks_counsel() -> None:
    h = auth_headers(Persona.IN_HOUSE_COUNSEL, user_id="COUNSEL-001")
    listed = client.get("/litigation?parcel_id=PARCEL-001", headers=h)
    assert listed.status_code == 200
    items = listed.json().get("items") or []
    if not items:
        pytest.skip("no litigation case seeded for PARCEL-001")
    case_id = items[0]["id"]
    res = client.get(f"/litigation/{case_id}/tracks", headers=h)
    assert res.status_code == 200
    data = res.json()
    assert data.get("case_id") == case_id
    assert "tx" in data and "in" in data
