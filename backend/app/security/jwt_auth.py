"""JWT decoding for persona-derived auth (Phase 3.3).

In dev we still honour the ``X-Persona`` header (see ``Settings`` flag) so
the Playwright suite can keep switching personas without a full login.  In
any other environment we require a Bearer token whose claims name the
persona; the header, if present, is ignored.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.db.models import Persona

logger = logging.getLogger(__name__)


@dataclass
class JWTPrincipal:
    user_id: str
    persona: Persona
    firm_id: Optional[str] = None
    email: Optional[str] = None


def _decode(token: str) -> dict:
    settings = get_settings()
    try:
        from jose import jwt  # type: ignore
    except Exception as exc:  # pragma: no cover - dep failure path
        logger.error("python-jose is not installed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT library not installed",
        )

    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"leeway": settings.jwt_leeway_seconds},
        )
    except Exception as exc:
        logger.warning("JWT decode failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


def principal_from_token(authorization: Optional[str]) -> Optional[JWTPrincipal]:
    """Return the principal carried by a Bearer token, or ``None`` if absent.

    Raises 401 when the header is malformed or the JWT fails validation.
    """

    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be a Bearer token",
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty Bearer token",
        )

    claims = _decode(token)
    persona_raw = claims.get("persona") or claims.get("role")
    if not persona_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing persona claim",
        )
    try:
        persona = Persona(persona_raw)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has unknown persona",
        )

    user_id = (
        claims.get("sub") or claims.get("user_id") or claims.get("uid") or "jwt-user"
    )
    return JWTPrincipal(
        user_id=str(user_id),
        persona=persona,
        firm_id=claims.get("firm_id"),
        email=claims.get("email"),
    )
