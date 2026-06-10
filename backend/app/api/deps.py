import hashlib
import hmac
from collections.abc import Generator
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Persona, User
from app.security.jwt_auth import JWTPrincipal


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_principal(request: Request) -> JWTPrincipal:
    """Return the authenticated principal (set by auth middleware)."""

    principal = getattr(request.state, "principal", None)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return principal


def get_current_persona(
    principal: JWTPrincipal = Depends(get_current_principal),
) -> Persona:
    """Resolve the caller's persona from the validated JWT."""

    return principal.persona


def get_current_user(
    principal: JWTPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> User:
    """Return the persisted user when ``sub`` matches a row; else a synthetic stub."""

    row = db.get(User, principal.user_id)
    if row is not None:
        return row
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
