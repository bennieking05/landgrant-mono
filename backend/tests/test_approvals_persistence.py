"""Phase 1.2: ApprovalService DB persistence and @requires_approval decorator."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models  # noqa: F401  (registers tables)
from app.db.session import Base
from app.services.approvals import (
    ApprovalRequest,
    ApprovalService,
    action_requires_approval,
    requires_approval,
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


def test_approvals_survive_restart(db_session):
    first = ApprovalService(db=db_session)
    approval = first.request_approval(
        ApprovalRequest(
            entity_type="document",
            entity_id="doc-xyz",
            action="send",
            content_hash="h0",
            project_id="PRJ",
            jurisdiction="TX",
        ),
        user_id="user-1",
    )
    assert approval.id.startswith("appr_")

    # A fresh service with the same DB session must see the persisted row.
    second = ApprovalService(db=db_session)
    reloaded = second.get_approval(approval.id)
    assert reloaded is not None
    assert reloaded.status == "pending_review"
    assert reloaded.entity_id == "doc-xyz"


def test_idempotent_request_returns_existing(db_session):
    service = ApprovalService(db=db_session)
    req = ApprovalRequest(
        entity_type="filing",
        entity_id="FILE-1",
        action="file_petition",
        content_hash="h1",
    )
    a = service.request_approval(req, user_id="u1")
    b = service.request_approval(req, user_id="u2")
    assert a.id == b.id


def test_approve_and_list_through_db(db_session):
    service = ApprovalService(db=db_session)
    approval = service.request_approval(
        ApprovalRequest(
            entity_type="document",
            entity_id="doc-1",
            action="send",
            content_hash="h",
        ),
        user_id="u1",
    )
    service.approve(approval.id, user_id="counsel-1", notes="ok")

    rows = service.list_approvals(status="approved")
    assert len(rows) == 1
    assert rows[0].id == approval.id
    assert rows[0].approval_notes == "ok"


def test_action_requires_approval_predicate():
    assert action_requires_approval("document", "send")
    assert action_requires_approval("binder", "export")
    assert not action_requires_approval("document", "read")


def test_requires_approval_decorator_blocks_without_approval(db_session):
    @requires_approval("document", "send")
    async def send_doc(*, entity_id: str, content_hash: str, db):
        return {"sent": True}

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(send_doc(entity_id="doc-42", content_hash="h", db=db_session))

    assert excinfo.value.status_code == 409
    detail = excinfo.value.detail
    assert detail["error"] == "approval_required"


def test_requires_approval_decorator_allows_after_approval(db_session):
    service = ApprovalService(db=db_session)
    approval = service.request_approval(
        ApprovalRequest(
            entity_type="document",
            entity_id="doc-ok",
            action="send",
            content_hash="h",
        ),
        user_id="u1",
    )
    service.approve(approval.id, user_id="counsel-1")

    @requires_approval("document", "send")
    async def send_doc(*, entity_id: str, content_hash: str, db):
        return {"sent": True}

    result = asyncio.run(send_doc(entity_id="doc-ok", content_hash="h", db=db_session))
    assert result == {"sent": True}


def test_requires_approval_decorator_noop_for_non_gated_action(db_session):
    @requires_approval("document", "read")
    async def read_doc(*, entity_id: str, content_hash: str, db):
        return {"read": True}

    result = asyncio.run(read_doc(entity_id="doc-1", content_hash="h", db=db_session))
    assert result == {"read": True}
