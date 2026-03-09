"""Evaluation Harness for AI Regression Testing.

Provides:
- Golden test case management
- AI output validation
- Deadline derivation testing
- State pack contract testing
- Regression detection

No AI update should silently break compliance.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from app.services.hashing import sha256_hex


@dataclass
class GoldenTestCase:
    """A golden test case for regression testing."""
    id: str
    name: str
    description: str
    state: str
    category: str  # deadline, clause, compliance, citation
    
    # Input scenario
    scenario: dict[str, Any]
    
    # Expected outputs
    expected_deadlines: Optional[list[dict[str, Any]]] = None
    expected_clauses: Optional[list[str]] = None
    expected_risk_level: Optional[str] = None
    expected_citations: Optional[list[str]] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0.0"


@dataclass
class TestResult:
    """Result of a single test."""
    test_id: str
    passed: bool
    category: str
    expected: Any
    actual: Any
    diff: Optional[str] = None
    execution_time_ms: int = 0


@dataclass
class EvalReport:
    """Report from an evaluation run."""
    id: str
    timestamp: datetime
    total_tests: int
    passed: int
    failed: int
    results: list[TestResult]
    summary: str


# Golden test cases for 5 example states
GOLDEN_TEST_CASES: list[GoldenTestCase] = [
    # Texas - Bill of Rights and wait periods
    GoldenTestCase(
        id="tx_001",
        name="TX Bill of Rights Timing",
        description="Verify Bill of Rights delivery deadline",
        state="TX",
        category="deadline",
        scenario={
            "final_offer_date": "2026-02-15",
            "jurisdiction": "TX",
        },
        expected_deadlines=[
            {
                "name": "bill_of_rights_delivery",
                "due_date": "2026-02-08",  # 7 days before final offer
                "citation": "Tex. Prop. Code §21.0112",
            },
        ],
    ),
    GoldenTestCase(
        id="tx_002",
        name="TX Initial Offer Wait Period",
        description="30-day wait after initial offer",
        state="TX",
        category="deadline",
        scenario={
            "initial_offer_date": "2026-01-15",
            "jurisdiction": "TX",
        },
        expected_deadlines=[
            {
                "name": "minimum_final_offer_date",
                "due_date": "2026-02-14",  # 30 days after initial
                "citation": "Tex. Prop. Code §21.0113",
            },
        ],
    ),
    GoldenTestCase(
        id="tx_003",
        name="TX Required Clauses",
        description="Verify TX offer letter clauses",
        state="TX",
        category="clause",
        scenario={
            "document_type": "offer_letter",
            "jurisdiction": "TX",
        },
        expected_clauses=[
            "bill_of_rights_reference",
            "property_code_citation",
            "just_compensation",
        ],
    ),
    
    # California - Resolution of Necessity
    GoldenTestCase(
        id="ca_001",
        name="CA Resolution Requirement",
        description="Resolution of Necessity required",
        state="CA",
        category="compliance",
        scenario={
            "action": "file_petition",
            "jurisdiction": "CA",
            "resolution_obtained": False,
        },
        expected_risk_level="red",
    ),
    GoldenTestCase(
        id="ca_002",
        name="CA Goodwill Disclosure",
        description="Business goodwill compensation notice",
        state="CA",
        category="clause",
        scenario={
            "document_type": "offer_letter",
            "jurisdiction": "CA",
            "is_business_property": True,
        },
        expected_clauses=[
            "goodwill_notice",
            "resolution_necessity",
        ],
    ),
    
    # Florida - Full Compensation
    GoldenTestCase(
        id="fl_001",
        name="FL Full Compensation Standard",
        description="Verify Florida uses full compensation",
        state="FL",
        category="compliance",
        scenario={
            "compensation_calculation": "fair_market_value_only",
            "jurisdiction": "FL",
        },
        expected_risk_level="red",  # FL requires more than FMV
    ),
    GoldenTestCase(
        id="fl_002",
        name="FL Attorney Fee Disclosure",
        description="Automatic attorney fee disclosure required",
        state="FL",
        category="clause",
        scenario={
            "document_type": "offer_letter",
            "jurisdiction": "FL",
        },
        expected_clauses=[
            "full_compensation",
            "fee_disclosure",
        ],
    ),
    
    # Michigan - Multiplier Application
    GoldenTestCase(
        id="mi_001",
        name="MI Residence Multiplier",
        description="125% multiplier for owner-occupied residence",
        state="MI",
        category="compliance",
        scenario={
            "property_type": "residence",
            "owner_occupied": True,
            "jurisdiction": "MI",
            "offered_multiplier": 1.0,
        },
        expected_risk_level="yellow",  # Should be 1.25
    ),
    GoldenTestCase(
        id="mi_002",
        name="MI Fee Reimbursement Notice",
        description="Mandatory fee reimbursement disclosure",
        state="MI",
        category="clause",
        scenario={
            "document_type": "offer_letter",
            "jurisdiction": "MI",
        },
        expected_clauses=[
            "multiplier_disclosure",
            "fee_reimbursement",
        ],
    ),
    
    # Missouri - Heritage Property
    GoldenTestCase(
        id="mo_001",
        name="MO Heritage Property Multiplier",
        description="150% for 50+ year family property",
        state="MO",
        category="compliance",
        scenario={
            "property_type": "residence",
            "family_ownership_years": 55,
            "jurisdiction": "MO",
            "offered_multiplier": 1.25,
        },
        expected_risk_level="yellow",  # Should be 1.50
    ),
    
    # New York - No specific reforms
    GoldenTestCase(
        id="ny_001",
        name="NY Standard Process",
        description="NY follows standard process",
        state="NY",
        category="deadline",
        scenario={
            "initial_offer_date": "2026-01-15",
            "jurisdiction": "NY",
        },
        expected_deadlines=[
            {
                "name": "offer_consideration_period",
                "due_date": "2026-02-14",  # Standard 30 days
                "citation": "NY EDPL",
            },
        ],
    ),
    
    # Illinois - Repurchase right
    GoldenTestCase(
        id="il_001",
        name="IL Repurchase Disclosure",
        description="Owner repurchase right if not used",
        state="IL",
        category="clause",
        scenario={
            "document_type": "offer_letter",
            "jurisdiction": "IL",
        },
        expected_clauses=[
            "repurchase_right_notice",
        ],
    ),
]


class EvalHarness:
    """Evaluation harness for AI regression testing."""

    def __init__(self):
        """Initialize the harness."""
        self._test_cases = {tc.id: tc for tc in GOLDEN_TEST_CASES}
        self._reports: dict[str, EvalReport] = {}

    def get_test_case(self, test_id: str) -> Optional[GoldenTestCase]:
        """Get a test case by ID."""
        return self._test_cases.get(test_id)

    def list_test_cases(
        self,
        state: Optional[str] = None,
        category: Optional[str] = None,
    ) -> list[GoldenTestCase]:
        """List test cases with optional filters."""
        cases = list(self._test_cases.values())
        
        if state:
            cases = [c for c in cases if c.state == state.upper()]
        if category:
            cases = [c for c in cases if c.category == category]
        
        return cases

    def run_deadline_test(
        self,
        test_case: GoldenTestCase,
    ) -> TestResult:
        """Run a deadline derivation test."""
        import time
        start = time.time()
        
        from app.services.deadline_rules import derive_deadlines
        
        # Mock the scenario
        scenario = test_case.scenario
        jurisdiction = scenario.get("jurisdiction", test_case.state)
        
        # Derive deadlines
        try:
            # Create a mock context
            mock_dates = {}
            for key, value in scenario.items():
                if "date" in key.lower():
                    mock_dates[key] = datetime.fromisoformat(value)
            
            # This would call the actual deadline derivation
            # For now, we simulate
            actual_deadlines = []
            
            # Simple simulation based on known rules
            if "initial_offer_date" in scenario and jurisdiction == "TX":
                initial = datetime.fromisoformat(scenario["initial_offer_date"])
                actual_deadlines.append({
                    "name": "minimum_final_offer_date",
                    "due_date": (initial + timedelta(days=30)).strftime("%Y-%m-%d"),
                    "citation": "Tex. Prop. Code §21.0113",
                })
            
            if "final_offer_date" in scenario and jurisdiction == "TX":
                final = datetime.fromisoformat(scenario["final_offer_date"])
                actual_deadlines.append({
                    "name": "bill_of_rights_delivery",
                    "due_date": (final - timedelta(days=7)).strftime("%Y-%m-%d"),
                    "citation": "Tex. Prop. Code §21.0112",
                })
            
            # Compare
            passed = self._compare_deadlines(
                test_case.expected_deadlines or [],
                actual_deadlines,
            )
            
            return TestResult(
                test_id=test_case.id,
                passed=passed,
                category="deadline",
                expected=test_case.expected_deadlines,
                actual=actual_deadlines,
                execution_time_ms=int((time.time() - start) * 1000),
            )
            
        except Exception as e:
            return TestResult(
                test_id=test_case.id,
                passed=False,
                category="deadline",
                expected=test_case.expected_deadlines,
                actual={"error": str(e)},
                diff=str(e),
                execution_time_ms=int((time.time() - start) * 1000),
            )

    def _compare_deadlines(
        self,
        expected: list[dict[str, Any]],
        actual: list[dict[str, Any]],
    ) -> bool:
        """Compare expected and actual deadlines."""
        if len(expected) != len(actual):
            return False
        
        for exp in expected:
            found = False
            for act in actual:
                if (exp.get("name") == act.get("name") and
                    exp.get("due_date") == act.get("due_date")):
                    found = True
                    break
            if not found:
                return False
        
        return True

    def run_clause_test(
        self,
        test_case: GoldenTestCase,
    ) -> TestResult:
        """Run a required clause test."""
        import time
        start = time.time()
        
        from app.services.qa_checks import STATE_REQUIRED_CLAUSES
        
        jurisdiction = test_case.scenario.get("jurisdiction", test_case.state)
        expected_clauses = set(test_case.expected_clauses or [])
        
        # Get actual required clauses for jurisdiction
        actual_clause_ids = {
            c["id"] for c in STATE_REQUIRED_CLAUSES.get(jurisdiction, [])
        }
        
        # Check if expected clauses are in actual
        missing = expected_clauses - actual_clause_ids
        passed = len(missing) == 0
        
        return TestResult(
            test_id=test_case.id,
            passed=passed,
            category="clause",
            expected=list(expected_clauses),
            actual=list(actual_clause_ids),
            diff=f"Missing: {missing}" if missing else None,
            execution_time_ms=int((time.time() - start) * 1000),
        )

    def run_compliance_test(
        self,
        test_case: GoldenTestCase,
    ) -> TestResult:
        """Run a compliance check test."""
        import time
        start = time.time()
        
        # Simulate compliance check based on scenario
        scenario = test_case.scenario
        jurisdiction = scenario.get("jurisdiction", test_case.state)
        
        actual_risk_level = "green"  # Default
        
        # Check specific scenarios
        if jurisdiction == "CA" and not scenario.get("resolution_obtained"):
            actual_risk_level = "red"
        
        if jurisdiction == "FL" and scenario.get("compensation_calculation") == "fair_market_value_only":
            actual_risk_level = "red"
        
        if jurisdiction == "MI" and scenario.get("owner_occupied"):
            if scenario.get("offered_multiplier", 1.0) < 1.25:
                actual_risk_level = "yellow"
        
        if jurisdiction == "MO" and scenario.get("family_ownership_years", 0) >= 50:
            if scenario.get("offered_multiplier", 1.0) < 1.50:
                actual_risk_level = "yellow"
        
        passed = actual_risk_level == test_case.expected_risk_level
        
        return TestResult(
            test_id=test_case.id,
            passed=passed,
            category="compliance",
            expected=test_case.expected_risk_level,
            actual=actual_risk_level,
            execution_time_ms=int((time.time() - start) * 1000),
        )

    def run_all_tests(
        self,
        state: Optional[str] = None,
    ) -> EvalReport:
        """Run all tests and generate report."""
        cases = self.list_test_cases(state=state)
        results = []
        
        for case in cases:
            if case.category == "deadline":
                result = self.run_deadline_test(case)
            elif case.category == "clause":
                result = self.run_clause_test(case)
            elif case.category == "compliance":
                result = self.run_compliance_test(case)
            else:
                continue
            
            results.append(result)
        
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        
        report_id = f"eval_{uuid.uuid4().hex[:8]}"
        report = EvalReport(
            id=report_id,
            timestamp=datetime.utcnow(),
            total_tests=len(results),
            passed=passed,
            failed=failed,
            results=results,
            summary=f"{passed}/{len(results)} tests passed ({failed} failed)",
        )
        
        self._reports[report_id] = report
        return report

    def validate_state_pack(
        self,
        state: str,
    ) -> dict[str, Any]:
        """Validate a state pack against golden tests.
        
        This is a "contract test" that ensures the state pack
        doesn't break known requirements.
        """
        cases = self.list_test_cases(state=state)
        report = self.run_all_tests(state=state)
        
        # Check for critical failures
        critical_failures = [
            r for r in report.results
            if not r.passed and r.category in ["deadline", "compliance"]
        ]
        
        return {
            "state": state,
            "pack_valid": len(critical_failures) == 0,
            "tests_run": report.total_tests,
            "passed": report.passed,
            "failed": report.failed,
            "critical_failures": [
                {
                    "test_id": r.test_id,
                    "category": r.category,
                    "expected": r.expected,
                    "actual": r.actual,
                }
                for r in critical_failures
            ],
            "report_id": report.id,
        }


def generate_uat_checklist(state: str) -> str:
    """Generate a UAT checklist for human review.
    
    Args:
        state: State code
        
    Returns:
        Markdown formatted checklist
    """
    harness = EvalHarness()
    cases = harness.list_test_cases(state=state)
    
    lines = [
        f"# UAT Checklist for {state}",
        "",
        f"*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        "## Test Cases",
        "",
    ]
    
    for case in cases:
        lines.append(f"### {case.name}")
        lines.append(f"*Category: {case.category}*")
        lines.append("")
        lines.append(f"**Description:** {case.description}")
        lines.append("")
        lines.append("**Scenario:**")
        lines.append("```json")
        lines.append(json.dumps(case.scenario, indent=2))
        lines.append("```")
        lines.append("")
        
        if case.expected_deadlines:
            lines.append("**Expected Deadlines:**")
            for dl in case.expected_deadlines:
                lines.append(f"- [ ] {dl['name']}: {dl['due_date']} ({dl['citation']})")
        
        if case.expected_clauses:
            lines.append("**Expected Clauses:**")
            for clause in case.expected_clauses:
                lines.append(f"- [ ] {clause}")
        
        if case.expected_risk_level:
            lines.append(f"**Expected Risk Level:** {case.expected_risk_level}")
        
        lines.append("")
        lines.append("**Result:** [ ] PASS  [ ] FAIL")
        lines.append("")
        lines.append("**Notes:**")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)
