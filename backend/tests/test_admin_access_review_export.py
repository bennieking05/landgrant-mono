"""Access review export (SOC2 evidence)."""

from fastapi.testclient import TestClient

from app.main import app
from app.db.models import Persona
from tests.jwt_helpers import auth_headers

client = TestClient(app)


def test_access_review_export_csv_forbidden_for_land_agent():
    r = client.get(
        "/admin/access-review/export?fmt=csv",
        headers=auth_headers(Persona.LAND_AGENT),
    )
    assert r.status_code == 403


def test_access_review_export_csv_ok_for_platform_admin():
    r = client.get(
        "/admin/access-review/export?fmt=csv",
        headers=auth_headers(Persona.PLATFORM_ADMIN),
    )
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    body = r.text
    assert "email" in body.lower() or "id" in body


def test_access_review_export_json_ok():
    r = client.get(
        "/admin/access-review/export?fmt=json",
        headers=auth_headers(Persona.PLATFORM_ADMIN),
    )
    assert r.status_code == 200
    data = r.json()
    assert "users" in data
    assert "count" in data
