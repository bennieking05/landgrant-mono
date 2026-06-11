"""Log mutating HTTP requests to the tamper-evident ``audit_events`` chain."""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

from app.db.session import SessionLocal
from app.services.audit_chain import append_audit_event

logger = logging.getLogger(__name__)


def _should_audit(method: str, path: str, status_code: int) -> bool:
    if method not in ("POST", "PUT", "PATCH", "DELETE"):
        return False
    if status_code >= 400:
        return False
    if path.startswith("/docs") or path in ("/openapi.json", "/redoc"):
        return False
    if path.startswith("/health") or path in ("/healthz", "/readyz"):
        return False
    if path.startswith("/auth/"):
        return False
    if path.startswith("/portal/verify"):
        return False
    if path.startswith("/integrations/dockets"):
        return False
    return True


class MutationAuditMiddleware(BaseHTTPMiddleware):
    """Append a hash-chained audit row for successful mutating API calls."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        raw_path = request.url.path
        if not _should_audit(request.method, raw_path, response.status_code):
            return response
        if isinstance(response, StreamingResponse):
            return response

        principal = getattr(request.state, "principal", None)
        if principal is None:
            return response

        db = SessionLocal()
        try:
            append_audit_event(
                db,
                action=f"http.{request.method.lower()}",
                resource=raw_path,
                user_id=principal.user_id,
                actor_persona=principal.persona,
                firm_id=principal.firm_id,
                payload={
                    "path": raw_path,
                    "query": request.url.query or None,
                    "status_code": response.status_code,
                },
            )
        except Exception:
            logger.exception("mutation_audit_failed path=%s", raw_path)
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            db.close()
        return response
