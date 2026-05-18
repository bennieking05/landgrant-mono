"""Global pytest fixtures for the backend suite.

Historically the tests depended on FastAPI's ``lifespan`` to create the schema
for the configured ``DATABASE_URL``. ``TestClient(app)`` is **not** used as a
context manager in most tests, so the lifespan callback never fires and the
tables never exist when tests connect to a real Postgres instance. This
``conftest.py`` closes that gap by bootstrapping the schema once per test
session against whatever database is configured (falling back to an in-memory
SQLite when the configured Postgres is unreachable so CI can still collect
unit-style tests without external services).
"""

from __future__ import annotations

import os

# IMPORTANT: these defaults must be set before any ``app.*`` module gets
# imported. ``app.core.config`` is eagerly instantiated at import time by
# several services (e.g. ``rag_service.settings = get_settings()``) so a
# ``setdefault`` inside a fixture would be too late -- the value would
# already be locked in by the time the fixture runs.
os.environ.setdefault("ENVIRONMENT", "dev")
# Keep unit tests fully hermetic. When RAG is left on it will try to
# boot Vertex AI + ChromaDB on the first ``/rag/*`` call, which hits
# real Google auth and blows past pytest timeouts. Tests that actually
# exercise the RAG path can override this locally.
os.environ.setdefault("RAG_ENABLED", "false")

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_schema() -> None:
    """Ensure schema + seed data exist before any test runs.

    Runs once per session. Safe to invoke repeatedly: ``_bootstrap_dev_db`` is
    idempotent and only seeds demo rows when the Project table is empty.
    """

    from app.main import _bootstrap_dev_db

    try:
        _bootstrap_dev_db()
    except Exception:
        # ``_bootstrap_dev_db`` already swallows connection errors; this guard
        # just protects against any unexpected side effects so collection
        # still succeeds when the target database is offline.
        pass
