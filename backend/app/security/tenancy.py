"""Firm-level tenancy helpers.

Phase 3.1: every tenant-scoped API should resolve the caller's firm via
:func:`get_current_firm_id` and pipe queries through
:func:`scope_to_firm` so even a mis-authorised persona can't enumerate
data from a sibling firm.

``PLATFORM_ADMIN`` (and legacy ``ADMIN``) callers bypass the filter
(returns ``None``) so the platform team can still run cross-firm operations.
Every other persona MUST carry a firm id; requests without one are rejected
with 401.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Query, Session

from app.api.deps import get_current_persona
from app.core.config import get_settings
from app.db.models import DEFAULT_FIRM_ID, Persona
from app.security.jwt_auth import JWTPrincipal

logger = logging.getLogger(__name__)


def _optional_principal(request: Request) -> Optional[JWTPrincipal]:
    """Return the JWT principal from middleware state, if any."""

    return getattr(request.state, "principal", None)


def resolve_firm_id(
    *,
    principal: Optional[JWTPrincipal],
    persona: Persona,
    x_firm_id: Optional[str],
) -> Optional[str]:
    """Pure resolver used by :func:`get_current_firm_id` and unit tests."""

    settings = get_settings()

    if principal is not None and principal.firm_id:
        if x_firm_id and x_firm_id != principal.firm_id and persona not in (
            Persona.ADMIN,
            Persona.PLATFORM_ADMIN,
        ):
            logger.warning(
                "X-Firm-Id %s overrides JWT firm_id %s - rejecting",
                x_firm_id,
                principal.firm_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="X-Firm-Id does not match token firm_id",
            )
        return principal.firm_id

    if x_firm_id and settings.environment == "dev":
        return x_firm_id

    if persona in (Persona.ADMIN, Persona.PLATFORM_ADMIN):
        return None

    if settings.environment == "dev":
        return DEFAULT_FIRM_ID

    return None


def get_current_firm_id(
    request: Request,
    persona: Persona = Depends(get_current_persona),
    x_firm_id: Optional[str] = Header(default=None, alias="X-Firm-Id"),
) -> Optional[str]:
    """Resolve the caller's firm id (see :func:`resolve_firm_id`)."""

    principal = _optional_principal(request)
    return resolve_firm_id(principal=principal, persona=persona, x_firm_id=x_firm_id)


def require_firm(firm_id: Optional[str]) -> str:
    """Raise 401 when ``firm_id`` is missing on a scoped endpoint."""

    if not firm_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="firm_id required for this resource",
        )
    return firm_id


def scope_to_firm(
    query: Query,
    model: Any,
    firm_id: Optional[str],
    *,
    strict: Optional[bool] = None,
) -> Query:
    """Apply ``firm_id`` filter to a SQLAlchemy ``Query``.

    ``firm_id=None`` is treated as the ADMIN bypass and returns the query
    unchanged. If the model has no ``firm_id`` column the function **warns**
    loudly (and in non-dev environments raises) so we can't accidentally ship
    a cross-tenant-leakable query after an incomplete migration. Callers that
    knowingly query un-scoped tables (lookup tables, rule packs, etc.) can
    silence the warning by passing ``strict=False``.
    """

    if firm_id is None:
        return query

    column = getattr(model, "firm_id", None)
    if column is not None:
        return query.filter(column == firm_id)

    model_name = getattr(model, "__name__", str(model))
    settings = get_settings()
    effective_strict = strict if strict is not None else (settings.environment != "dev")

    if effective_strict:
        raise RuntimeError(
            f"scope_to_firm called on {model_name} which has no firm_id column; "
            "refusing to return an un-scoped query in non-dev environment. "
            "Pass strict=False to opt out explicitly."
        )

    logger.warning(
        "scope_to_firm: %s has no firm_id column; returning un-scoped query. "
        "This path is OK for lookup/reference tables but risky for tenant data.",
        model_name,
    )
    return query


def backfill_firm_ids(
    db: Session,
    *,
    default_firm_id: str = DEFAULT_FIRM_ID,
    default_firm_name: str = "Default Firm",
) -> dict[str, int]:
    """Backfill ``firm_id`` on all tenant-scoped tables to the default firm.

    Idempotent: rows that already have a ``firm_id`` are left alone.  A
    :class:`~app.db.models.Firm` row with ``default_firm_id`` is created on
    first run.
    """

    from app.db import models

    created = 0
    if not db.get(models.Firm, default_firm_id):
        db.add(
            models.Firm(
                id=default_firm_id,
                name=default_firm_name,
                slug=default_firm_id,
                active=True,
            )
        )
        created = 1

    counts: dict[str, int] = {"firm_created": created}
    for model in (models.Project, models.User, models.Document):
        column = getattr(model, "firm_id", None)
        if column is None:
            continue
        updated = (
            db.query(model)
            .filter(column.is_(None))
            .update({"firm_id": default_firm_id}, synchronize_session=False)
        )
        counts[model.__tablename__] = updated

    db.commit()
    return counts
