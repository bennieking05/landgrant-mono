"""Mint short-lived JWTs for pytest / local tooling."""

from __future__ import annotations

import time
from typing import Optional

from jose import jwt

from app.core.config import get_settings
from app.db.models import Persona


def issue_test_token(
    *,
    persona: Persona = Persona.LAND_AGENT,
    user_id: str = "u-test",
    firm_id: Optional[str] = "firm_default",
    email: Optional[str] = None,
    expires_in: int = 3600,
) -> str:
    settings = get_settings()
    now = int(time.time())
    persona_claim = (
        Persona.PLATFORM_ADMIN.value
        if persona == Persona.ADMIN
        else persona.value
    )
    payload: dict = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": user_id,
        "persona": persona_claim,
        "iat": now,
        "nbf": now - 1,
        "exp": now + expires_in,
    }
    if firm_id is not None:
        payload["firm_id"] = firm_id
    if email:
        payload["email"] = email
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def auth_headers(
    *,
    persona: Persona = Persona.LAND_AGENT,
    user_id: str = "u-test",
    firm_id: Optional[str] = "firm_default",
    email: Optional[str] = None,
) -> dict[str, str]:
    tok = issue_test_token(
        persona=persona, user_id=user_id, firm_id=firm_id, email=email
    )
    return {"Authorization": f"Bearer {tok}"}
