from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_binder_export_requires_body():
    """Binder export returns 422 when called without the required project_id."""
    response = client.post(
        "/workflows/binder/export", headers={"X-Persona": "in_house_counsel"}
    )
    assert response.status_code == 422


def test_binder_export_rejects_unauthorized_persona():
    """Binder export rejects personas without binder:approve permission."""
    response = client.post(
        "/workflows/binder/export",
        json={"project_id": "PRJ-001"},
        headers={"X-Persona": "landowner"},
    )
    assert response.status_code == 403
