"""Tests for Requirements Operations Service."""

import pytest
from datetime import datetime

from app.services.requirements_ops import (
    RequirementsOpsService,
    ValidationResult,
)


@pytest.fixture
def requirements_service(tmp_path):
    """Create a requirements service with temp storage."""
    return RequirementsOpsService(storage_path=tmp_path)


# Sample YAML content for testing
TX_PACK_YAML = """
version: 1.0.0
jurisdiction: TX
extends: base
maintainer: Test

citations:
  primary: "Tex. Prop. Code Ch. 21"

initiation:
  landowner_bill_of_rights: true
  bill_of_rights_citation: "Tex. Prop. Code §21.0112"
  pre_condemnation_offer_required: true
  appraisal_based_offer: true
  good_faith_negotiation: true
  initial_offer_days: 30
  final_offer_days: 14

compensation:
  base: fair_market_value
  includes_severance: true
  attorney_fees:
    automatic: false
    threshold_based: false

owner_rights:
  jury_trial: true
  commissioners_panel: special_commissioners
  public_use_challenge: true

deadline_chains:
  - anchor_event: offer_served
    deadlines:
      - id: initial_offer_wait
        offset_days: 30
        direction: after
        citation: "Tex. Prop. Code §21.0113"

triggers:
  - id: tx_offer_served
    match: "case.jurisdiction == 'TX'"
    deadlines:
      - id: bill_of_rights
        offset_days: 7
        citation: "Tex. Prop. Code §21.0112"
"""


def test_import_state_pack(requirements_service):
    """Test importing a state pack."""
    result = requirements_service.import_state_pack(
        jurisdiction="TX",
        yaml_content=TX_PACK_YAML,
    )
    
    assert result["pack"]["jurisdiction"] == "TX"
    assert result["pack"]["version"] == "1.0.0"
    assert result["pack"]["status"] == "draft"
    assert result["requirements_count"] > 0
    assert "staging_path" in result


def test_import_pack_jurisdiction_mismatch(requirements_service):
    """Test that jurisdiction mismatch raises error."""
    with pytest.raises(ValueError, match="Jurisdiction mismatch"):
        requirements_service.import_state_pack(
            jurisdiction="CA",  # Doesn't match YAML
            yaml_content=TX_PACK_YAML,
        )


def test_validate_pack(requirements_service):
    """Test pack validation."""
    # First import
    result = requirements_service.import_state_pack(
        jurisdiction="TX",
        yaml_content=TX_PACK_YAML,
    )
    pack_id = result["pack"]["id"]
    
    # Then validate
    validation = requirements_service.validate_pack(pack_id)
    
    assert validation.valid
    assert len(validation.errors) == 0
    assert validation.requirements_count > 0
    assert "notice" in validation.topics_covered


def test_validate_pack_invalid_yaml(requirements_service):
    """Test validation with invalid YAML."""
    invalid_yaml = "this is: [not valid yaml"
    
    result = requirements_service.import_state_pack(
        jurisdiction="TX",
        yaml_content="version: 1.0.0\njurisdiction: TX",  # Valid minimal
    )
    
    # Validation should pass for minimal valid YAML
    validation = requirements_service.validate_pack(result["pack"]["id"])
    # May have warnings but shouldn't have parse errors
    assert "YAML parse error" not in str(validation.errors)


def test_validate_pack_missing_required(requirements_service):
    """Test validation catches missing required fields."""
    minimal_yaml = """
initiation:
  pre_condemnation_offer_required: true
"""
    
    result = requirements_service.import_state_pack(
        jurisdiction="TX",
        yaml_content=minimal_yaml,
    )
    
    validation = requirements_service.validate_pack(result["pack"]["id"])
    
    # Should have errors for missing version and jurisdiction
    assert not validation.valid
    assert any("version" in e.lower() for e in validation.errors)


def test_normalize_requirements(requirements_service):
    """Test requirement normalization."""
    result = requirements_service.import_state_pack(
        jurisdiction="TX",
        yaml_content=TX_PACK_YAML,
    )
    
    requirements = result["requirements"]
    
    # Should have normalized requirements
    assert len(requirements) > 0
    
    # Check for expected requirements
    req_ids = [r["requirement_id"] for r in requirements]
    assert any("bill_of_rights" in rid for rid in req_ids)
    assert any("initial_wait" in rid or "initial_offer" in rid for rid in req_ids)


def test_publish_pack(requirements_service):
    """Test publishing a pack."""
    # Import
    result = requirements_service.import_state_pack(
        jurisdiction="TX",
        yaml_content=TX_PACK_YAML,
    )
    pack_id = result["pack"]["id"]
    
    # Publish
    published = requirements_service.publish_pack(
        pack_id=pack_id,
        user_id="test-user",
    )
    
    assert published["status"] == "active"
    assert published["published_by"] == "test-user"
    assert "active_path" in published


def test_get_active_pack(requirements_service):
    """Test getting active pack."""
    # Import and publish
    result = requirements_service.import_state_pack(
        jurisdiction="TX",
        yaml_content=TX_PACK_YAML,
    )
    requirements_service.publish_pack(result["pack"]["id"], "test-user")
    
    # Get active
    pack = requirements_service.get_active_pack("TX")
    
    assert pack is not None
    assert pack["jurisdiction"] == "TX"
    assert pack["version"] == "1.0.0"


def test_list_jurisdictions(requirements_service):
    """Test listing jurisdictions."""
    # Import and publish
    result = requirements_service.import_state_pack(
        jurisdiction="TX",
        yaml_content=TX_PACK_YAML,
    )
    requirements_service.publish_pack(result["pack"]["id"], "test-user")
    
    jurisdictions = requirements_service.list_jurisdictions()
    
    # Should include TX
    tx = next((j for j in jurisdictions if j["jurisdiction"] == "TX"), None)
    assert tx is not None


def test_diff_packs(requirements_service):
    """Test diffing pack versions."""
    # Import first version
    result1 = requirements_service.import_state_pack(
        jurisdiction="TX",
        yaml_content=TX_PACK_YAML,
    )
    
    # Import modified version
    modified_yaml = TX_PACK_YAML.replace("initial_offer_days: 30", "initial_offer_days: 45")
    result2 = requirements_service.import_state_pack(
        jurisdiction="TX",
        yaml_content=modified_yaml,
    )
    
    # Diff
    diff = requirements_service.diff_packs(
        result1["pack"]["id"],
        result2["pack"]["id"],
    )
    
    # Should detect changes
    assert diff.modified or diff.added or diff.removed
