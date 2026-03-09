from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_binder_export_endpoint():
    response = client.post("/workflows/binder/export", headers={"X-Persona": "in_house_counsel"})
    assert response.status_code == 200
    data = response.json()
    assert "bundle_id" in data
