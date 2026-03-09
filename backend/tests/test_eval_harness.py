"""Tests for Evaluation Harness."""

import pytest

from app.services.eval_harness import (
    EvalHarness,
    GoldenTestCase,
    generate_uat_checklist,
    GOLDEN_TEST_CASES,
)


@pytest.fixture
def harness():
    """Create an evaluation harness."""
    return EvalHarness()


def test_list_test_cases(harness):
    """Test listing test cases."""
    all_cases = harness.list_test_cases()
    
    assert len(all_cases) > 0
    
    # Filter by state
    tx_cases = harness.list_test_cases(state="TX")
    assert len(tx_cases) > 0
    assert all(c.state == "TX" for c in tx_cases)
    
    # Filter by category
    deadline_cases = harness.list_test_cases(category="deadline")
    assert all(c.category == "deadline" for c in deadline_cases)


def test_get_test_case(harness):
    """Test getting a specific test case."""
    case = harness.get_test_case("tx_001")
    
    assert case is not None
    assert case.state == "TX"
    assert case.name == "TX Bill of Rights Timing"


def test_run_deadline_test(harness):
    """Test running a deadline test."""
    case = harness.get_test_case("tx_002")  # Initial offer wait
    result = harness.run_deadline_test(case)
    
    assert result.test_id == "tx_002"
    assert result.category == "deadline"
    assert result.execution_time_ms >= 0
    # The test may pass or fail depending on implementation
    # We're checking it runs without error


def test_run_clause_test(harness):
    """Test running a clause test."""
    case = harness.get_test_case("tx_003")  # TX required clauses
    result = harness.run_clause_test(case)
    
    assert result.test_id == "tx_003"
    assert result.category == "clause"
    assert isinstance(result.expected, list)
    assert isinstance(result.actual, (list, set))


def test_run_compliance_test(harness):
    """Test running a compliance test."""
    case = harness.get_test_case("ca_001")  # CA Resolution requirement
    result = harness.run_compliance_test(case)
    
    assert result.test_id == "ca_001"
    assert result.category == "compliance"


def test_run_all_tests(harness):
    """Test running all tests."""
    report = harness.run_all_tests()
    
    assert report.total_tests > 0
    assert report.passed + report.failed == report.total_tests
    assert len(report.results) == report.total_tests
    assert report.id.startswith("eval_")


def test_run_all_tests_filtered(harness):
    """Test running tests for a specific state."""
    report = harness.run_all_tests(state="TX")
    
    # Should only include TX tests
    assert all(r.test_id.startswith("tx_") for r in report.results)


def test_validate_state_pack(harness):
    """Test state pack validation."""
    result = harness.validate_state_pack("TX")
    
    assert result["state"] == "TX"
    assert result["tests_run"] > 0
    assert "pack_valid" in result
    assert "critical_failures" in result


def test_golden_test_cases_structure():
    """Test that golden test cases are well-formed."""
    for case in GOLDEN_TEST_CASES:
        # Required fields
        assert case.id
        assert case.name
        assert case.state
        assert case.category in ["deadline", "clause", "compliance", "citation"]
        assert case.scenario
        
        # Category-specific expected outputs
        if case.category == "deadline":
            assert case.expected_deadlines is not None
        elif case.category == "clause":
            assert case.expected_clauses is not None
        elif case.category == "compliance":
            assert case.expected_risk_level is not None


def test_generate_uat_checklist():
    """Test UAT checklist generation."""
    checklist = generate_uat_checklist("TX")
    
    # Should be markdown
    assert "# UAT Checklist for TX" in checklist
    assert "## Test Cases" in checklist
    
    # Should contain test cases
    assert "TX Bill of Rights Timing" in checklist
    assert "Expected Deadlines" in checklist or "Expected Clauses" in checklist


def test_eval_report_summary():
    """Test that report summary is accurate."""
    harness = EvalHarness()
    report = harness.run_all_tests()
    
    expected_summary = f"{report.passed}/{report.total_tests} tests passed"
    assert expected_summary in report.summary


def test_multiple_states_coverage():
    """Test that multiple states have test coverage."""
    harness = EvalHarness()
    
    states_with_tests = set()
    for case in harness.list_test_cases():
        states_with_tests.add(case.state)
    
    # Should have tests for multiple states
    expected_states = {"TX", "CA", "FL", "MI", "MO"}
    assert expected_states.issubset(states_with_tests)


def test_test_result_details():
    """Test that test results include sufficient details."""
    harness = EvalHarness()
    case = harness.get_test_case("tx_001")
    result = harness.run_deadline_test(case)
    
    # Should have detailed result
    assert result.expected is not None
    assert result.actual is not None
    # If failed, should have diff
    if not result.passed:
        assert result.diff is not None or result.expected != result.actual
