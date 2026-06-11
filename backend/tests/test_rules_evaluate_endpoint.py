"""Tests for ``POST /rules/evaluate``."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.models import Persona
from app.main import app

from tests.jwt_helpers import auth_headers

client = TestClient(app)


def test_rules_evaluate_requires_auth():
    res = client.post("/rules/evaluate", json={"jurisdiction": "IN", "case_payload": {}})
    assert res.status_code == 401


def test_rules_evaluate_indiana_triggers_and_deadlines():
    res = client.post(
        "/rules/evaluate",
        headers=auth_headers(Persona.IN_HOUSE_COUNSEL, user_id="c-1"),
        json={
            "jurisdiction": "IN",
            "case_payload": {
                "case": {"jurisdiction": "IN"},
                "events": {"offer_served": "2026-01-01"},
            },
            "anchor_events": {"offer_served": "2026-06-01"},
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["jurisdiction"] == "IN"
    assert len(body["triggers"]) >= 1
    assert any(d["deadline_type"] == "deadline" for d in body["deadlines"])
