"""Firm-level tenancy helpers.

Phase 3.1: every tenant-scoped API should resolve the caller's firm via
:func:`get_current_firm_id` and pipe queries through
:func:`scope_to_firm` so even a mis-authorised persona can't enumerate
data from a sibling firm.

``ADMIN`` persona callers bypass the filter (returns ``None``) so the
platform team can still run cross-firm operations.  Every other persona
MUST carry a firm id; requests without one are rejected with 401.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Query, Session

from app.api.deps import get_current_persona
from app.core.config import get_settings
from app.db.models import DEFAULT_FIRM_ID, Persona
from app.security.jwt_auth import JWTPrincipal, principal_from_token

logger = logging.getLogger(__name__)


def _optional_principal(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> Optional[JWTPrincipal]:
    """Return the JWT principal if one is present, or ``None`` for dev calls.

    Distinct from :func:`get_current_principal` which raises 401 when there's
    no token. We need to allow ``get_current_firm_id`` to fall through to its
    dev fallback when the caller is using the ``X-Persona`` header path.
    """

    return principal_from_token(authorization)


def get_current_firm_id(
    principal: Optional[JWTPrincipal] = Depends(_optional_principal),
    persona: Persona = Depends(get_current_persona),
    x_firm_id: Optional[str] = Header(default=None, alias="X-Firm-Id"),
) -> Optional[str]:
    """Resolve the caller's firm id.

    Lookup order:

    1. ``firm_id`` claim on a validated JWT (authoritative). A mismatched
       ``X-Firm-Id`` header is rejected with 403 so a compromised browser
       session cannot spoof a sibling firm.
    2. Explicit ``X-Firm-Id`` header — only honoured in dev, because in
       every other environment the header carries no trust boundary.
    3. ``ADMIN`` persona → ``None`` (cross-tenant read bypass).
    4. Dev fallback → ``DEFAULT_FIRM_ID`` so local tests work out of the box.
    """

    settings = get_settings()

    # (1) JWT claim wins. If the caller also supplied an X-Firm-Id header that
    # disagrees with the claim, refuse the request — we never want a UI-side
    # value to override what the token was signed for.
    if principal is not None and principal.firm_id:
        if x_firm_id and x_firm_id != principal.firm_id and persona != Persona.ADMIN:
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

    # (2) Dev-only: trust the raw header so the Playwright suite / local tools
    # can still switch firms without minting JWTs.
    if x_firm_id and settings.environment == "dev":
        return x_firm_id

    # (3) ADMIN persona crosses tenants by design.
    if persona == Persona.ADMIN:
        return None

    # (4) Dev/test convenience: every request gets the default firm scope.
    if settings.environment == "dev":
        return DEFAULT_FIRM_ID

    # In non-dev, require a firm id explicitly. Callers wrap this in
    # ``require_firm`` to convert ``None`` to a 401, so returning ``None`` is
    # safe and lets ADMIN still bypass via the explicit check above.
    return None


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
