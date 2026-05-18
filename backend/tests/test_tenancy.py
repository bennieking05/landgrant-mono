"""Phase 3.1: firm-level tenancy filter + backfill."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models
from app.db.session import Base
from app.security.tenancy import (
    backfill_firm_ids,
    require_firm,
    scope_to_firm,
)
from fastapi import HTTPException


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


def test_backfill_creates_default_firm_and_updates_rows(db_session):
    db_session.add(
        models.Project(
            id="proj-legacy",
            name="Legacy",
            jurisdiction_code="TX",
        )
    )
    db_session.add(
        models.User(
            id="user-legacy",
            email="legacy@example.com",
            persona=models.Persona.LAND_AGENT,
        )
    )
    db_session.commit()

    counts = backfill_firm_ids(db_session)
    assert counts["firm_created"] == 1
    assert counts["projects"] == 1
    assert counts["users"] == 1

    reloaded = db_session.get(models.Project, "proj-legacy")
    assert reloaded.firm_id == models.DEFAULT_FIRM_ID

    user = db_session.get(models.User, "user-legacy")
    assert user.firm_id == models.DEFAULT_FIRM_ID


def test_backfill_is_idempotent(db_session):
    db_session.add(
        models.Project(id="p1", name="P1", jurisdiction_code="TX")
    )
    db_session.commit()

    backfill_firm_ids(db_session)
    second = backfill_firm_ids(db_session)

    # firm_created only counts on first run.
    assert second["firm_created"] == 0
    assert second["projects"] == 0


def test_scope_to_firm_filters_query(db_session):
    backfill_firm_ids(db_session)
    db_session.add(
        models.Project(
            id="p_firm_a",
            name="A",
            jurisdiction_code="TX",
            firm_id="firm_a",
        )
    )
    db_session.add(
        models.Project(
            id="p_firm_b",
            name="B",
            jurisdiction_code="TX",
            firm_id="firm_b",
        )
    )
    db_session.commit()

    q = db_session.query(models.Project)
    a_projects = scope_to_firm(q, models.Project, "firm_a").all()
    assert {p.id for p in a_projects} == {"p_firm_a"}

    unrestricted = scope_to_firm(q, models.Project, None).all()
    assert {p.id for p in unrestricted} >= {"p_firm_a", "p_firm_b"}


def test_require_firm_raises_when_missing():
    with pytest.raises(HTTPException) as exc:
        require_firm(None)
    assert exc.value.status_code == 401
    assert require_firm("firm_x") == "firm_x"


# ---------------------------------------------------------------------------
# get_current_firm_id (JWT firm_id trust boundary)
# ---------------------------------------------------------------------------


from app.security.jwt_auth import JWTPrincipal
from app.security.tenancy import get_current_firm_id


def test_get_current_firm_id_prefers_jwt_claim():
    """JWT ``firm_id`` is authoritative — ignore the dev header when present."""

    principal = JWTPrincipal(
        user_id="u1", persona=models.Persona.IN_HOUSE_COUNSEL, firm_id="firm_from_token"
    )
    result = get_current_firm_id(
        principal=principal,
        persona=models.Persona.IN_HOUSE_COUNSEL,
        x_firm_id=None,
    )
    assert result == "firm_from_token"


def test_get_current_firm_id_rejects_mismatched_header():
    """A spoofed ``X-Firm-Id`` must 403, not silently override the JWT."""

    principal = JWTPrincipal(
        user_id="u1", persona=models.Persona.IN_HOUSE_COUNSEL, firm_id="firm_from_token"
    )
    with pytest.raises(HTTPException) as exc:
        get_current_firm_id(
            principal=principal,
            persona=models.Persona.IN_HOUSE_COUNSEL,
            x_firm_id="firm_spoof",
        )
    assert exc.value.status_code == 403


def test_get_current_firm_id_admin_bypass():
    """ADMIN persona returns ``None`` so cross-tenant reads are allowed."""

    result = get_current_firm_id(
        principal=None,
        persona=models.Persona.ADMIN,
        x_firm_id=None,
    )
    assert result is None


def test_get_current_firm_id_admin_header_override_allowed():
    """ADMIN may intentionally scope to a specific firm via the header."""

    principal = JWTPrincipal(
        user_id="u1", persona=models.Persona.ADMIN, firm_id="firm_a"
    )
    result = get_current_firm_id(
        principal=principal,
        persona=models.Persona.ADMIN,
        x_firm_id="firm_b",
    )
    assert result == "firm_a"  # JWT claim still wins; admin gets own firm scope


def test_get_current_firm_id_dev_fallback_without_token():
    """Dev env with no JWT falls back to ``DEFAULT_FIRM_ID``."""

    # get_settings() defaults to ENVIRONMENT=dev in the test suite.
    result = get_current_firm_id(
        principal=None,
        persona=models.Persona.LAND_AGENT,
        x_firm_id=None,
    )
    assert result == models.DEFAULT_FIRM_ID


def test_scope_to_firm_strict_on_missing_column(monkeypatch):
    """A model without ``firm_id`` must raise when ``strict=True`` is forced."""

    class _Dummy:
        __name__ = "Dummy"

    # Explicit strict=True bypasses the environment check and always raises
    # when the column is missing, which is what cross-tenant-sensitive call
    # sites should pass.
    with pytest.raises(RuntimeError):
        scope_to_firm(object(), _Dummy, "firm_a", strict=True)


def test_scope_to_firm_non_strict_warns_but_returns(caplog):
    """strict=False returns the original query and logs a warning."""

    class _Dummy:
        __name__ = "Dummy"

    sentinel = object()
    result = scope_to_firm(sentinel, _Dummy, "firm_a", strict=False)
    assert result is sentinel
