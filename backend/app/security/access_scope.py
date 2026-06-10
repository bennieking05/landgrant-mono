"""Parcel-level access grants for landowner and outside counsel personas."""

from __future__ import annotations

import logging
from typing import Optional, Set

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import models
from app.db.models import Persona
from app.security.jwt_auth import JWTPrincipal

logger = logging.getLogger(__name__)


def _normalized_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    return email.strip().lower()


def granted_parcel_ids(db: Session, principal: JWTPrincipal) -> Optional[Set[str]]:
    """Return parcel ids the principal may access, or ``None`` if not row-scoped.

    ``None`` means the caller is not restricted by parcel grants (internal roles).
    """

    if principal.persona == Persona.LANDOWNER:
        email = _normalized_email(principal.email)
        q = db.query(models.ParcelAccessGrant.parcel_id).filter(
            models.ParcelAccessGrant.scope_persona == Persona.LANDOWNER.value,
        )
        clauses = []
        if principal.user_id:
            clauses.append(models.ParcelAccessGrant.user_id == principal.user_id)
        if email:
            clauses.append(
                models.ParcelAccessGrant.grantee_email == email,
            )
        if not clauses:
            return set()
        q = q.filter(or_(*clauses))
        return {row[0] for row in q.all()}

    if principal.persona == Persona.OUTSIDE_COUNSEL:
        q = db.query(models.ParcelAccessGrant.parcel_id).filter(
            models.ParcelAccessGrant.scope_persona == Persona.OUTSIDE_COUNSEL.value,
        )
        clauses = []
        if principal.user_id:
            clauses.append(models.ParcelAccessGrant.user_id == principal.user_id)
        email = _normalized_email(principal.email)
        if email:
            clauses.append(models.ParcelAccessGrant.grantee_email == email)
        if not clauses:
            return set()
        q = q.filter(or_(*clauses))
        return {row[0] for row in q.all()}

    return None


def require_parcel_scope(
    db: Session, principal: JWTPrincipal, parcel_id: Optional[str]
) -> None:
    """Raise 403 when an explicit parcel is outside the grant set."""

    if not parcel_id:
        return
    allowed = granted_parcel_ids(db, principal)
    if allowed is None:
        return
    if parcel_id not in allowed:
        logger.info(
            "parcel scope denied persona=%s parcel_id=%s",
            principal.persona,
            parcel_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="parcel_access_denied",
        )


def filter_parcels_query(db: Session, principal: JWTPrincipal, query):
    """Apply IN-filter for landowner / outside counsel list queries."""

    allowed = granted_parcel_ids(db, principal)
    if allowed is None:
        return query
    if not allowed:
        return query.filter(False)
    return query.filter(models.Parcel.id.in_(list(allowed)))
