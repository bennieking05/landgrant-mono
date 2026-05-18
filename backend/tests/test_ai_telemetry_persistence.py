"""Tests for the persistent AITelemetryService (Phase 1.1).

Uses a SQLite in-memory engine so we can validate real DB round-trips without
requiring Postgres.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models  # noqa: F401  (registers tables on Base)
from app.db.session import Base
from app.services.ai_telemetry import (
    AIEventInput,
    AITelemetryService,
    estimate_cost,
    extract_usage_from_vertex,
    redact,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_log_event_persists_to_ai_events_table(db_session):
    service = AITelemetryService(db=db_session)

    event = service.log_event(
        AIEventInput(
            action="generate_draft",
            model="gemini-1.5-flash-001",
            inputs={"prompt": "Analyze Texas offer"},
            outputs={"summary": "Looks good"},
            project_id=None,
            actor_persona="in_house_counsel",
            input_tokens=120,
            output_tokens=40,
            latency_ms=350,
        )
    )

    assert event.id.startswith("aievt_")

    reloaded = service.get_event(event.id)
    assert reloaded is not None
    assert reloaded.action == "generate_draft"
    assert reloaded.input_tokens == 120
    assert reloaded.total_tokens == 160
    assert reloaded.cost_estimate_usd is not None

    fresh = AITelemetryService(db=db_session)
    listed = fresh.list_events(limit=10)
    assert any(e.id == event.id for e in listed), "event should survive service re-init"


def test_redact_strips_known_fields_and_pii_patterns():
    payload = {
        "ssn": "123-45-6789",
        "email_body": "Contact me at jane.doe@example.com or 415-555-1212.",
        "nested": {"password": "hunter2", "note": "SSN 987-65-4321 in text"},
        "list": ["555-111-2222", {"api_key": "secret"}],
    }

    cleaned = redact(payload)

    assert cleaned["ssn"] == "[REDACTED]"
    assert "[REDACTED-EMAIL]" in cleaned["email_body"]
    assert "[REDACTED-PHONE]" in cleaned["email_body"]
    assert cleaned["nested"]["password"] == "[REDACTED]"
    assert "[REDACTED-SSN]" in cleaned["nested"]["note"]
    assert cleaned["list"][1]["api_key"] == "[REDACTED]"


def test_log_event_redacts_pii_before_persisting(db_session):
    service = AITelemetryService(db=db_session)
    event = service.log_event(
        AIEventInput(
            action="intake_review",
            model="gemini-1.5-flash-001",
            inputs={
                "prompt": "Owner email is owner@example.com",
                "ssn": "123-45-6789",
            },
            outputs={"result": "ok"},
        )
    )

    reloaded = service.get_event(event.id)
    assert reloaded is not None
    assert reloaded.inputs_json["ssn"] == "[REDACTED]"
    assert "[REDACTED-EMAIL]" in reloaded.inputs_json["prompt"]


def test_estimate_cost_matches_published_rates():
    cost = estimate_cost("gemini-1.5-flash-001", 1000, 1000)
    assert cost == Decimal("0.000075") + Decimal("0.0003")


def test_extract_usage_from_vertex_handles_object_and_dict():
    class _Usage:
        prompt_token_count = 50
        candidates_token_count = 20
        total_token_count = 70

    class _Resp:
        usage_metadata = _Usage()

    out = extract_usage_from_vertex(_Resp())
    assert out == {"input_tokens": 50, "output_tokens": 20, "total_tokens": 70}

    class _Resp2:
        usage = {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10}

    out2 = extract_usage_from_vertex(_Resp2())
    assert out2 == {"input_tokens": 7, "output_tokens": 3, "total_tokens": 10}

    class _Empty:
        pass

    out3 = extract_usage_from_vertex(_Empty())
    assert out3 == {"input_tokens": None, "output_tokens": None, "total_tokens": None}
