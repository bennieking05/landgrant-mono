"""
Tests for Texas eminent domain rules.
"""

import pytest
from typing import Any

from app.services.rules_engine import (
    load_rule,
    evaluate_rules,
    get_jurisdiction_config,
    get_notice_requirements,
    get_attorney_fee_rules,
    is_quick_take_available,
    is_economic_development_banned,
)


class TestTexasRulesLoading:
    """Tests for loading TX rules."""

    def test_tx_rules_load(self):
        """TX rules should load successfully."""
        rules = load_rule("TX")
        assert rules is not None
        assert rules.get("jurisdiction") == "TX"

    def test_tx_extends_base(self):
        """TX rules should extend base."""
        rules = load_rule("TX")
        assert rules.get("extends") == "base"

    def test_tx_has_citations(self):
        """TX rules should have citations."""
        rules = load_rule("TX")
        citations = rules.get("citations", {})
        assert "Tex. Prop. Code" in citations.get("primary", "")


class TestTexasJurisdictionConfig:
    """Tests for TX jurisdiction configuration."""

    def test_tx_config(self):
        """Should return valid TX config."""
        config = get_jurisdiction_config("TX")
        assert config.jurisdiction == "TX"
        assert config.version == "1.0.0"

    def test_tx_initiation_requires_bill_of_rights(self):
        """TX should require Landowner Bill of Rights."""
        config = get_jurisdiction_config("TX")
        assert config.initiation.get("landowner_bill_of_rights") is True

    def test_tx_has_quick_take(self):
        """TX should have quick-take available."""
        assert is_quick_take_available("TX") is True

    def test_tx_economic_development_banned(self):
        """TX should ban economic development takings."""
        assert is_economic_development_banned("TX") is True


class TestTexasNoticeRequirements:
    """Tests for TX notice requirements."""

    def test_tx_notice_periods(self):
        """TX should have specific notice periods."""
        notice = get_notice_requirements("TX")
        
        assert notice["offer_notice_days"] == 30
        assert notice["final_offer_notice_days"] == 14
        assert notice["bill_of_rights_days"] == 7
        assert notice["landowner_bill_of_rights_required"] is True


class TestTexasAttorneyFees:
    """Tests for TX attorney fee rules."""

    def test_tx_fees_not_automatic(self):
        """TX should not automatically award attorney fees."""
        fees = get_attorney_fee_rules("TX")
        assert fees["automatic"] is False
        assert fees["threshold_based"] is False


class TestTexasTriggerEvaluation:
    """Tests for evaluating TX triggers."""

    def test_tx_offer_served_trigger(self, base_case_payload: dict[str, Any]):
        """Offer served trigger should fire when offer is served."""
        payload = base_case_payload.copy()
        payload["case.jurisdiction"] = "TX"
        
        results = evaluate_rules("TX", payload)
        
        # Find the offer_served trigger result
        offer_trigger = next(
            (r for r in results if "offer_served" in r.rule_id),
            None
        )
        assert offer_trigger is not None
        assert offer_trigger.fired is True

    def test_tx_valuation_threshold_low_value(self, base_case_payload: dict[str, Any]):
        """Valuation threshold should not fire for low value parcel."""
        payload = base_case_payload.copy()
        payload["case.jurisdiction"] = "TX"
        payload["parcel.assessed_value"] = 100000  # Below 250000 threshold
        payload["case.dispute_level"] = "LOW"
        
        results = evaluate_rules("TX", payload)
        
        threshold_trigger = next(
            (r for r in results if "valuation_threshold" in r.rule_id),
            None
        )
        if threshold_trigger:
            assert threshold_trigger.fired is False

    def test_tx_valuation_threshold_high_value(self, high_value_payload: dict[str, Any]):
        """Valuation threshold should fire for high value parcel."""
        payload = high_value_payload.copy()
        payload["case.jurisdiction"] = "TX"
        
        results = evaluate_rules("TX", payload)
        
        threshold_trigger = next(
            (r for r in results if "valuation_threshold" in r.rule_id),
            None
        )
        if threshold_trigger:
            assert threshold_trigger.fired is True

    def test_tx_high_dispute_triggers(self, disputed_payload: dict[str, Any]):
        """High dispute level should trigger valuation threshold."""
        payload = disputed_payload.copy()
        payload["case.jurisdiction"] = "TX"
        
        results = evaluate_rules("TX", payload)
        
        threshold_trigger = next(
            (r for r in results if "valuation_threshold" in r.rule_id),
            None
        )
        if threshold_trigger:
            assert threshold_trigger.fired is True
