"""HTTP tests for ``GET /jurisdictions``."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.models import Persona
from app.main import app

from tests.jwt_helpers import auth_headers

client = TestClient(app)


def test_jurisdictions_requires_auth():
    res = client.get("/jurisdictions")
    assert res.status_code == 401


def test_jurisdictions_tx_in_only():
    res = client.get(
        "/jurisdictions",
        headers=auth_headers(Persona.LAND_AGENT, user_id="agent-1"),
    )
    assert res.status_code == 200
    data = res.json()
    codes = {item["code"] for item in data["items"]}
    assert codes == {"TX", "IN"}
