"""
Tests for California eminent domain rules.

California is unique for:
- Resolution of Necessity requirement with public hearing
- Business goodwill compensation
- Limited post-Kelo reform (Prop 99 - only protects owner-occupied homes)
"""

import pytest
from typing import Any

from app.services.rules_engine import (
    load_rule,
    evaluate_rules,
    get_jurisdiction_config,
    get_attorney_fee_rules,
    is_quick_take_available,
    is_economic_development_banned,
)


class TestCaliforniaRulesLoading:
    """Tests for loading CA rules."""

    def test_ca_rules_load(self):
        """CA rules should load successfully."""
        rules = load_rule("CA")
        assert rules is not None
        assert rules.get("jurisdiction") == "CA"

    def test_ca_extends_base(self):
        """CA rules should extend base."""
        rules = load_rule("CA")
        assert rules.get("extends") == "base"

    def test_ca_cites_ccp(self):
        """CA rules should cite Code of Civil Procedure."""
        rules = load_rule("CA")
        citations = rules.get("citations", {})
        assert "Cal. Code Civ. Proc." in citations.get("primary", "")


class TestCaliforniaResolutionOfNecessity:
    """Tests for CA's Resolution of Necessity requirement."""

    def test_ca_requires_resolution(self):
        """CA should require Resolution of Necessity."""
        config = get_jurisdiction_config("CA")
        assert config.initiation.get("resolution_required") is True

    def test_ca_resolution_type(self):
        """CA resolution should be 'resolution_of_necessity' type."""
        config = get_jurisdiction_config("CA")
        assert config.initiation.get("resolution_type") == "resolution_of_necessity"

    def test_ca_requires_public_hearing(self):
        """CA should require public hearing for resolution."""
        config = get_jurisdiction_config("CA")
        assert config.initiation.get("public_hearing_required") is True

    def test_ca_resolution_requires_supermajority(self):
        """CA resolution should require supermajority vote."""
        config = get_jurisdiction_config("CA")
        assert config.initiation.get("resolution_vote") == "supermajority"

    def test_ca_resolution_required_findings(self):
        """CA resolution should require 3 specific findings."""
        config = get_jurisdiction_config("CA")
        findings = config.initiation.get("resolution_findings_required", [])
        
        assert "public_use_necessary" in findings
        assert "project_planned_to_minimize_private_injury" in findings
        assert "property_necessary_for_project" in findings


class TestCaliforniaBusinessGoodwill:
    """Tests for CA's unique business goodwill compensation."""

    def test_ca_compensates_business_goodwill(self):
        """CA should compensate for loss of business goodwill."""
        config = get_jurisdiction_config("CA")
        assert config.compensation.get("business_goodwill") is True

    def test_ca_goodwill_has_requirements(self):
        """CA goodwill compensation should have requirements."""
        config = get_jurisdiction_config("CA")
        requirements = config.compensation.get("business_goodwill_requirements", [])
        
        assert len(requirements) > 0
        assert any("business_conducted_on_property" in str(r) for r in requirements)


class TestCaliforniaAttorneyFees:
    """Tests for CA attorney fee rules."""

    def test_ca_fees_not_automatic(self):
        """CA fees should not be automatic."""
        fees = get_attorney_fee_rules("CA")
        assert fees["automatic"] is False

    def test_ca_fees_threshold_based(self):
        """CA fees should be based on reasonableness test."""
        fees = get_attorney_fee_rules("CA")
        assert fees["threshold_based"] is True

    def test_ca_reasonableness_test(self):
        """CA should use reasonableness test for fees."""
        config = get_jurisdiction_config("CA")
        atty_fees = config.compensation.get("attorney_fees", {})
        assert atty_fees.get("reasonableness_test") is True


class TestCaliforniaPublicUse:
    """Tests for CA public use limitations."""

    def test_ca_limited_reform(self):
        """CA should have limited post-Kelo reform (Prop 99)."""
        config = get_jurisdiction_config("CA")
        
        # CA did NOT ban economic development broadly
        assert config.public_use.get("economic_development_banned") is False

    def test_ca_prop_99_protects_homes(self):
        """CA Prop 99 should protect owner-occupied homes only."""
        config = get_jurisdiction_config("CA")
        prop_99 = config.public_use.get("prop_99", {})
        
        assert prop_99.get("year") == 2008
        assert prop_99.get("protection") == "owner_occupied_single_family_residence"

    def test_ca_reform_scope_limited(self):
        """CA reform scope should be 'limited'."""
        config = get_jurisdiction_config("CA")
        assert config.public_use.get("reform_scope") == "limited"


class TestCaliforniaTriggerEvaluation:
    """Tests for evaluating CA triggers."""

    def test_ca_resolution_trigger(self, ca_business_payload: dict[str, Any]):
        """Resolution trigger should fire for public entity."""
        results = evaluate_rules("CA", ca_business_payload)
        
        resolution_trigger = next(
            (r for r in results if "resolution" in r.rule_id),
            None
        )
        assert resolution_trigger is not None
        assert resolution_trigger.fired is True

    def test_ca_business_goodwill_trigger(self, ca_business_payload: dict[str, Any]):
        """Business goodwill trigger should fire when business on property."""
        results = evaluate_rules("CA", ca_business_payload)
        
        goodwill_trigger = next(
            (r for r in results if "goodwill" in r.rule_id),
            None
        )
        assert goodwill_trigger is not None
        assert goodwill_trigger.fired is True
