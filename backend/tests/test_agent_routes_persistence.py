"""Phase 1.3: /agents/* routes round-trip against AIDecision/EscalationRequest."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def counsel_headers():
    return {"X-Persona": "in_house_counsel"}


@pytest.fixture()
def seeded_decision():
    db = SessionLocal()
    decision_id = str(uuid4())
    # Ensure the reviewer referenced by assignment/resolution tests exists.
    # ``escalation_requests.assigned_to`` has a FK to ``users.id``; without this
    # pre-seeded user the route would fail with a 404 and the DB would reject
    # the update.
    assignee_id = "USER-42"
    created_assignee = False
    try:
        if db.get(models.User, assignee_id) is None:
            db.add(
                models.User(
                    id=assignee_id,
                    email="reviewer-42@example.com",
                    persona=models.Persona.IN_HOUSE_COUNSEL,
                    full_name="Reviewer 42",
                )
            )
            db.commit()
            created_assignee = True
        decision = models.AIDecision(
            id=decision_id,
            agent_type="ComplianceAgent",
            project_id="PRJ-001",
            parcel_id="PARCEL-001",
            context_hash="c" * 64,
            result_data={"ok": True},
            confidence=0.83,
            flags=["minor_issue"],
            explanation="seeded",
            occurred_at=datetime.utcnow(),
            hash="h" * 64,
        )
        escalation = models.EscalationRequest(
            id=str(uuid4()),
            ai_decision_id=decision_id,
            reason="low_confidence",
            priority="medium",
            status="open",
            created_at=datetime.utcnow(),
        )
        db.add(decision)
        db.add(escalation)
        db.commit()
        yield {"decision_id": decision.id, "escalation_id": escalation.id}
    finally:
        try:
            db.query(models.EscalationRequest).filter_by(
                ai_decision_id=decision_id
            ).delete()
            db.query(models.AIDecision).filter_by(id=decision_id).delete()
            if created_assignee:
                db.query(models.User).filter_by(id=assignee_id).delete()
            db.commit()
        finally:
            db.close()


def test_get_ai_decision_returns_persisted_row(client, counsel_headers, seeded_decision):
    response = client.get(
        f"/agents/decisions/{seeded_decision['decision_id']}",
        headers=counsel_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == seeded_decision["decision_id"]
    assert data["agent_type"] == "ComplianceAgent"
    assert data["flags"] == ["minor_issue"]


def test_list_ai_decisions_includes_seeded(client, counsel_headers, seeded_decision):
    response = client.get(
        "/agents/decisions?project_id=PRJ-001",
        headers=counsel_headers,
    )
    assert response.status_code == 200
    ids = [d["id"] for d in response.json()]
    assert seeded_decision["decision_id"] in ids


def test_resolve_escalation_updates_db(client, counsel_headers, seeded_decision):
    response = client.post(
        f"/agents/escalations/{seeded_decision['escalation_id']}/resolve",
        json={"resolution": "reviewed", "outcome": "approved"},
        headers=counsel_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"

    db = SessionLocal()
    try:
        row = db.get(models.EscalationRequest, seeded_decision["escalation_id"])
        assert row is not None
        assert row.status == "resolved"
        assert row.resolved_at is not None
    finally:
        db.close()


def test_assign_escalation_updates_db(client, counsel_headers, seeded_decision):
    response = client.post(
        f"/agents/escalations/{seeded_decision['escalation_id']}/assign?assignee_id=USER-42",
        headers=counsel_headers,
    )
    assert response.status_code == 200
    assert response.json()["assigned_to"] == "USER-42"
