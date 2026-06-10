"""HTTP middleware that enforces JWT authentication (default deny)."""

from __future__ import annotations

from typing import Callable

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.security.jwt_auth import principal_from_token


def _exempt(method: str, path: str, settings: Settings) -> bool:
    if path == "/healthz" and method == "GET":
        return True
    if path == "/health/live" and method == "GET":
        return True
    if path == "/readyz" and method == "GET":
        return True
    if path == "/auth/login" and method == "POST":
        return True
    if path == "/portal/verify" and method == "POST":
        return True
    if path == "/portal/verify/refresh" and method == "POST":
        return True
    if path == "/portal/logout" and method == "POST":
        return True
    if path == "/integrations/dockets" and method == "POST":
        return True
    if settings.environment == "dev":
        if path in ("/docs", "/openapi.json", "/redoc") and method == "GET":
            return True
    return False


class AuthEnforcementMiddleware(BaseHTTPMiddleware):
    """Require ``Authorization: Bearer`` except on a small public allowlist."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()

        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path.rstrip("/") or "/"
        # Normalise trailing slash handling: compare both raw and stripped.
        raw_path = request.url.path

        if _exempt(request.method, raw_path, settings) or _exempt(
            request.method, path, settings
        ):
            auth = request.headers.get("authorization")
            if auth:
                try:
                    request.state.principal = principal_from_token(auth)
                except HTTPException as exc:
                    return JSONResponse(
                        {"detail": exc.detail},
                        status_code=exc.status_code,
                    )
            else:
                request.state.principal = None
            return await call_next(request)

        auth = request.headers.get("authorization")
        if not auth:
            return JSONResponse(
                {"detail": "Not authenticated"},
                status_code=401,
            )
        try:
            request.state.principal = principal_from_token(auth)
        except HTTPException as exc:
            return JSONResponse(
                {"detail": exc.detail},
                status_code=exc.status_code,
            )

        return await call_next(request)
