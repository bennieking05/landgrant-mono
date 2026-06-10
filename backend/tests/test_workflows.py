from fastapi.testclient import TestClient

from app.db.models import Persona
from app.main import app

from tests.jwt_helpers import auth_headers

client = TestClient(app)


def test_binder_export_requires_body():
    """Binder export returns 422 when called without the required project_id."""
    response = client.post(
        "/workflows/binder/export",
        headers=auth_headers(Persona.IN_HOUSE_COUNSEL, user_id="COUNSEL-001"),
    )
    assert response.status_code == 422


def test_binder_export_rejects_unauthorized_persona():
    """Binder export rejects personas without binder:approve permission."""
    response = client.post(
        "/workflows/binder/export",
        json={"project_id": "PRJ-001"},
        headers=auth_headers(
            Persona.LANDOWNER, user_id="portal:x", email="owner@example.com"
        ),
    )
    assert response.status_code == 403
