"""
Tests for base rules and rules engine functionality.
"""

import pytest
from pathlib import Path

from app.services.rules_engine import (
    load_base_rules,
    load_rule,
    _deep_merge,
    list_available_jurisdictions,
    validate_rules_file,
)


class TestBaseRules:
    """Tests for base.yaml rules file."""

    def test_base_rules_loads(self, rules_dir: Path):
        """Base rules file should load successfully."""
        base = load_base_rules()
        assert base is not None
        assert base.get("type") == "base"
        assert base.get("version") == "1.0.0"

    def test_base_has_anchor_events(self):
        """Base rules should define anchor events."""
        base = load_base_rules()
        anchor_events = base.get("anchor_events", [])
        assert len(anchor_events) > 0
        
        event_ids = [e.get("id") for e in anchor_events]
        assert "offer_served" in event_ids
        assert "complaint_filed" in event_ids

    def test_base_has_compensation_defaults(self):
        """Base rules should define compensation defaults."""
        base = load_base_rules()
        comp = base.get("compensation_defaults", {})
        
        assert comp.get("fair_market_value") is True
        assert comp.get("severance_damages") is True

    def test_base_has_notice_defaults(self):
        """Base rules should define notice defaults."""
        base = load_base_rules()
        notice = base.get("notice_defaults", {})
        
        assert "offer_notice_days" in notice
        assert "final_offer_notice_days" in notice


class TestDeepMerge:
    """Tests for the _deep_merge function."""

    def test_merge_simple_override(self):
        """Simple values should be overridden."""
        base = {"a": 1, "b": 2}
        override = {"b": 3}
        result = _deep_merge(base, override)
        
        assert result["a"] == 1
        assert result["b"] == 3

    def test_merge_nested_dicts(self):
        """Nested dicts should be recursively merged."""
        base = {
            "compensation": {
                "fair_market_value": True,
                "severance_damages": True,
            }
        }
        override = {
            "compensation": {
                "business_goodwill": True,
            }
        }
        result = _deep_merge(base, override)
        
        assert result["compensation"]["fair_market_value"] is True
        assert result["compensation"]["severance_damages"] is True
        assert result["compensation"]["business_goodwill"] is True

    def test_merge_adds_new_keys(self):
        """New keys from override should be added."""
        base = {"a": 1}
        override = {"b": 2}
        result = _deep_merge(base, override)
        
        assert result["a"] == 1
        assert result["b"] == 2

    def test_merge_preserves_original(self):
        """Original dicts should not be modified."""
        base = {"a": {"x": 1}}
        override = {"a": {"y": 2}}
        result = _deep_merge(base, override)
        
        assert "y" not in base["a"]
        assert result["a"]["x"] == 1
        assert result["a"]["y"] == 2


class TestListJurisdictions:
    """Tests for listing available jurisdictions."""

    def test_list_includes_priority_states(self):
        """Should list priority states that have rules files."""
        jurisdictions = list_available_jurisdictions()
        
        assert "TX" in jurisdictions
        assert "IN" in jurisdictions
        assert "FL" in jurisdictions
        assert "CA" in jurisdictions
        assert "MI" in jurisdictions
        assert "MO" in jurisdictions

    def test_list_excludes_base(self):
        """Should not include 'base' in jurisdictions list."""
        jurisdictions = list_available_jurisdictions()
        assert "BASE" not in jurisdictions
        assert "base" not in jurisdictions


class TestValidateRulesFile:
    """Tests for rules file validation."""

    def test_validate_tx_rules(self):
        """TX rules should validate without errors."""
        errors = validate_rules_file("TX")
        assert len(errors) == 0

    def test_validate_in_rules(self):
        """IN rules should validate without errors."""
        errors = validate_rules_file("IN")
        assert len(errors) == 0

    def test_validate_nonexistent_state(self):
        """Should return error for nonexistent state."""
        errors = validate_rules_file("XX")
        assert len(errors) > 0
        assert "not found" in errors[0].lower()
