"""Tests for ``GET /projects/{id}/hierarchy``."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.models import Persona
from app.main import app

from tests.jwt_helpers import auth_headers

client = TestClient(app)


def test_project_hierarchy_smoke():
    res = client.get(
        "/projects/PRJ-001/hierarchy",
        headers=auth_headers(Persona.LAND_AGENT, user_id="agent-h"),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["project"]["id"] == "PRJ-001"
    assert isinstance(body["alignments"], list)
    assert isinstance(body["unassigned_parcels"], list)
