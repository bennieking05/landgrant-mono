"""Tests for GET /search (staff global search, UX-2)."""

from fastapi.testclient import TestClient

from app.db.models import Persona
from app.main import app

from tests.jwt_helpers import auth_headers

client = TestClient(app)

_LANDOWNER = auth_headers(Persona.LANDOWNER, email="owner@example.com")
_LAND_AGENT = auth_headers(Persona.LAND_AGENT, user_id="AGENT-001")


def test_search_landowner_empty():
    r = client.get("/search?q=ab", headers=_LANDOWNER)
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 0
    assert body["results"] == []


def test_search_staff_requires_min_length():
    r = client.get("/search?q=a", headers=_LAND_AGENT)
    assert r.status_code == 422


def test_search_staff_ok_shape():
    r = client.get("/search?q=00", headers=_LAND_AGENT)
    assert r.status_code == 200
    body = r.json()
    assert "query" in body
    assert "results" in body
    assert "count" in body
    assert isinstance(body["results"], list)
