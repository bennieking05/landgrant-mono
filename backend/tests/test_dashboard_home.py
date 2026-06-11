from fastapi.testclient import TestClient

from app.db.models import Persona
from app.main import app

from tests.jwt_helpers import auth_headers

client = TestClient(app)

_LANDOWNER = auth_headers(Persona.LANDOWNER, email="owner@example.com")
_AGENT = auth_headers(Persona.LAND_AGENT, user_id="AGENT-DASH")


def test_dashboard_landowner_empty():
    r = client.get("/dashboard/home", headers=_LANDOWNER)
    assert r.status_code == 200
    body = r.json()
    assert body["sample_size"] == 0
    assert body["pending_offers_count"] == 0


def test_dashboard_agent_shape():
    r = client.get("/dashboard/home", headers=_AGENT)
    assert r.status_code == 200
    body = r.json()
    assert "parcels_by_stage" in body
    assert "pending_offers_count" in body
    assert "litigation_rate_insufficient_data" in body
    assert isinstance(body["parcels_by_stage"], dict)
