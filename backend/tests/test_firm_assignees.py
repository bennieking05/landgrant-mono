"""Firm-scoped assignee list for parcel filters (``/users/me/firm-assignees``)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.models import Persona
from app.main import app
from tests.jwt_helpers import auth_headers

client = TestClient(app)


def test_firm_assignees_requires_auth() -> None:
    assert client.get("/users/me/firm-assignees").status_code == 401


def test_firm_assignees_staff_non_empty() -> None:
    h = auth_headers(Persona.LAND_AGENT, user_id="AGENT-001", email="agent@example.com")
    r = client.get("/users/me/firm-assignees", headers=h)
    assert r.status_code == 200
    items = r.json()["items"]
    assert isinstance(items, list)
    assert len(items) >= 1
    ids = {x["id"] for x in items}
    assert "AGENT-001" in ids


def test_firm_assignees_landowner_empty() -> None:
    h = auth_headers(Persona.LANDOWNER, user_id="LANDOWNER-001", email="owner@example.com")
    r = client.get("/users/me/firm-assignees", headers=h)
    assert r.status_code == 200
    assert r.json()["items"] == []
