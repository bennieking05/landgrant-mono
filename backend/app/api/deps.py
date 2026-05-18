import hashlib
import hmac
import logging
from collections.abc import Generator
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.db.models import Persona, User
from app.security.jwt_auth import JWTPrincipal, principal_from_token

logger = logging.getLogger(__name__)

_settings = get_settings()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _resolve_principal(authorization: Optional[str]) -> Optional[JWTPrincipal]:
    """Resolve the principal from an Authorization header.

    Returns ``None`` when no header is present; raises 401 for malformed or
    invalid tokens.  Non-dev environments require a token, so callers should
    check for ``None`` themselves.
    """

    return principal_from_token(authorization)


def get_current_persona(
    x_persona: Optional[str] = Header(default=None, alias="X-Persona"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> Persona:
    """Resolve the caller's persona.

    Resolution order:
    1. JWT persona claim (required outside of dev).
    2. ``X-Persona`` header (only honoured when ``allow_persona_header`` is
       set, which we leave on in dev and turn off in prod).
    """

    principal = _resolve_principal(authorization)
    if principal is not None:
        return principal.persona

    if not _settings.allow_persona_header or _settings.environment != "dev":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization Bearer token with persona claim required",
        )

    if not x_persona:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Persona header required",
        )
    try:
        return Persona(x_persona)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid persona header",
        ) from exc


def get_current_principal(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    x_persona: Optional[str] = Header(default=None, alias="X-Persona"),
) -> JWTPrincipal:
    """Return the full principal (persona + user/firm) for the request."""

    principal = _resolve_principal(authorization)
    if principal is not None:
        return principal

    if not _settings.allow_persona_header or _settings.environment != "dev":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization Bearer token required",
        )

    if not x_persona:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Persona header required",
        )
    try:
        persona = Persona(x_persona)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid persona header",
        ) from exc
    return JWTPrincipal(user_id="dev-user", persona=persona)


def get_current_user(
    principal: "JWTPrincipal" = Depends(get_current_principal),
) -> User:
    """Return a lightweight User record derived from the current principal.

    The actual DB lookup happens in route handlers that need it; this helper
    is used by handlers that only care about id/email/persona.
    """

    return User(
        id=principal.user_id,
        email=principal.email or f"{principal.user_id}@landgrant.local",
        persona=principal.persona,
        full_name=principal.email or principal.user_id,
    )


def verify_webhook_signature(
    payload_body: bytes,
    signature_header: Optional[str],
    secret: str,
) -> bool:
    """Verify HMAC-SHA256 webhook signature. Returns False if unverifiable."""
    if not signature_header or not secret:
        return False
    expected = hmac.new(secret.encode(), payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)
