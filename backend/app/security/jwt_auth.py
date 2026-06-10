"""JWT encoding/decoding for API authentication (Phase 3.3+).

Tokens carry ``sub``, ``email``, ``firm_id``, ``persona``, and optional
``roles`` / ``permissions`` claims. Legacy JWTs may still use ``persona=admin``;
those are normalized to :class:`Persona.PLATFORM_ADMIN`.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

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
    roles: tuple[str, ...] = field(default_factory=tuple)
    permissions: tuple[str, ...] = field(default_factory=tuple)


def _persona_from_claim(raw: str) -> Persona:
    if raw == "admin":
        return Persona.PLATFORM_ADMIN
    try:
        return Persona(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has unknown persona",
        ) from exc


def _decode(token: str) -> dict[str, Any]:
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
    persona = _persona_from_claim(str(persona_raw))

    user_id = (
        claims.get("sub") or claims.get("user_id") or claims.get("uid") or "jwt-user"
    )
    roles = claims.get("roles") or []
    perms = claims.get("permissions") or []
    if isinstance(roles, str):
        roles = [roles]
    if isinstance(perms, str):
        perms = [perms]

    return JWTPrincipal(
        user_id=str(user_id),
        persona=persona,
        firm_id=claims.get("firm_id"),
        email=claims.get("email"),
        roles=tuple(str(r) for r in roles),
        permissions=tuple(str(p) for p in perms),
    )


def create_access_token(
    *,
    user_id: str,
    persona: Persona,
    email: Optional[str] = None,
    firm_id: Optional[str] = None,
    roles: Optional[list[str]] = None,
    permissions: Optional[list[str]] = None,
    expires_in_seconds: int = 8 * 3600,
) -> str:
    """Mint a signed JWT suitable for ``Authorization: Bearer``."""

    from jose import jwt  # type: ignore

    settings = get_settings()
    now = int(time.time())
    persona_claim = (
        Persona.PLATFORM_ADMIN.value
        if persona == Persona.ADMIN
        else persona.value
    )
    payload: dict[str, Any] = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": user_id,
        "persona": persona_claim,
        "iat": now,
        "nbf": now - 1,
        "exp": now + int(expires_in_seconds),
    }
    if email:
        payload["email"] = email
    if firm_id is not None:
        payload["firm_id"] = firm_id
    if roles:
        payload["roles"] = roles
    if permissions:
        payload["permissions"] = permissions

    return jwt.encode(
        payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
