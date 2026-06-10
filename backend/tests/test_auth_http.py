"""Default-deny HTTP auth: anonymous requests must be rejected except allowlist."""

from __future__ import annotations

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_PUBLIC_METHOD_PATHS: set[tuple[str, str]] = {
    ("GET", "/healthz"),
    ("GET", "/health/live"),
    ("GET", "/readyz"),
    ("POST", "/auth/login"),
    ("POST", "/portal/verify"),
    ("POST", "/portal/verify/refresh"),
    ("POST", "/portal/logout"),
    ("POST", "/integrations/dockets"),
}


def _iter_api_routes():
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or set():
            if method in ("HEAD", "OPTIONS"):
                continue
            yield method, route.path


def test_healthz_anonymous_ok():
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json().get("status") == "ok"


def test_parcels_anonymous_401():
    assert client.get("/parcels").status_code == 401


def test_auth_me_anonymous_401():
    assert client.get("/auth/me").status_code == 401


def test_registered_http_routes_default_deny():
    """Every concrete HTTP route rejects anonymous callers except the public set."""

    failures: list[str] = []
    for method, path in _iter_api_routes():
        if "{" in path:
            continue
        key = (method, path)
        if key in _PUBLIC_METHOD_PATHS:
            continue
        if path.startswith("/docs") or path.startswith("/openapi.json") or path.startswith("/redoc"):
            continue
        if method == "GET":
            res = client.get(path)
        elif method == "POST":
            res = client.post(path, json={})
        elif method == "PUT":
            res = client.put(path, json={})
        elif method == "DELETE":
            res = client.delete(path)
        elif method == "PATCH":
            res = client.patch(path, json={})
        else:
            continue
        if res.status_code not in (401, 404, 405, 422, 400, 415):
            failures.append(f"{method} {path} -> {res.status_code}")
    assert not failures, "; ".join(failures[:20])
