"""
Tests for Michigan eminent domain rules.

Michigan is unique for:
- 125% compensation for owner-occupied principal residences (constitutional)
- Mandatory attorney fee reimbursement
- Going concern value for businesses that cannot relocate
- Clear and convincing evidence required for blight
- County of Wayne v. Hathcock (2004) predates Kelo
"""

import pytest
from typing import Any

from app.services.rules_engine import (
    load_rule,
    evaluate_rules,
    get_jurisdiction_config,
    get_compensation_multiplier,
    get_attorney_fee_rules,
    is_quick_take_available,
    is_economic_development_banned,
)


class TestMichiganRulesLoading:
    """Tests for loading MI rules."""

    def test_mi_rules_load(self):
        """MI rules should load successfully."""
        rules = load_rule("MI")
        assert rules is not None
        assert rules.get("jurisdiction") == "MI"

    def test_mi_extends_base(self):
        """MI rules should extend base."""
        rules = load_rule("MI")
        assert rules.get("extends") == "base"

    def test_mi_cites_constitution(self):
        """MI rules should cite constitution."""
        rules = load_rule("MI")
        citations = rules.get("citations", {})
        assert "Mich. Const." in citations.get("constitution", "")


class TestMichiganResidenceMultiplier:
    """Tests for MI's 125% residence multiplier."""

    def test_mi_has_residence_multiplier(self):
        """MI should have 1.25 residence multiplier."""
        config = get_jurisdiction_config("MI")
        assert config.compensation.get("residence_multiplier") == 1.25

    def test_mi_multiplier_applies_owner_occupied(self, mi_owner_occupied_payload: dict[str, Any]):
        """Multiplier should apply for owner-occupied principal residence."""
        multiplier = get_compensation_multiplier("MI", {
            "owner_occupied": True,
            "principal_residence": True,
        })
        assert multiplier == 1.25

    def test_mi_multiplier_not_applies_rental(self):
        """Multiplier should not apply for rental property."""
        multiplier = get_compensation_multiplier("MI", {
            "owner_occupied": False,
            "principal_residence": False,
        })
        assert multiplier == 1.0

    def test_mi_multiplier_not_applies_non_principal(self):
        """Multiplier should not apply for non-principal residence."""
        multiplier = get_compensation_multiplier("MI", {
            "owner_occupied": True,
            "principal_residence": False,  # vacation home
        })
        assert multiplier == 1.0


class TestMichiganAttorneyFees:
    """Tests for MI's mandatory attorney fee reimbursement."""

    def test_mi_fees_automatic(self):
        """MI should automatically award attorney fees."""
        fees = get_attorney_fee_rules("MI")
        assert fees["automatic"] is True

    def test_mi_fees_mandatory(self):
        """MI fees should be mandatory."""
        fees = get_attorney_fee_rules("MI")
        assert fees["mandatory"] is True

    def test_mi_fees_include_expert(self):
        """MI fees should include expert witness fees."""
        fees = get_attorney_fee_rules("MI")
        assert fees["includes_expert_fees"] is True


class TestMichiganBusinessCompensation:
    """Tests for MI business compensation rules."""

    def test_mi_compensates_business_losses(self):
        """MI should compensate for business losses."""
        config = get_jurisdiction_config("MI")
        business = config.compensation.get("business_losses", {})
        
        assert business.get("compensable") is True
        assert business.get("includes_interruption_costs") is True

    def test_mi_compensates_going_concern(self):
        """MI should compensate going concern value for non-relocatable businesses."""
        config = get_jurisdiction_config("MI")
        going_concern = config.compensation.get("going_concern_value", {})
        
        assert going_concern.get("compensable") is True


class TestMichiganBlightStandard:
    """Tests for MI's clear and convincing evidence standard for blight."""

    def test_mi_blight_clear_and_convincing(self):
        """MI should require clear and convincing evidence for blight."""
        config = get_jurisdiction_config("MI")
        assert config.public_use.get("blight_proof_standard") == "clear_and_convincing"

    def test_mi_blight_parcel_specific(self):
        """MI should require parcel-specific blight determination."""
        config = get_jurisdiction_config("MI")
        assert config.public_use.get("blight_parcel_specific") is True


class TestMichiganPublicUse:
    """Tests for MI public use limitations."""

    def test_mi_economic_development_banned(self):
        """MI should ban economic development takings."""
        assert is_economic_development_banned("MI") is True

    def test_mi_has_hathcock_precedent(self):
        """MI should reference Hathcock decision."""
        config = get_jurisdiction_config("MI")
        hathcock = config.public_use.get("hathcock_decision", {})
        
        assert hathcock.get("year") == 2004
        assert hathcock.get("predates_kelo") is True

    def test_mi_2006_constitutional_reform(self):
        """MI should have 2006 constitutional reform."""
        config = get_jurisdiction_config("MI")
        assert config.public_use.get("post_kelo_reform_year") == 2006
        assert config.public_use.get("reform_type") == "constitutional"


class TestMichiganChallengeWindow:
    """Tests for MI's limited challenge window."""

    def test_mi_has_limited_challenge_window(self):
        """MI should have limited window to contest necessity."""
        config = get_jurisdiction_config("MI")
        
        assert config.owner_rights.get("challenge_window_limited") is True
        assert config.owner_rights.get("challenge_deadline_days") == 21


class TestMichiganTriggerEvaluation:
    """Tests for evaluating MI triggers."""

    def test_mi_offer_served_trigger(self, mi_owner_occupied_payload: dict[str, Any]):
        """Offer served trigger should fire when offer is served."""
        results = evaluate_rules("MI", mi_owner_occupied_payload)
        
        offer_trigger = next(
            (r for r in results if "offer_served" in r.rule_id),
            None
        )
        assert offer_trigger is not None
        assert offer_trigger.fired is True

    def test_mi_residence_compensation_trigger(self, mi_owner_occupied_payload: dict[str, Any]):
        """Residence compensation trigger should fire for owner-occupied residence."""
        results = evaluate_rules("MI", mi_owner_occupied_payload)
        
        residence_trigger = next(
            (r for r in results if "residence_compensation" in r.rule_id),
            None
        )
        assert residence_trigger is not None
        assert residence_trigger.fired is True
