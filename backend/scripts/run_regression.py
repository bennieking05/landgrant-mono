#!/usr/bin/env python3
"""
Regression Test Runner with CSV Logging

Runs all pytest test suites and outputs results to a timestamped CSV file.

Usage:
    cd backend && python -m scripts.run_regression

Output:
    artifacts/regression/regression_YYYY-MM-DD_HH-mm-ss.csv
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


# Paths relative to the repository root
REPO_ROOT = Path(__file__).parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "regression"
JSON_REPORT_PATH = BACKEND_DIR / ".report.json"


def ensure_artifacts_dir() -> None:
    """Create artifacts directory if it doesn't exist."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def run_pytest() -> tuple[int, dict]:
    """
    Run pytest with JSON report output.
    
    Returns:
        Tuple of (exit_code, report_dict)
    """
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "--json-report",
        f"--json-report-file={JSON_REPORT_PATH}",
        "-v",
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print(f"Working directory: {BACKEND_DIR}")
    print("-" * 60)
    
    result = subprocess.run(
        cmd,
        cwd=BACKEND_DIR,
        capture_output=False,  # Let output stream to console
    )
    
    # Read the JSON report
    report = {}
    if JSON_REPORT_PATH.exists():
        with open(JSON_REPORT_PATH) as f:
            report = json.load(f)
        # Clean up temporary report file
        JSON_REPORT_PATH.unlink()
    
    return result.returncode, report


def classify_suite(nodeid: str) -> str:
    """
    Classify a test into a suite based on its node ID.
    
    Examples:
        tests/test_rules_engine.py::test_foo -> unit
        tests/test_endpoints_rbac.py::test_foo -> integration
        tests/test_workflows.py::test_foo -> integration
    """
    nodeid_lower = nodeid.lower()
    
    if "rules_engine" in nodeid_lower:
        return "unit"
    elif "rbac" in nodeid_lower or "endpoints" in nodeid_lower:
        return "integration"
    elif "workflow" in nodeid_lower:
        return "integration"
    elif "e2e" in nodeid_lower or "playwright" in nodeid_lower:
        return "e2e"
    elif "smoke" in nodeid_lower:
        return "smoke"
    else:
        return "unit"


def map_outcome(outcome: str) -> str:
    """Map pytest outcome to our status format."""
    mapping = {
        "passed": "PASS",
        "failed": "FAIL",
        "skipped": "SKIP",
        "xfailed": "SKIP",  # Expected failure
        "xpassed": "PASS",  # Unexpected pass
        "error": "FAIL",
    }
    return mapping.get(outcome.lower(), "FAIL")


def extract_error_message(test: dict) -> str:
    """Extract error message from a failed test."""
    call = test.get("call", {})
    if call.get("outcome") == "failed":
        longrepr = call.get("longrepr", "")
        if isinstance(longrepr, str):
            # Take first line or truncate
            lines = longrepr.strip().split("\n")
            msg = lines[-1] if lines else ""
            # Truncate long messages
            return msg[:500] if len(msg) > 500 else msg
    return ""


def generate_csv(report: dict, run_id: str, timestamp: datetime) -> Path:
    """
    Generate CSV file from pytest JSON report.
    
    Returns:
        Path to the generated CSV file.
    """
    timestamp_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
    csv_path = ARTIFACTS_DIR / f"regression_{timestamp_str}.csv"
    
    tests = report.get("tests", [])
    
    # Counters for summary
    total = len(tests)
    passed = 0
    failed = 0
    skipped = 0
    total_duration_ms = 0
    
    rows = []
    
    for test in tests:
        nodeid = test.get("nodeid", "")
        outcome = test.get("outcome", "unknown")
        
        # Duration is in seconds, convert to ms
        duration_s = test.get("call", {}).get("duration", 0) or test.get("duration", 0)
        duration_ms = int(duration_s * 1000)
        total_duration_ms += duration_ms
        
        status = map_outcome(outcome)
        if status == "PASS":
            passed += 1
        elif status == "FAIL":
            failed += 1
        else:
            skipped += 1
        
        # Extract test name from nodeid (e.g., tests/test_foo.py::test_bar -> test_bar)
        test_name = nodeid.split("::")[-1] if "::" in nodeid else nodeid
        
        rows.append({
            "run_id": run_id,
            "timestamp_utc": timestamp.isoformat(),
            "suite": classify_suite(nodeid),
            "test_name": test_name,
            "status": status,
            "duration_ms": duration_ms,
            "error_message": extract_error_message(test),
        })
    
    # Write CSV
    fieldnames = ["run_id", "timestamp_utc", "suite", "test_name", "status", "duration_ms", "error_message"]
    
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
        # Write summary row
        summary_timestamp = datetime.now(timezone.utc).isoformat()
        writer.writerow({
            "run_id": run_id,
            "timestamp_utc": summary_timestamp,
            "suite": "SUMMARY",
            "test_name": f"total={total}",
            "status": f"passed={passed}",
            "duration_ms": f"failed={failed}",
            "error_message": f"skipped={skipped},total_duration_ms={total_duration_ms}",
        })
    
    return csv_path


def print_summary(report: dict) -> None:
    """Print a human-readable summary to console."""
    summary = report.get("summary", {})
    
    print("\n" + "=" * 60)
    print("REGRESSION TEST SUMMARY")
    print("=" * 60)
    print(f"  Total:   {summary.get('total', 0)}")
    print(f"  Passed:  {summary.get('passed', 0)}")
    print(f"  Failed:  {summary.get('failed', 0)}")
    print(f"  Skipped: {summary.get('skipped', 0)}")
    
    duration = report.get("duration", 0)
    print(f"  Duration: {duration:.2f}s")
    print("=" * 60)


def main() -> int:
    """
    Main entry point for the regression runner.
    
    Returns:
        Exit code (0 for success, non-zero for failures)
    """
    print("=" * 60)
    print("LandRight Regression Test Runner")
    print("=" * 60)
    
    # Generate unique run ID and timestamp
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(timezone.utc)
    
    print(f"Run ID: {run_id}")
    print(f"Timestamp: {timestamp.isoformat()}")
    print()
    
    # Ensure output directory exists
    ensure_artifacts_dir()
    
    # Run pytest
    exit_code, report = run_pytest()
    
    if not report:
        print("\nERROR: Failed to generate pytest JSON report")
        print("Make sure pytest-json-report is installed:")
        print("  pip install pytest-json-report")
        return 1
    
    # Generate CSV
    csv_path = generate_csv(report, run_id, timestamp)
    
    # Print summary
    print_summary(report)
    
    print(f"\nCSV report saved to: {csv_path}")
    print(f"Relative path: {csv_path.relative_to(REPO_ROOT)}")
    
    # Return non-zero if any tests failed
    if exit_code != 0:
        print(f"\nExit code: {exit_code} (tests failed)")
    else:
        print("\nAll tests passed!")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
