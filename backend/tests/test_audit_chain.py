"""Phase 3.2: audit hash chain + privilege/retention columns."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models
from app.db.session import Base
from app.services.audit_chain import append_audit_event, verify_chain


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    s = Session()
    try:
        yield s
    finally:
        s.close()
        engine.dispose()


def test_chain_verifies_intact_log(db_session):
    for i in range(5):
        append_audit_event(
            db_session,
            action="document.create",
            resource=f"doc-{i}",
            payload={"i": i},
            firm_id="firm_a",
        )
    result = verify_chain(db_session, firm_id="firm_a")
    assert result.verified is True
    assert result.rows_checked == 5


def test_chain_detects_payload_tampering(db_session):
    events = [
        append_audit_event(
            db_session,
            action="document.update",
            resource=f"doc-{i}",
            payload={"i": i},
            firm_id="firm_a",
        )
        for i in range(3)
    ]

    # Tamper: flip a payload on the middle event.
    middle = events[1]
    middle.payload = {"i": 999}
    db_session.commit()

    result = verify_chain(db_session, firm_id="firm_a")
    assert result.verified is False
    assert result.first_bad_event == middle.id


def test_chain_is_firm_scoped(db_session):
    append_audit_event(
        db_session, action="a", resource="r", firm_id="firm_a", payload={}
    )
    append_audit_event(
        db_session, action="b", resource="r", firm_id="firm_b", payload={}
    )
    # Each firm's chain should verify independently.
    assert verify_chain(db_session, firm_id="firm_a").verified is True
    assert verify_chain(db_session, firm_id="firm_b").verified is True


def test_document_privilege_defaults(db_session):
    doc = models.Document(
        id="doc_1",
        doc_type="petition",
        sha256="abc",
        storage_path="/tmp/doc",
    )
    db_session.add(doc)
    db_session.commit()

    reloaded = db_session.get(models.Document, "doc_1")
    assert reloaded.privilege_class == "work_product"
    assert reloaded.retention_class == "default"
    assert reloaded.litigation_hold in (False, None)


def test_document_litigation_hold_flag(db_session):
    doc = models.Document(
        id="doc_2",
        doc_type="deed",
        sha256="xyz",
        storage_path="/tmp/doc2",
        privilege_class="attorney_client",
        litigation_hold=True,
    )
    db_session.add(doc)
    db_session.commit()

    reloaded = db_session.get(models.Document, "doc_2")
    assert reloaded.privilege_class == "attorney_client"
    assert reloaded.litigation_hold is True
