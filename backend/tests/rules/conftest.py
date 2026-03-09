"""
Shared fixtures for rules tests.
"""

import pytest
from pathlib import Path
from typing import Any

# Root directory for rules
RULES_DIR = Path(__file__).resolve().parents[3] / "rules"


@pytest.fixture
def rules_dir() -> Path:
    """Path to rules directory."""
    return RULES_DIR


@pytest.fixture
def base_case_payload() -> dict[str, Any]:
    """Base payload for testing trigger evaluation."""
    return {
        "parcel.assessed_value": 100000,
        "parcel.pin": "12-34-56-789",
        "parcel.owner_occupied": True,
        "parcel.principal_residence": True,
        "parcel.family_ownership_years": 10,
        "case.jurisdiction": "TX",
        "case.dispute_level": "LOW",
        "owner.name": "John Smith",
        "offer.total_amount": 100000,
        "offer.appraisal_date": "2025-01-15",
        "events.offer_served": "2025-01-20",
        "appraisal.value": 100000,
        "appraisal.date": "2025-01-15",
    }


@pytest.fixture
def high_value_payload(base_case_payload: dict[str, Any]) -> dict[str, Any]:
    """Payload with high parcel value that should trigger valuation thresholds."""
    payload = base_case_payload.copy()
    payload["parcel.assessed_value"] = 500000
    return payload


@pytest.fixture
def disputed_payload(base_case_payload: dict[str, Any]) -> dict[str, Any]:
    """Payload with HIGH dispute level."""
    payload = base_case_payload.copy()
    payload["case.dispute_level"] = "HIGH"
    return payload


@pytest.fixture
def mi_owner_occupied_payload() -> dict[str, Any]:
    """Payload for Michigan owner-occupied residence (125% multiplier)."""
    return {
        "parcel.assessed_value": 200000,
        "parcel.pin": "MI-12-34-56",
        "parcel.owner_occupied": True,
        "parcel.principal_residence": True,
        "parcel.family_ownership_years": 5,
        "case.jurisdiction": "MI",
        "owner.name": "Jane Doe",
        "offer.total_amount": 200000,
        "events.offer_served": "2025-01-20",
        "appraisal.value": 200000,
    }


@pytest.fixture
def mo_heritage_payload() -> dict[str, Any]:
    """Payload for Missouri heritage value (50+ years family ownership = 150%)."""
    return {
        "parcel.assessed_value": 150000,
        "parcel.pin": "MO-12-34-56",
        "parcel.owner_occupied": True,
        "parcel.principal_residence": True,
        "parcel.family_ownership_years": 55,
        "case.jurisdiction": "MO",
        "owner.name": "Family Farm Owner",
        "offer.total_amount": 150000,
        "events.offer_served": "2025-01-20",
        "events.notice_of_intent_served": "2024-11-15",
        "appraisal.value": 150000,
    }


@pytest.fixture
def mo_homestead_payload() -> dict[str, Any]:
    """Payload for Missouri homestead value (owner-occupied, <50 years = 125%)."""
    return {
        "parcel.assessed_value": 150000,
        "parcel.pin": "MO-12-34-56",
        "parcel.owner_occupied": True,
        "parcel.principal_residence": True,
        "parcel.family_ownership_years": 20,
        "case.jurisdiction": "MO",
        "owner.name": "Homestead Owner",
        "offer.total_amount": 150000,
        "events.offer_served": "2025-01-20",
        "appraisal.value": 150000,
    }


@pytest.fixture
def ca_business_payload() -> dict[str, Any]:
    """Payload for California with business on property (goodwill compensation)."""
    return {
        "parcel.assessed_value": 300000,
        "parcel.pin": "CA-123-456-789",
        "parcel.has_business": True,
        "case.jurisdiction": "CA",
        "project.public_entity": True,
        "owner.name": "Business Owner",
        "business.name": "Local Shop",
        "business.years_at_location": 10,
        "offer.total_amount": 300000,
        "events.offer_served": "2025-01-20",
        "resolution.hearing_date": "2025-02-15",
        "appraisal.value": 300000,
    }


@pytest.fixture
def fl_presuit_payload() -> dict[str, Any]:
    """Payload for Florida presuit negotiation."""
    return {
        "parcel.assessed_value": 250000,
        "parcel.pin": "FL-12-34-56-789",
        "case.jurisdiction": "FL",
        "owner.name": "Florida Owner",
        "offer.total_amount": 250000,
        "events.offer_served": "2025-01-10",
        "events.offer_rejected": "2025-01-25",
        "negotiation.attempts": 3,
        "appraisal.value": 250000,
    }
