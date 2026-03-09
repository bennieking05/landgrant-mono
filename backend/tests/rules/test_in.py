"""
Tests for Indiana eminent domain rules.
"""

import pytest
from typing import Any

from app.services.rules_engine import (
    load_rule,
    evaluate_rules,
    get_jurisdiction_config,
    get_notice_requirements,
    is_quick_take_available,
    is_economic_development_banned,
)


class TestIndianaRulesLoading:
    """Tests for loading IN rules."""

    def test_in_rules_load(self):
        """IN rules should load successfully."""
        rules = load_rule("IN")
        assert rules is not None
        assert rules.get("jurisdiction") == "IN"

    def test_in_extends_base(self):
        """IN rules should extend base."""
        rules = load_rule("IN")
        assert rules.get("extends") == "base"

    def test_in_has_deadline_chains(self):
        """IN rules should have deadline chains."""
        rules = load_rule("IN")
        chains = rules.get("deadline_chains", [])
        assert len(chains) > 0
        
        # Check for key anchor events
        anchors = [c.get("anchor_event") for c in chains]
        assert "offer_served" in anchors
        assert "complaint_filed" in anchors
        assert "notice_served" in anchors


class TestIndianaJurisdictionConfig:
    """Tests for IN jurisdiction configuration."""

    def test_in_config(self):
        """Should return valid IN config."""
        config = get_jurisdiction_config("IN")
        assert config.jurisdiction == "IN"

    def test_in_requires_resolution(self):
        """IN should require resolution from local body."""
        config = get_jurisdiction_config("IN")
        assert config.initiation.get("resolution_required") is True

    def test_in_has_quick_take(self):
        """IN should have quick-take available."""
        assert is_quick_take_available("IN") is True

    def test_in_economic_development_banned(self):
        """IN should ban economic development takings."""
        assert is_economic_development_banned("IN") is True


class TestIndianaDeadlineChains:
    """Tests for IN deadline chain structure."""

    def test_in_offer_served_chain(self):
        """Offer served chain should have correct deadlines."""
        rules = load_rule("IN")
        chains = rules.get("deadline_chains", [])
        
        offer_chain = next(
            (c for c in chains if c.get("anchor_event") == "offer_served"),
            None
        )
        assert offer_chain is not None
        
        deadlines = offer_chain.get("deadlines", [])
        deadline_ids = [d.get("id") for d in deadlines]
        
        assert "earliest_complaint_filing" in deadline_ids
        assert "owner_response_window" in deadline_ids

    def test_in_30_day_response_window(self):
        """Owner should have 30 days to respond to offer."""
        rules = load_rule("IN")
        chains = rules.get("deadline_chains", [])
        
        offer_chain = next(
            (c for c in chains if c.get("anchor_event") == "offer_served"),
            None
        )
        
        response_deadline = next(
            (d for d in offer_chain.get("deadlines", []) 
             if d.get("id") == "owner_response_window"),
            None
        )
        
        assert response_deadline is not None
        assert response_deadline.get("offset_days") == 30

    def test_in_objection_deadline_extendable(self):
        """Defendant objection deadline should be extendable."""
        rules = load_rule("IN")
        chains = rules.get("deadline_chains", [])
        
        notice_chain = next(
            (c for c in chains if c.get("anchor_event") == "notice_served"),
            None
        )
        
        obj_deadline = next(
            (d for d in notice_chain.get("deadlines", [])
             if d.get("id") == "defendant_objection_deadline"),
            None
        )
        
        assert obj_deadline is not None
        assert obj_deadline.get("extendable") is True
        assert obj_deadline.get("max_extension_days") == 30


class TestIndianaTriggerEvaluation:
    """Tests for evaluating IN triggers."""

    def test_in_offer_served_trigger(self, base_case_payload: dict[str, Any]):
        """Offer served trigger should fire when offer is served in IN."""
        payload = base_case_payload.copy()
        payload["case.jurisdiction"] = "IN"
        
        results = evaluate_rules("IN", payload)
        
        offer_trigger = next(
            (r for r in results if "offer_served" in r.rule_id),
            None
        )
        assert offer_trigger is not None
        assert offer_trigger.fired is True

    def test_in_offer_served_captures_evidence(self, base_case_payload: dict[str, Any]):
        """Offer served trigger should capture required evidence fields."""
        payload = base_case_payload.copy()
        payload["case.jurisdiction"] = "IN"
        
        results = evaluate_rules("IN", payload)
        
        offer_trigger = next(
            (r for r in results if "offer_served" in r.rule_id),
            None
        )
        
        assert offer_trigger is not None
        assert len(offer_trigger.evidence) > 0


class TestIndianaPaymentRules:
    """Tests for IN payment election rules."""

    def test_in_has_payment_rules(self):
        """IN should have payment election rules."""
        rules = load_rule("IN")
        payment_rules = rules.get("payment_rules", [])
        assert len(payment_rules) > 0

    def test_in_annual_payment_threshold(self):
        """Annual payment election should have $5,000 threshold."""
        rules = load_rule("IN")
        payment_rules = rules.get("payment_rules", [])
        
        annual_rule = next(
            (r for r in payment_rules if r.get("id") == "annual_payment_election"),
            None
        )
        
        assert annual_rule is not None
        assert annual_rule.get("threshold_amount") == 5000
        assert annual_rule.get("max_payment_years") == 20
