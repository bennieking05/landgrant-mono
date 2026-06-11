"""Saved parcel grid views (``/users/me/parcel-views``)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.models import Persona
from app.main import app
from tests.jwt_helpers import auth_headers

client = TestClient(app)


def test_parcel_grid_views_list_requires_auth() -> None:
    assert client.get("/users/me/parcel-views").status_code == 401


def test_parcel_grid_views_crud() -> None:
    h = auth_headers(Persona.LAND_AGENT, user_id="AGENT-001", email="agent@example.com")
    assert client.get("/users/me/parcel-views", headers=h).status_code == 200

    name = "pytest_view_a9f2"
    created = client.post(
        "/users/me/parcel-views",
        headers=h,
        json={"name": name, "payload": {"q": "abc", "stage": ""}},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["name"] == name
    assert body["payload"]["q"] == "abc"
    vid = body["id"]

    dup = client.post(
        "/users/me/parcel-views",
        headers=h,
        json={"name": name, "payload": {}},
    )
    assert dup.status_code == 409

    listed = client.get("/users/me/parcel-views", headers=h)
    assert listed.status_code == 200
    ids = {item["id"] for item in listed.json()["items"]}
    assert vid in ids

    other = auth_headers(Persona.LAND_AGENT, user_id="OUTSIDE-001", email="outside@example.com")
    forbidden = client.delete(f"/users/me/parcel-views/{vid}", headers=other)
    assert forbidden.status_code == 403

    deleted = client.delete(f"/users/me/parcel-views/{vid}", headers=h)
    assert deleted.status_code == 200
