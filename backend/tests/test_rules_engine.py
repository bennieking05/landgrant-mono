from app.services.rules_engine import evaluate_rules


def test_rules_engine_fires_for_high_value(tmp_path, monkeypatch):
    payload = {
        "parcel.assessed_value": 300000,
        "case.dispute_level": "HIGH",
        "appraisal.summary": "",
        "comms.last_contact_at": "2025-01-01T00:00:00Z",
    }
    results = evaluate_rules("tx", payload)
    assert any(result.fired for result in results)
