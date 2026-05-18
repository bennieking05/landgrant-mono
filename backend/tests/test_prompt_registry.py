"""Phase 1.4: PromptTemplate ORM-backed registry."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models  # noqa: F401
from app.db.session import Base
from app.services.prompt_registry import (
    get_active_prompt,
    resolve_for_task,
    seed_default_prompts,
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


def test_seed_default_prompts_is_idempotent(db_session):
    first = seed_default_prompts(db_session)
    second = seed_default_prompts(db_session)
    assert {p.name for p in first} == {
        "legal_analysis",
        "document_review",
        "risk_assessment",
    }
    assert [p.id for p in first] == [p.id for p in second]


def test_resolve_for_task_maps_task_types(db_session):
    seed_default_prompts(db_session)

    draft = resolve_for_task(db_session, "draft_analysis")
    doc = resolve_for_task(db_session, "document_review")
    risk = resolve_for_task(db_session, "risk_assessment")
    unknown = resolve_for_task(db_session, "nope")

    assert draft is not None and draft.name == "legal_analysis"
    assert doc is not None and doc.name == "document_review"
    assert risk is not None and risk.name == "risk_assessment"
    assert unknown is None


def test_inactive_prompt_is_skipped(db_session):
    seed_default_prompts(db_session)
    active = get_active_prompt(db_session, "legal_analysis")
    assert active is not None

    row = db_session.get(models.PromptTemplate, active.id)
    row.is_active = False
    db_session.commit()

    assert get_active_prompt(db_session, "legal_analysis") is None
