#!/usr/bin/env python3
"""
Texas vs Indiana Eminent Domain Regression Test Suite

Comprehensive regression tests comparing Texas and Indiana requirements.
Each test case documents its inputs explicitly for traceability.

Usage:
    cd backend && python -m scripts.regression_tx_vs_in

Output:
    artifacts/regression/tx_vs_in_regression_YYYY-MM-DD_HH-mm-ss.csv

Author: LandRight Team
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable
import traceback


# =============================================================================
# CONFIGURATION
# =============================================================================

REPO_ROOT = Path(__file__).parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "regression"


class TestStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class TestInput:
    """Documented test input with all fields explicitly defined."""
    
    # Case identification
    case_id: str = "TEST-001"
    jurisdiction: str = "TX"
    
    # Parcel information
    parcel_pin: str = "12-34-56-789"
    parcel_assessed_value: float = 150000.00
    parcel_owner_occupied: bool = True
    parcel_principal_residence: bool = True
    parcel_family_ownership_years: int = 10
    parcel_has_business: bool = False
    parcel_is_agricultural: bool = False
    parcel_acreage: float = 1.5
    
    # Owner information
    owner_name: str = "Test Owner"
    owner_address: str = "123 Main St"
    owner_city: str = "Austin"
    owner_state: str = "TX"
    owner_zip: str = "78701"
    owner_phone: str = "512-555-1234"
    owner_email: str = "owner@example.com"
    
    # Offer details
    offer_total_amount: float = 150000.00
    offer_appraisal_value: float = 150000.00
    offer_appraisal_date: str = "2025-01-15"
    offer_includes_severance: bool = True
    offer_severance_amount: float = 0.00
    
    # Event timestamps (ISO format strings)
    event_offer_served: str | None = "2025-01-20"
    event_final_offer_served: str | None = None
    event_bill_of_rights_served: str | None = None
    event_notice_of_intent_served: str | None = None
    event_complaint_filed: str | None = None
    event_notice_served: str | None = None
    event_appraisers_report_mailed: str | None = None
    event_commissioners_award: str | None = None
    event_trial_date_set: str | None = None
    
    # Case metadata
    case_dispute_level: str = "LOW"  # LOW, MEDIUM, HIGH
    case_project_type: str = "highway"
    case_condemnor_type: str = "state_dot"
    
    # Business details (if applicable)
    business_name: str | None = None
    business_type: str | None = None
    business_years_at_location: int | None = None
    business_annual_revenue: float | None = None
    
    def to_payload(self) -> dict[str, Any]:
        """Convert to rules engine payload format."""
        return {
            "case.id": self.case_id,
            "case.jurisdiction": self.jurisdiction,
            "case.dispute_level": self.case_dispute_level,
            "case.project_type": self.case_project_type,
            "case.condemnor_type": self.case_condemnor_type,
            
            "parcel.pin": self.parcel_pin,
            "parcel.assessed_value": self.parcel_assessed_value,
            "parcel.owner_occupied": self.parcel_owner_occupied,
            "parcel.principal_residence": self.parcel_principal_residence,
            "parcel.family_ownership_years": self.parcel_family_ownership_years,
            "parcel.has_business": self.parcel_has_business,
            "parcel.is_agricultural": self.parcel_is_agricultural,
            "parcel.acreage": self.parcel_acreage,
            
            "owner.name": self.owner_name,
            "owner.address": self.owner_address,
            "owner.city": self.owner_city,
            "owner.state": self.owner_state,
            "owner.zip": self.owner_zip,
            
            "offer.total_amount": self.offer_total_amount,
            "offer.appraisal_value": self.offer_appraisal_value,
            "offer.appraisal_date": self.offer_appraisal_date,
            "offer.includes_severance": self.offer_includes_severance,
            "offer.severance_amount": self.offer_severance_amount,
            
            "events.offer_served": self.event_offer_served,
            "events.final_offer_served": self.event_final_offer_served,
            "events.bill_of_rights_served": self.event_bill_of_rights_served,
            "events.notice_of_intent_served": self.event_notice_of_intent_served,
            "events.complaint_filed": self.event_complaint_filed,
            "events.notice_served": self.event_notice_served,
            "events.appraisers_report_mailed": self.event_appraisers_report_mailed,
            "events.commissioners_award": self.event_commissioners_award,
            "events.trial_date_set": self.event_trial_date_set,
            
            "appraisal.value": self.offer_appraisal_value,
            "appraisal.date": self.offer_appraisal_date,
            
            "business.name": self.business_name,
            "business.type": self.business_type,
            "business.years_at_location": self.business_years_at_location,
            "business.annual_revenue": self.business_annual_revenue,
        }


@dataclass
class TestResult:
    """Result of a single test case."""
    test_id: str
    test_name: str
    category: str
    jurisdiction: str
    status: TestStatus
    expected: Any
    actual: Any
    duration_ms: int
    error_message: str = ""
    input_summary: str = ""
    

@dataclass
class TestCase:
    """A single test case with documented inputs and expected outputs."""
    test_id: str
    name: str
    description: str
    category: str
    jurisdiction: str
    inputs: TestInput
    expected_outcome: dict[str, Any]
    test_fn: Callable[[TestInput], dict[str, Any]] | None = None


# =============================================================================
# TEST INPUT DEFINITIONS
# =============================================================================

def create_texas_base_input() -> TestInput:
    """
    Texas base test input with standard values.
    
    Key Texas-specific fields:
    - jurisdiction: TX
    - Requires Landowner Bill of Rights
    - 30-day initial offer wait period
    - 14-day final offer consideration
    - 7-day Bill of Rights notice before final offer
    """
    return TestInput(
        case_id="TX-REG-001",
        jurisdiction="TX",
        parcel_pin="TX-12-34-56-789",
        parcel_assessed_value=200000.00,
        parcel_owner_occupied=True,
        parcel_principal_residence=True,
        parcel_family_ownership_years=15,
        owner_name="John Smith",
        owner_city="Houston",
        owner_state="TX",
        offer_total_amount=200000.00,
        offer_appraisal_value=200000.00,
        offer_appraisal_date="2025-01-15",
        event_offer_served="2025-01-20",
        case_dispute_level="LOW",
        case_project_type="highway",
        case_condemnor_type="txdot",
    )


def create_indiana_base_input() -> TestInput:
    """
    Indiana base test input with standard values.
    
    Key Indiana-specific fields:
    - jurisdiction: IN
    - Requires Notice of Intent (certified mail)
    - 30-day response window
    - Court-appointed appraisers
    - 45-day exceptions window after appraisers report
    - Requires local legislative body approval
    """
    return TestInput(
        case_id="IN-REG-001",
        jurisdiction="IN",
        parcel_pin="IN-12-34-56-789",
        parcel_assessed_value=200000.00,
        parcel_owner_occupied=True,
        parcel_principal_residence=True,
        parcel_family_ownership_years=15,
        owner_name="Jane Doe",
        owner_city="Indianapolis",
        owner_state="IN",
        offer_total_amount=200000.00,
        offer_appraisal_value=200000.00,
        offer_appraisal_date="2025-01-15",
        event_offer_served="2025-01-20",
        event_notice_of_intent_served="2025-01-10",
        case_dispute_level="LOW",
        case_project_type="highway",
        case_condemnor_type="indot",
    )


def create_texas_high_value_input() -> TestInput:
    """
    Texas high-value parcel input (> $250,000 threshold).
    
    Expected behavior:
    - Should trigger tx_valuation_threshold rule
    - Requires enhanced legal review
    - May require good faith meeting at 45 days
    """
    base = create_texas_base_input()
    base.case_id = "TX-REG-002"
    base.parcel_assessed_value = 500000.00
    base.offer_total_amount = 500000.00
    base.offer_appraisal_value = 500000.00
    base.case_dispute_level = "MEDIUM"
    return base


def create_indiana_high_value_input() -> TestInput:
    """
    Indiana high-value parcel input.
    
    Expected behavior:
    - Standard Indiana procedures apply
    - No special valuation threshold triggers
    - Owner may elect annual payments (> $5,000)
    """
    base = create_indiana_base_input()
    base.case_id = "IN-REG-002"
    base.parcel_assessed_value = 500000.00
    base.offer_total_amount = 500000.00
    base.offer_appraisal_value = 500000.00
    return base


def create_texas_disputed_input() -> TestInput:
    """
    Texas high-dispute scenario.
    
    Expected behavior:
    - Should trigger valuation threshold due to HIGH dispute
    - Enhanced procedural scrutiny
    - Possible challenge to public use
    """
    base = create_texas_base_input()
    base.case_id = "TX-REG-003"
    base.case_dispute_level = "HIGH"
    base.parcel_assessed_value = 150000.00  # Below dollar threshold
    base.offer_total_amount = 150000.00
    return base


def create_indiana_disputed_input() -> TestInput:
    """
    Indiana high-dispute scenario.
    
    Expected behavior:
    - Owner likely to file objections within 30-day window
    - May request 30-day extension
    - Court findings required if private facility taking
    """
    base = create_indiana_base_input()
    base.case_id = "IN-REG-003"
    base.case_dispute_level = "HIGH"
    return base


def create_texas_with_timeline_input() -> TestInput:
    """
    Texas case with full timeline events populated.
    
    Timeline:
    - Offer served: 2025-01-20
    - Bill of Rights served: 2025-02-10 (7+ days before final offer)
    - Final offer served: 2025-02-20 (30+ days after initial)
    - Commissioners award: 2025-04-01
    
    Expected deadlines:
    - Final offer response: 2025-03-06 (14 days after final offer)
    - Commissioners objection: 2025-04-21 (20 days after award)
    """
    base = create_texas_base_input()
    base.case_id = "TX-REG-004"
    base.event_offer_served = "2025-01-20"
    base.event_bill_of_rights_served = "2025-02-10"
    base.event_final_offer_served = "2025-02-20"
    base.event_commissioners_award = "2025-04-01"
    return base


def create_indiana_with_timeline_input() -> TestInput:
    """
    Indiana case with full timeline events populated.
    
    Timeline:
    - Notice of intent served: 2025-01-10
    - Offer served: 2025-01-20
    - Complaint filed: 2025-02-25 (30+ days after offer)
    - Notice served: 2025-03-01
    - Appraisers report mailed: 2025-04-15
    
    Expected deadlines:
    - Owner response window: 2025-02-19 (30 days after offer)
    - Defendant objection: 2025-03-31 (30 days after notice, extendable)
    - Exceptions deadline: 2025-05-30 (45 days after report mailed)
    """
    base = create_indiana_base_input()
    base.case_id = "IN-REG-004"
    base.event_notice_of_intent_served = "2025-01-10"
    base.event_offer_served = "2025-01-20"
    base.event_complaint_filed = "2025-02-25"
    base.event_notice_served = "2025-03-01"
    base.event_appraisers_report_mailed = "2025-04-15"
    return base


def create_texas_quick_take_input() -> TestInput:
    """
    Texas quick-take scenario.
    
    Expected behavior:
    - Quick-take available for all condemnations
    - Deposit and possession after commissioners' award
    - No court approval required
    - Owner can still object (leads to jury trial)
    """
    base = create_texas_base_input()
    base.case_id = "TX-REG-005"
    base.case_project_type = "highway_expansion"
    base.event_commissioners_award = "2025-04-01"
    return base


def create_indiana_quick_take_input() -> TestInput:
    """
    Indiana quick-take scenario (highway project).
    
    Expected behavior:
    - Quick-take only for certain highway projects
    - Requires court approval
    - Deposit required
    - More limited scope than Texas
    """
    base = create_indiana_base_input()
    base.case_id = "IN-REG-005"
    base.case_project_type = "highway"
    base.case_condemnor_type = "indot"
    return base


def create_texas_partial_taking_input() -> TestInput:
    """
    Texas partial taking scenario.
    
    Expected behavior:
    - Severance damages included (Tex. Prop. Code §21.042)
    - Loss of access NOT separately compensated
    - Compensation = FMV of taken portion + damage to remainder
    """
    base = create_texas_base_input()
    base.case_id = "TX-REG-006"
    base.parcel_acreage = 10.0
    base.offer_includes_severance = True
    base.offer_severance_amount = 25000.00
    base.offer_total_amount = 75000.00  # 50K taken + 25K severance
    base.offer_appraisal_value = 50000.00  # Just the taken portion
    return base


def create_indiana_partial_taking_input() -> TestInput:
    """
    Indiana partial taking scenario.
    
    Expected behavior:
    - Severance damages included
    - Loss of ingress/egress compensable (damage to remainder)
    - Better loss-of-access protection than Texas
    """
    base = create_indiana_base_input()
    base.case_id = "IN-REG-006"
    base.parcel_acreage = 10.0
    base.offer_includes_severance = True
    base.offer_severance_amount = 30000.00  # Higher due to access loss
    base.offer_total_amount = 80000.00
    base.offer_appraisal_value = 50000.00
    return base


def create_texas_business_input() -> TestInput:
    """
    Texas property with business (no goodwill compensation).
    
    Expected behavior:
    - Business goodwill: NOT compensable
    - Business losses: NOT compensable (unless affects real property value)
    - Relocation assistance available (separate from ED damages)
    """
    base = create_texas_base_input()
    base.case_id = "TX-REG-007"
    base.parcel_has_business = True
    base.business_name = "Smith's Auto Shop"
    base.business_type = "automotive_repair"
    base.business_years_at_location = 20
    base.business_annual_revenue = 350000.00
    return base


def create_indiana_business_input() -> TestInput:
    """
    Indiana property with business (no goodwill compensation).
    
    Expected behavior:
    - Business goodwill: NOT compensable
    - Business losses: NOT compensable
    - Relocation assistance available per federal guidelines
    """
    base = create_indiana_base_input()
    base.case_id = "IN-REG-007"
    base.parcel_has_business = True
    base.business_name = "Doe's Diner"
    base.business_type = "restaurant"
    base.business_years_at_location = 15
    base.business_annual_revenue = 250000.00
    return base


def create_texas_attorney_fees_input() -> TestInput:
    """
    Texas attorney fees scenario.
    
    Expected behavior:
    - Automatic fees: NO
    - Threshold-based fees: NO
    - Fees only if condemnor lacks authority or fails procedure
    - 2011 amendments: stronger recovery if entity abuses process
    """
    base = create_texas_base_input()
    base.case_id = "TX-REG-008"
    base.case_dispute_level = "HIGH"
    return base


def create_indiana_attorney_fees_input() -> TestInput:
    """
    Indiana attorney fees scenario.
    
    Expected behavior:
    - Automatic fees: NO
    - Threshold-based fees: YES
    - Fees if final award exceeds appraisers' award by "substantial amount"
    - Citation: IC 32-24-1-14
    """
    base = create_indiana_base_input()
    base.case_id = "IN-REG-008"
    base.case_dispute_level = "HIGH"
    base.offer_total_amount = 200000.00
    # Assume final award would be significantly higher
    return base


def create_indiana_payment_election_input() -> TestInput:
    """
    Indiana annual payment election scenario.
    
    Expected behavior:
    - For offers over $5,000, owner may elect annual payments
    - Max payment period: 20 years
    - Includes interest
    - Citation: IC 32-24-4-4
    """
    base = create_indiana_base_input()
    base.case_id = "IN-REG-009"
    base.offer_total_amount = 150000.00  # Well over $5,000 threshold
    return base


# =============================================================================
# TEST CASE DEFINITIONS
# =============================================================================

TEST_CASES: list[TestCase] = [
    # ----- Initiation Procedure Tests -----
    TestCase(
        test_id="TX-INIT-001",
        name="Texas requires Landowner Bill of Rights",
        description="Verify TX mandates Landowner Bill of Rights document",
        category="Initiation",
        jurisdiction="TX",
        inputs=create_texas_base_input(),
        expected_outcome={
            "landowner_bill_of_rights": True,
            "bill_of_rights_citation": "Tex. Prop. Code §21.0112",
        },
    ),
    TestCase(
        test_id="IN-INIT-001",
        name="Indiana does NOT require Landowner Bill of Rights",
        description="Verify IN does not mandate Bill of Rights document",
        category="Initiation",
        jurisdiction="IN",
        inputs=create_indiana_base_input(),
        expected_outcome={
            "landowner_bill_of_rights": False,
        },
    ),
    TestCase(
        test_id="TX-INIT-002",
        name="Texas does NOT require resolution",
        description="Verify TX does not require local body resolution",
        category="Initiation",
        jurisdiction="TX",
        inputs=create_texas_base_input(),
        expected_outcome={
            "resolution_required": False,
        },
    ),
    TestCase(
        test_id="IN-INIT-002",
        name="Indiana requires local body resolution",
        description="Verify IN requires city/town council or county commissioner approval",
        category="Initiation",
        jurisdiction="IN",
        inputs=create_indiana_base_input(),
        expected_outcome={
            "resolution_required": True,
            "resolution_body": "city/town council or county commissioners",
        },
    ),
    
    # ----- Notice Period Tests -----
    TestCase(
        test_id="TX-NOTICE-001",
        name="Texas 30-day initial offer wait period",
        description="Verify TX requires 30 days after initial offer before final offer",
        category="Notice",
        jurisdiction="TX",
        inputs=create_texas_base_input(),
        expected_outcome={
            "initial_offer_days": 30,
        },
    ),
    TestCase(
        test_id="TX-NOTICE-002",
        name="Texas 14-day final offer consideration",
        description="Verify TX gives owner 14 days to consider final offer",
        category="Notice",
        jurisdiction="TX",
        inputs=create_texas_base_input(),
        expected_outcome={
            "final_offer_days": 14,
        },
    ),
    TestCase(
        test_id="TX-NOTICE-003",
        name="Texas 7-day Bill of Rights notice",
        description="Verify TX requires Bill of Rights 7 days before final offer",
        category="Notice",
        jurisdiction="TX",
        inputs=create_texas_base_input(),
        expected_outcome={
            "bill_of_rights_notice_days": 7,
        },
    ),
    TestCase(
        test_id="IN-NOTICE-001",
        name="Indiana 30-day owner response window",
        description="Verify IN gives owner 30 days to respond to offer",
        category="Notice",
        jurisdiction="IN",
        inputs=create_indiana_base_input(),
        expected_outcome={
            "owner_response_days": 30,
        },
    ),
    TestCase(
        test_id="IN-NOTICE-002",
        name="Indiana 30-day objection window (extendable)",
        description="Verify IN objection deadline is 30 days and extendable by 30 more",
        category="Notice",
        jurisdiction="IN",
        inputs=create_indiana_base_input(),
        expected_outcome={
            "objection_window_days": 30,
            "extension_days": 30,
            "extendable": True,
        },
    ),
    TestCase(
        test_id="IN-NOTICE-003",
        name="Indiana 45-day exceptions window",
        description="Verify IN allows 45 days to file exceptions to appraisers' report",
        category="Notice",
        jurisdiction="IN",
        inputs=create_indiana_base_input(),
        expected_outcome={
            "exceptions_window_days": 45,
        },
    ),
    
    # ----- Quick-Take Tests -----
    TestCase(
        test_id="TX-QT-001",
        name="Texas quick-take broadly available",
        description="Verify TX allows quick-take for all condemnations",
        category="Quick-Take",
        jurisdiction="TX",
        inputs=create_texas_quick_take_input(),
        expected_outcome={
            "quick_take_available": True,
            "quick_take_type": "deposit_and_possession",
            "court_approval_required": False,
        },
    ),
    TestCase(
        test_id="IN-QT-001",
        name="Indiana quick-take limited to highways",
        description="Verify IN quick-take only for certain highway projects",
        category="Quick-Take",
        jurisdiction="IN",
        inputs=create_indiana_quick_take_input(),
        expected_outcome={
            "quick_take_available": True,
            "quick_take_type": "deposit_and_possession",
            "court_approval_required": True,
        },
    ),
    
    # ----- Compensation Tests -----
    TestCase(
        test_id="TX-COMP-001",
        name="Texas compensation standard",
        description="Verify TX uses 'adequate compensation' (constitutional term)",
        category="Compensation",
        jurisdiction="TX",
        inputs=create_texas_base_input(),
        expected_outcome={
            "compensation_standard": "adequate compensation",
            "highest_and_best_use": True,
            "severance_damages": True,
        },
    ),
    TestCase(
        test_id="IN-COMP-001",
        name="Indiana compensation standard",
        description="Verify IN uses fair market value standard",
        category="Compensation",
        jurisdiction="IN",
        inputs=create_indiana_base_input(),
        expected_outcome={
            "compensation_standard": "fair_market_value",
            "highest_and_best_use": True,
            "severance_damages": True,
        },
    ),
    TestCase(
        test_id="TX-COMP-002",
        name="Texas loss of access NOT compensated",
        description="Verify TX does NOT separately compensate loss of access",
        category="Compensation",
        jurisdiction="TX",
        inputs=create_texas_partial_taking_input(),
        expected_outcome={
            "loss_of_access_compensable": False,
        },
    ),
    TestCase(
        test_id="IN-COMP-002",
        name="Indiana loss of access IS compensated",
        description="Verify IN compensates loss of ingress/egress in partial takings",
        category="Compensation",
        jurisdiction="IN",
        inputs=create_indiana_partial_taking_input(),
        expected_outcome={
            "loss_of_access_compensable": True,
        },
    ),
    TestCase(
        test_id="TX-COMP-003",
        name="Texas no business goodwill",
        description="Verify TX does NOT compensate business goodwill",
        category="Compensation",
        jurisdiction="TX",
        inputs=create_texas_business_input(),
        expected_outcome={
            "business_goodwill": False,
            "business_losses": False,
        },
    ),
    TestCase(
        test_id="IN-COMP-003",
        name="Indiana no business goodwill",
        description="Verify IN does NOT compensate business goodwill",
        category="Compensation",
        jurisdiction="IN",
        inputs=create_indiana_business_input(),
        expected_outcome={
            "business_goodwill": False,
            "business_losses": False,
        },
    ),
    
    # ----- Attorney Fees Tests -----
    TestCase(
        test_id="TX-FEES-001",
        name="Texas no automatic attorney fees",
        description="Verify TX does NOT automatically award attorney fees",
        category="Attorney Fees",
        jurisdiction="TX",
        inputs=create_texas_attorney_fees_input(),
        expected_outcome={
            "automatic_fees": False,
            "threshold_based": False,
        },
    ),
    TestCase(
        test_id="IN-FEES-001",
        name="Indiana threshold-based attorney fees",
        description="Verify IN awards fees if final award exceeds appraisers by substantial amount",
        category="Attorney Fees",
        jurisdiction="IN",
        inputs=create_indiana_attorney_fees_input(),
        expected_outcome={
            "automatic_fees": False,
            "threshold_based": True,
        },
    ),
    
    # ----- Public Use Limitations Tests -----
    TestCase(
        test_id="TX-PU-001",
        name="Texas constitutional public use reform",
        description="Verify TX has constitutional + statutory ban on economic development takings",
        category="Public Use",
        jurisdiction="TX",
        inputs=create_texas_base_input(),
        expected_outcome={
            "economic_development_banned": True,
            "tax_revenue_banned": True,
            "reform_type": "constitutional_and_statutory",
        },
    ),
    TestCase(
        test_id="IN-PU-001",
        name="Indiana statutory public use reform",
        description="Verify IN has statutory ban on economic development takings",
        category="Public Use",
        jurisdiction="IN",
        inputs=create_indiana_base_input(),
        expected_outcome={
            "economic_development_banned": True,
            "tax_revenue_banned": True,
            "reform_type": "statutory",
        },
    ),
    TestCase(
        test_id="TX-PU-002",
        name="Texas blight restrictions",
        description="Verify TX restricts blight designation for economic development",
        category="Public Use",
        jurisdiction="TX",
        inputs=create_texas_base_input(),
        expected_outcome={
            "blight_for_private": "restricted",
            "blight_parcel_specific": False,
        },
    ),
    TestCase(
        test_id="IN-PU-002",
        name="Indiana parcel-specific blight",
        description="Verify IN requires parcel-by-parcel blight determination",
        category="Public Use",
        jurisdiction="IN",
        inputs=create_indiana_base_input(),
        expected_outcome={
            "blight_for_private": "restricted",
            "blight_parcel_specific": True,
            "blight_definition_narrowed": True,
        },
    ),
    
    # ----- Trial/Commissioners Tests -----
    TestCase(
        test_id="TX-TRIAL-001",
        name="Texas special commissioners panel",
        description="Verify TX uses 3 local landowners as special commissioners",
        category="Trial",
        jurisdiction="TX",
        inputs=create_texas_base_input(),
        expected_outcome={
            "commissioners_type": "special_commissioners",
            "jury_trial_available": True,
        },
    ),
    TestCase(
        test_id="IN-TRIAL-001",
        name="Indiana court-appointed appraisers",
        description="Verify IN uses court-appointed appraisers",
        category="Trial",
        jurisdiction="IN",
        inputs=create_indiana_base_input(),
        expected_outcome={
            "commissioners_type": "appraisers",
            "jury_trial_available": True,
        },
    ),
    
    # ----- Timeline Validation Tests -----
    TestCase(
        test_id="TX-TIME-001",
        name="Texas has deadline chains defined",
        description="Verify TX has deadline chains for procedural events",
        category="Timeline",
        jurisdiction="TX",
        inputs=create_texas_with_timeline_input(),
        expected_outcome={
            "has_deadline_chains": True,
            "initial_offer_days": 30,
            "final_offer_days": 14,
        },
    ),
    TestCase(
        test_id="IN-TIME-001",
        name="Indiana has deadline chains defined",
        description="Verify IN has deadline chains for procedural events",
        category="Timeline",
        jurisdiction="IN",
        inputs=create_indiana_with_timeline_input(),
        expected_outcome={
            "has_deadline_chains": True,
            "owner_response_days": 30,
            "exceptions_window_days": 45,
        },
    ),
    
    # ----- Indiana-Specific Tests -----
    TestCase(
        test_id="IN-SPEC-001",
        name="Indiana payment election rules",
        description="Verify IN allows annual payment election for offers > $5,000",
        category="Indiana-Specific",
        jurisdiction="IN",
        inputs=create_indiana_payment_election_input(),
        expected_outcome={
            "annual_payment_available": True,
            "threshold_amount": 5000,
            "max_payment_years": 20,
            "includes_interest": True,
        },
    ),
    TestCase(
        test_id="IN-SPEC-002",
        name="Indiana private facility court findings",
        description="Verify IN requires court findings for private commercial facility takings",
        category="Indiana-Specific",
        jurisdiction="IN",
        inputs=create_indiana_base_input(),
        expected_outcome={
            "private_facility_findings_required": True,
        },
    ),
]


# =============================================================================
# TEST EXECUTION ENGINE
# =============================================================================

def load_rules(jurisdiction: str) -> dict[str, Any]:
    """Load rules for a jurisdiction from YAML file."""
    import yaml
    
    rules_path = REPO_ROOT / "rules" / f"{jurisdiction.lower()}.yaml"
    if not rules_path.exists():
        raise FileNotFoundError(f"Rules file not found: {rules_path}")
    
    with open(rules_path) as f:
        return yaml.safe_load(f)


def extract_value(rules: dict, path: str, default: Any = None) -> Any:
    """Extract a value from nested dict using dot notation."""
    keys = path.split(".")
    value = rules
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value


def validate_test_case(test_case: TestCase, rules: dict) -> TestResult:
    """
    Execute a single test case and return the result.
    """
    start_time = datetime.now()
    
    try:
        actual_outcomes = {}
        all_passed = True
        mismatches = []
        
        for key, expected_value in test_case.expected_outcome.items():
            # Map expected keys to rules structure
            key_mappings = {
                "landowner_bill_of_rights": "initiation.landowner_bill_of_rights",
                "bill_of_rights_citation": "initiation.bill_of_rights_citation",
                "resolution_required": "initiation.resolution_required",
                "resolution_body": "initiation.resolution_body",
                "initial_offer_days": "initiation.initial_offer_days",
                "final_offer_days": "initiation.final_offer_days",
                "bill_of_rights_notice_days": "initiation.bill_of_rights_notice_days",
                "owner_response_days": "initiation.initial_offer_days",
                "objection_window_days": "owner_rights.notice_periods.objection_window_days",
                "extension_days": "owner_rights.notice_periods.objection_extension_days",
                "extendable": "deadline_chains",  # Special handling
                "exceptions_window_days": "owner_rights.notice_periods.exceptions_window_days",
                "quick_take_available": "initiation.quick_take.available",
                "quick_take_type": "initiation.quick_take.type",
                "court_approval_required": "initiation.quick_take.court_approval_required",
                "compensation_standard": "compensation.constitutional_term",
                "highest_and_best_use": "compensation.highest_and_best_use",
                "severance_damages": "compensation.includes_severance",
                "loss_of_access_compensable": "compensation.loss_of_access_in_partial",
                "business_goodwill": "compensation.business_goodwill",
                "business_losses": "compensation.business_losses",
                "automatic_fees": "compensation.attorney_fees.automatic",
                "threshold_based": "compensation.attorney_fees.threshold_based",
                "economic_development_banned": "public_use.economic_development_banned",
                "tax_revenue_banned": "public_use.tax_revenue_purpose_banned",
                "reform_type": "public_use.reform_type",
                "blight_for_private": "public_use.blight_for_private",
                "blight_parcel_specific": "public_use.blight_parcel_specific",
                "blight_definition_narrowed": "public_use.blight_definition_narrowed",
                "commissioners_type": "owner_rights.commissioners_panel",
                "jury_trial_available": "owner_rights.jury_trial",
                "private_facility_findings_required": "owner_rights.private_facility_court_findings",
                "annual_payment_available": "payment_rules",  # Special handling
                "threshold_amount": "payment_rules",  # Special handling
                "max_payment_years": "payment_rules",  # Special handling
                "includes_interest": "payment_rules",  # Special handling
                "has_deadline_chains": "deadline_chains",  # Special handling
            }
            
            rules_path = key_mappings.get(key, key)
            
            # Special handling for certain keys
            if key == "extendable":
                # Check deadline chains for extendable flag
                chains = extract_value(rules, "deadline_chains", [])
                actual = False
                for chain in chains:
                    for deadline in chain.get("deadlines", []):
                        if deadline.get("extendable"):
                            actual = True
                            break
            elif key == "has_deadline_chains":
                chains = extract_value(rules, "deadline_chains", [])
                actual = len(chains) > 0
            elif key in ["annual_payment_available", "threshold_amount", "max_payment_years", "includes_interest"]:
                # Check payment rules
                payment_rules = extract_value(rules, "payment_rules", [])
                if payment_rules:
                    rule = payment_rules[0] if payment_rules else {}
                    if key == "annual_payment_available":
                        actual = len(payment_rules) > 0
                    elif key == "threshold_amount":
                        actual = rule.get("threshold_amount")
                    elif key == "max_payment_years":
                        actual = rule.get("max_payment_years")
                    elif key == "includes_interest":
                        actual = rule.get("includes_interest")
                else:
                    actual = None
            elif key == "reform_type" and expected_value == "constitutional_and_statutory":
                actual = extract_value(rules, rules_path)
                if actual == "both":
                    actual = "constitutional_and_statutory"
            elif key == "compensation_standard" and expected_value == "fair_market_value":
                actual = extract_value(rules, "compensation.base")
            elif key == "loss_of_access_compensable":
                actual = extract_value(rules, rules_path, False)
            else:
                actual = extract_value(rules, rules_path)
            
            actual_outcomes[key] = actual
            
            if actual != expected_value:
                # Handle None vs False equivalence for boolean fields
                if expected_value is False and actual is None:
                    pass  # Treat as match
                elif expected_value is True and actual is None:
                    all_passed = False
                    mismatches.append(f"{key}: expected={expected_value}, actual={actual}")
                else:
                    all_passed = False
                    mismatches.append(f"{key}: expected={expected_value}, actual={actual}")
        
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Generate input summary
        input_summary = (
            f"jurisdiction={test_case.inputs.jurisdiction}, "
            f"parcel_value=${test_case.inputs.parcel_assessed_value:,.2f}, "
            f"dispute_level={test_case.inputs.case_dispute_level}"
        )
        
        if all_passed:
            return TestResult(
                test_id=test_case.test_id,
                test_name=test_case.name,
                category=test_case.category,
                jurisdiction=test_case.jurisdiction,
                status=TestStatus.PASS,
                expected=test_case.expected_outcome,
                actual=actual_outcomes,
                duration_ms=duration_ms,
                input_summary=input_summary,
            )
        else:
            return TestResult(
                test_id=test_case.test_id,
                test_name=test_case.name,
                category=test_case.category,
                jurisdiction=test_case.jurisdiction,
                status=TestStatus.FAIL,
                expected=test_case.expected_outcome,
                actual=actual_outcomes,
                duration_ms=duration_ms,
                error_message="; ".join(mismatches),
                input_summary=input_summary,
            )
            
    except Exception as e:
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        return TestResult(
            test_id=test_case.test_id,
            test_name=test_case.name,
            category=test_case.category,
            jurisdiction=test_case.jurisdiction,
            status=TestStatus.ERROR,
            expected=test_case.expected_outcome,
            actual={},
            duration_ms=duration_ms,
            error_message=f"{type(e).__name__}: {str(e)}",
            input_summary="",
        )


def run_regression_tests() -> list[TestResult]:
    """Run all regression tests and return results."""
    results = []
    
    # Load rules for both jurisdictions
    try:
        tx_rules = load_rules("TX")
        in_rules = load_rules("IN")
    except Exception as e:
        print(f"ERROR: Failed to load rules: {e}")
        return results
    
    rules_by_jurisdiction = {
        "TX": tx_rules,
        "IN": in_rules,
    }
    
    for test_case in TEST_CASES:
        rules = rules_by_jurisdiction.get(test_case.jurisdiction)
        if rules is None:
            results.append(TestResult(
                test_id=test_case.test_id,
                test_name=test_case.name,
                category=test_case.category,
                jurisdiction=test_case.jurisdiction,
                status=TestStatus.ERROR,
                expected=test_case.expected_outcome,
                actual={},
                duration_ms=0,
                error_message=f"No rules loaded for jurisdiction: {test_case.jurisdiction}",
            ))
            continue
        
        result = validate_test_case(test_case, rules)
        results.append(result)
    
    return results


def generate_csv_report(results: list[TestResult], timestamp: datetime) -> Path:
    """Generate CSV report from test results."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
    csv_path = ARTIFACTS_DIR / f"tx_vs_in_regression_{timestamp_str}.csv"
    
    fieldnames = [
        "test_id",
        "test_name", 
        "category",
        "jurisdiction",
        "status",
        "input_summary",
        "expected",
        "actual",
        "duration_ms",
        "error_message",
    ]
    
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            writer.writerow({
                "test_id": result.test_id,
                "test_name": result.test_name,
                "category": result.category,
                "jurisdiction": result.jurisdiction,
                "status": result.status.value,
                "input_summary": result.input_summary,
                "expected": json.dumps(result.expected),
                "actual": json.dumps(result.actual),
                "duration_ms": result.duration_ms,
                "error_message": result.error_message,
            })
        
        # Summary row
        total = len(results)
        passed = sum(1 for r in results if r.status == TestStatus.PASS)
        failed = sum(1 for r in results if r.status == TestStatus.FAIL)
        errors = sum(1 for r in results if r.status == TestStatus.ERROR)
        
        writer.writerow({
            "test_id": "SUMMARY",
            "test_name": f"Total: {total}",
            "category": f"Passed: {passed}",
            "jurisdiction": f"Failed: {failed}",
            "status": f"Errors: {errors}",
            "input_summary": "",
            "expected": "",
            "actual": "",
            "duration_ms": sum(r.duration_ms for r in results),
            "error_message": "",
        })
    
    return csv_path


