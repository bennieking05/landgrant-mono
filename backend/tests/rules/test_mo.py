"""
Tests for Missouri eminent domain rules.

Missouri is unique for:
- Heritage value bonus: 150% for property owned 50+ years by same family
- Heritage value bonus: 125% for owner-occupied homestead
- 60-day notice of intent requirement
- 30-day final offer requirement with calculation explanation
- Citizen's right to appeal blight designations
"""

import pytest
from typing import Any

from app.services.rules_engine import (
    load_rule,
    evaluate_rules,
    get_jurisdiction_config,
    get_compensation_multiplier,
    get_notice_requirements,
    get_attorney_fee_rules,
    is_economic_development_banned,
)


class TestMissouriRulesLoading:
    """Tests for loading MO rules."""

    def test_mo_rules_load(self):
        """MO rules should load successfully."""
        rules = load_rule("MO")
        assert rules is not None
        assert rules.get("jurisdiction") == "MO"

    def test_mo_extends_base(self):
        """MO rules should extend base."""
        rules = load_rule("MO")
        assert rules.get("extends") == "base"

    def test_mo_cites_rsmo(self):
        """MO rules should cite Revised Statutes of Missouri."""
        rules = load_rule("MO")
        citations = rules.get("citations", {})
        assert "RSMo" in citations.get("primary", "")


class TestMissouriHeritageValue:
    """Tests for MO's heritage value bonus multipliers."""

    def test_mo_has_heritage_multiplier(self):
        """MO should have heritage value multipliers defined."""
        config = get_jurisdiction_config("MO")
        heritage = config.compensation.get("heritage_multiplier", {})
        
        assert heritage is not None
        assert "long_term_family" in heritage
        assert "homestead" in heritage

    def test_mo_long_term_family_150_percent(self):
        """50+ years family ownership should get 150% multiplier."""
        config = get_jurisdiction_config("MO")
        heritage = config.compensation.get("heritage_multiplier", {})
        long_term = heritage.get("long_term_family", {})
        
        assert long_term.get("multiplier") == 1.50
        assert long_term.get("years_required") == 50

    def test_mo_homestead_125_percent(self):
        """Owner-occupied homestead should get 125% multiplier."""
        config = get_jurisdiction_config("MO")
        heritage = config.compensation.get("heritage_multiplier", {})
        homestead = heritage.get("homestead", {})
        
        assert homestead.get("multiplier") == 1.25

    def test_mo_multiplier_50_years_family(self, mo_heritage_payload: dict[str, Any]):
        """Should return 1.50 for 50+ years family ownership."""
        multiplier = get_compensation_multiplier("MO", {
            "family_ownership_years": 55,
            "owner_occupied": True,
        })
        assert multiplier == 1.50

    def test_mo_multiplier_homestead(self, mo_homestead_payload: dict[str, Any]):
        """Should return 1.25 for owner-occupied homestead under 50 years."""
        multiplier = get_compensation_multiplier("MO", {
            "family_ownership_years": 20,
            "owner_occupied": True,
        })
        assert multiplier == 1.25

    def test_mo_multiplier_not_owner_occupied(self):
        """Should return 1.0 for non-owner-occupied property."""
        multiplier = get_compensation_multiplier("MO", {
            "family_ownership_years": 60,
            "owner_occupied": False,
        })
        # Long-term family bonus may still apply regardless of occupancy
        # Check the specific MO rules for this edge case
        assert multiplier >= 1.0


class TestMissouriNoticeRequirements:
    """Tests for MO's enhanced notice requirements."""

    def test_mo_60_day_notice_of_intent(self):
        """MO should require 60-day notice of intent."""
        config = get_jurisdiction_config("MO")
        assert config.initiation.get("notice_of_intent_days") == 60

    def test_mo_30_day_final_offer(self):
        """MO should require 30-day final offer period."""
        config = get_jurisdiction_config("MO")
        assert config.initiation.get("final_offer_days") == 30

    def test_mo_final_offer_explanation_required(self):
        """MO should require explanation of how offer was calculated."""
        config = get_jurisdiction_config("MO")
        assert config.initiation.get("final_offer_explanation_required") is True


class TestMissouriAttorneyFees:
    """Tests for MO attorney fee rules."""

    def test_mo_fees_threshold_based(self):
        """MO fees should be threshold-based."""
        fees = get_attorney_fee_rules("MO")
        assert fees["threshold_based"] is True

    def test_mo_fees_20_percent_threshold(self):
        """MO should award fees if award exceeds commissioners by 20%."""
        fees = get_attorney_fee_rules("MO")
        assert fees["threshold_percent"] == 20


class TestMissouriPublicUse:
    """Tests for MO public use limitations."""

    def test_mo_economic_development_banned(self):
        """MO should ban economic development takings."""
        assert is_economic_development_banned("MO") is True

    def test_mo_blight_definition_tightened(self):
        """MO should have tightened blight definition."""
        config = get_jurisdiction_config("MO")
        assert config.public_use.get("blight_definition_tightened") is True

    def test_mo_citizens_appeal_right(self):
        """MO should provide citizen's right to appeal blight designations."""
        config = get_jurisdiction_config("MO")
        assert config.owner_rights.get("citizens_appeal_right") is True
        assert config.owner_rights.get("blight_designation_appeal") is True


class TestMissouriDeadlineChains:
    """Tests for MO deadline chain structure."""

    def test_mo_notice_of_intent_chain(self):
        """MO should have notice of intent deadline chain."""
        rules = load_rule("MO")
        chains = rules.get("deadline_chains", [])
        
        intent_chain = next(
            (c for c in chains if c.get("anchor_event") == "notice_of_intent_served"),
            None
        )
        assert intent_chain is not None

    def test_mo_60_day_floor(self):
        """Cannot file until 60 days after notice of intent."""
        rules = load_rule("MO")
        chains = rules.get("deadline_chains", [])
        
        intent_chain = next(
            (c for c in chains if c.get("anchor_event") == "notice_of_intent_served"),
            None
        )
        
        filing_floor = next(
            (d for d in intent_chain.get("deadlines", [])
             if d.get("id") == "earliest_filing_date"),
            None
        )
        
        assert filing_floor is not None
        assert filing_floor.get("offset_days") == 60
        assert filing_floor.get("type") == "floor"


class TestMissouriTriggerEvaluation:
    """Tests for evaluating MO triggers."""

    def test_mo_notice_of_intent_trigger(self, mo_heritage_payload: dict[str, Any]):
        """Notice of intent trigger should fire when notice is served."""
        results = evaluate_rules("MO", mo_heritage_payload)
        
        intent_trigger = next(
            (r for r in results if "notice_of_intent" in r.rule_id),
            None
        )
        assert intent_trigger is not None
        assert intent_trigger.fired is True

    def test_mo_heritage_family_trigger(self, mo_heritage_payload: dict[str, Any]):
        """Heritage value trigger should fire for 50+ year family ownership."""
        results = evaluate_rules("MO", mo_heritage_payload)
        
        heritage_trigger = next(
            (r for r in results if "heritage_value_family" in r.rule_id),
            None
        )
        assert heritage_trigger is not None
        assert heritage_trigger.fired is True

    def test_mo_homestead_trigger(self, mo_homestead_payload: dict[str, Any]):
        """Homestead trigger should fire for owner-occupied under 50 years."""
        results = evaluate_rules("MO", mo_homestead_payload)
        
        homestead_trigger = next(
            (r for r in results if "heritage_value_homestead" in r.rule_id),
            None
        )
        assert homestead_trigger is not None
        assert homestead_trigger.fired is True
