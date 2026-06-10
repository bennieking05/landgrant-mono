"""Phase 3.3: prod secret validation + JWT-derived persona + rate limits."""

from __future__ import annotations

import time

import pytest
from fastapi import FastAPI

from app.core.config import Settings
from app.db.models import Persona


def _issue_token(
    settings: Settings,
    *,
    persona: Persona = Persona.LAND_AGENT,
    user_id: str = "u-1",
    firm_id: str = "firm_test",
    expires_in: int = 300,
) -> str:
    from jose import jwt

    now = int(time.time())
    payload = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": user_id,
        "persona": persona.value,
        "firm_id": firm_id,
        "iat": now,
        "nbf": now - 1,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def test_validate_prod_secrets_flags_dev_defaults():
    s = Settings(environment="prod")
    problems = s.validate_prod_secrets()
    assert any("jwt_secret" in p for p in problems)


def test_validate_prod_secrets_allows_dev_env():
    s = Settings(environment="dev")
    assert s.validate_prod_secrets() == []


def test_validate_prod_secrets_requires_long_secret():
    s = Settings(
        environment="prod",
        jwt_secret="short",
        session_secret="x" * 40,
        encryption_key="y" * 40,
    )
    assert any("32 characters" in p for p in s.validate_prod_secrets())


def test_validate_prod_secrets_passes_with_real_secrets():
    s = Settings(
        environment="prod",
        jwt_secret="a" * 40,
        session_secret="b" * 40,
        encryption_key="c" * 40,
    )
    assert s.validate_prod_secrets() == []


def test_principal_from_jwt_returns_persona(monkeypatch):
    from app.security.jwt_auth import principal_from_token

    settings = Settings(environment="dev")
    monkeypatch.setattr(
        "app.security.jwt_auth.get_settings", lambda: settings
    )
    token = _issue_token(settings, persona=Persona.IN_HOUSE_COUNSEL, firm_id="firm_a")
    principal = principal_from_token(f"Bearer {token}")
    assert principal is not None
    assert principal.persona == Persona.IN_HOUSE_COUNSEL
    assert principal.firm_id == "firm_a"
    assert principal.user_id == "u-1"


def test_principal_from_jwt_rejects_unknown_persona(monkeypatch):
    from jose import jwt
    from app.security.jwt_auth import principal_from_token
    from fastapi import HTTPException

    settings = Settings(environment="dev")
    monkeypatch.setattr(
        "app.security.jwt_auth.get_settings", lambda: settings
    )
    now = int(time.time())
    token = jwt.encode(
        {
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "sub": "u",
            "persona": "not_a_persona",
            "iat": now,
            "exp": now + 60,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(HTTPException) as exc:
        principal_from_token(f"Bearer {token}")
    assert exc.value.status_code == 401


def test_principal_from_jwt_ignores_missing_header(monkeypatch):
    from app.security.jwt_auth import principal_from_token

    settings = Settings(environment="dev")
    monkeypatch.setattr(
        "app.security.jwt_auth.get_settings", lambda: settings
    )
    assert principal_from_token(None) is None
    assert principal_from_token("") is None


def test_principal_from_jwt_rejects_malformed_bearer(monkeypatch):
    from app.security.jwt_auth import principal_from_token
    from fastapi import HTTPException

    settings = Settings(environment="dev")
    monkeypatch.setattr(
        "app.security.jwt_auth.get_settings", lambda: settings
    )
    with pytest.raises(HTTPException):
        principal_from_token("Basic xyz")


def test_get_current_principal_requires_middleware_principal():
    from starlette.requests import Request
    from fastapi import HTTPException

    from app.api.deps import get_current_principal

    req = Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "method": "GET",
            "path": "/test",
            "headers": [],
            "scheme": "http",
            "server": ("127.0.0.1", 8050),
            "client": ("127.0.0.1", 12345),
        }
    )
    with pytest.raises(HTTPException) as exc:
        get_current_principal(req)
    assert exc.value.status_code == 401


def test_get_current_principal_reads_request_state():
    from starlette.requests import Request

    from app.api.deps import get_current_principal
    from app.security.jwt_auth import JWTPrincipal

    req = Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "method": "GET",
            "path": "/test",
            "headers": [],
            "scheme": "http",
            "server": ("127.0.0.1", 8050),
            "client": ("127.0.0.1", 12345),
        }
    )
    req.state.principal = JWTPrincipal(user_id="u1", persona=Persona.LAND_AGENT)
    assert get_current_principal(req).persona == Persona.LAND_AGENT


def test_admin_jwt_claim_maps_to_platform_admin(monkeypatch):
    from app.security.jwt_auth import principal_from_token

    settings = Settings(environment="dev")
    monkeypatch.setattr("app.security.jwt_auth.get_settings", lambda: settings)
    token = _issue_token(settings, persona=Persona.ADMIN)
    principal = principal_from_token(f"Bearer {token}")
    assert principal.persona == Persona.PLATFORM_ADMIN


def test_rate_limit_middleware_returns_429_when_configured(monkeypatch):
    """Smoke test the slowapi wiring against a minimal FastAPI app."""

    slowapi = pytest.importorskip("slowapi")

    from slowapi import Limiter
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.util import get_remote_address
    from fastapi.testclient import TestClient

    limiter = Limiter(key_func=get_remote_address, default_limits=["2/minute"])
    app = FastAPI()
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 429