def print_summary(results: list[TestResult]) -> None:
    """Print human-readable summary to console."""
    total = len(results)
    passed = sum(1 for r in results if r.status == TestStatus.PASS)
    failed = sum(1 for r in results if r.status == TestStatus.FAIL)
    errors = sum(1 for r in results if r.status == TestStatus.ERROR)
    
    # Group by category
    by_category: dict[str, list[TestResult]] = {}
    for r in results:
        by_category.setdefault(r.category, []).append(r)
    
    print("\n" + "=" * 80)
    print("TEXAS vs INDIANA REGRESSION TEST RESULTS")
    print("=" * 80)
    
    for category, cat_results in sorted(by_category.items()):
        cat_passed = sum(1 for r in cat_results if r.status == TestStatus.PASS)
        cat_total = len(cat_results)
        print(f"\n{category}: {cat_passed}/{cat_total} passed")
        print("-" * 40)
        
        for r in cat_results:
            status_icon = "✓" if r.status == TestStatus.PASS else "✗" if r.status == TestStatus.FAIL else "!"
            print(f"  [{r.jurisdiction}] {status_icon} {r.test_id}: {r.test_name}")
            if r.error_message:
                print(f"           └── {r.error_message[:60]}...")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Total Tests: {total}")
    print(f"  Passed:      {passed} ({passed/total*100:.1f}%)")
    print(f"  Failed:      {failed}")
    print(f"  Errors:      {errors}")
    print("=" * 80)


def main() -> int:
    """Main entry point."""
    print("=" * 80)
    print("Texas vs Indiana Eminent Domain Regression Test Suite")
    print("=" * 80)
    
    timestamp = datetime.now(timezone.utc)
    print(f"Timestamp: {timestamp.isoformat()}")
    print(f"Test Cases: {len(TEST_CASES)}")
    print()
    
    # Run tests
    results = run_regression_tests()
    
    # Print summary
    print_summary(results)
    
    # Generate CSV
    csv_path = generate_csv_report(results, timestamp)
    print(f"\nCSV report saved to: {csv_path}")
    print(f"Relative path: {csv_path.relative_to(REPO_ROOT)}")
    
    # Return exit code
    failed = sum(1 for r in results if r.status in (TestStatus.FAIL, TestStatus.ERROR))
    if failed > 0:
        print(f"\n{failed} test(s) failed or errored")
        return 1
    
    print("\nAll tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
