"""
Tests for Florida eminent domain rules.

Florida is unique for:
- "Full compensation" constitutional standard (not just "just compensation")
- Automatic attorney fee reimbursement
- Prohibition on blight takings for private redevelopment
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


class TestFloridaRulesLoading:
    """Tests for loading FL rules."""

    def test_fl_rules_load(self):
        """FL rules should load successfully."""
        rules = load_rule("FL")
        assert rules is not None
        assert rules.get("jurisdiction") == "FL"

    def test_fl_extends_base(self):
        """FL rules should extend base."""
        rules = load_rule("FL")
        assert rules.get("extends") == "base"

    def test_fl_has_constitutional_citation(self):
        """FL rules should cite constitution."""
        rules = load_rule("FL")
        citations = rules.get("citations", {})
        assert "Fla. Const." in citations.get("constitution", "")


class TestFloridaFullCompensation:
    """Tests for FL's unique 'full compensation' standard."""

    def test_fl_full_compensation_base(self):
        """FL should use 'full_compensation' as base standard."""
        config = get_jurisdiction_config("FL")
        assert config.compensation.get("base") == "full_compensation"

    def test_fl_includes_stigma_damages(self):
        """FL should include stigma damages in compensation."""
        config = get_jurisdiction_config("FL")
        assert config.compensation.get("stigma_damages") is True


class TestFloridaAttorneyFees:
    """Tests for FL's automatic attorney fee rules."""

    def test_fl_fees_automatic(self):
        """FL should automatically award attorney fees."""
        fees = get_attorney_fee_rules("FL")
        assert fees["automatic"] is True

    def test_fl_fees_include_expert(self):
        """FL attorney fees should include expert fees."""
        fees = get_attorney_fee_rules("FL")
        assert fees["includes_expert_fees"] is True

    def test_fl_fees_mandatory(self):
        """FL should mandate condemnor pays fees."""
        config = get_jurisdiction_config("FL")
        atty_fees = config.compensation.get("attorney_fees", {})
        assert atty_fees.get("paid_by_condemnor") is True


class TestFloridaQuickTake:
    """Tests for FL quick-take (Order of Taking) procedure."""

    def test_fl_has_quick_take(self):
        """FL should have quick-take available."""
        assert is_quick_take_available("FL") is True

    def test_fl_quick_take_type(self):
        """FL quick-take should be 'order_of_taking' type."""
        config = get_jurisdiction_config("FL")
        quick_take = config.initiation.get("quick_take", {})
        assert quick_take.get("type") == "order_of_taking"

    def test_fl_quick_take_requires_hearing(self):
        """FL quick-take should require a hearing."""
        config = get_jurisdiction_config("FL")
        quick_take = config.initiation.get("quick_take", {})
        assert quick_take.get("hearing_required") is True


class TestFloridaPublicUse:
    """Tests for FL public use limitations."""

    def test_fl_economic_development_banned(self):
        """FL should ban economic development takings."""
        assert is_economic_development_banned("FL") is True

    def test_fl_blight_elimination_banned(self):
        """FL should ban blight elimination as justification for private takings."""
        config = get_jurisdiction_config("FL")
        assert config.public_use.get("blight_elimination_banned") is True
        assert config.public_use.get("blight_for_private") == "prohibited"

    def test_fl_post_kelo_reform(self):
        """FL should have 2006 post-Kelo reform."""
        config = get_jurisdiction_config("FL")
        assert config.public_use.get("post_kelo_reform_year") == 2006
        assert config.public_use.get("reform_type") == "both"


class TestFloridaTriggerEvaluation:
    """Tests for evaluating FL triggers."""

    def test_fl_presuit_trigger(self, fl_presuit_payload: dict[str, Any]):
        """Presuit negotiation trigger should fire when offer is rejected."""
        results = evaluate_rules("FL", fl_presuit_payload)
        
        presuit_trigger = next(
            (r for r in results if "presuit" in r.rule_id),
            None
        )
        assert presuit_trigger is not None
        assert presuit_trigger.fired is True

    def test_fl_captures_negotiation_evidence(self, fl_presuit_payload: dict[str, Any]):
        """FL trigger should capture negotiation attempts evidence."""
        results = evaluate_rules("FL", fl_presuit_payload)
        
        presuit_trigger = next(
            (r for r in results if "presuit" in r.rule_id),
            None
        )
        
        assert presuit_trigger is not None
        assert len(presuit_trigger.evidence) > 0
