#!/usr/bin/env python3
"""Generate state rule packs from the States requirements.md documentation.

This script reads the comprehensive state requirements document and generates
YAML rule packs for priority states using Gemini for intelligent extraction.

Priority states (by eminent domain volume):
OH, GA, VA, NC, SC, PA, NJ, NY, AZ, NV, CO, IL, MN, WI

Usage:
    python -m scripts.generate_state_packs [--state XX] [--all] [--validate] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Paths
ROOT_DIR = Path(__file__).resolve().parents[2]
RULES_DIR = ROOT_DIR / "rules"
SCHEMA_PATH = RULES_DIR / "schema" / "state_rules.schema.json"
REQUIREMENTS_PATH = ROOT_DIR / "States requitments.md"

# Priority states to generate
PRIORITY_STATES = [
    "OH",  # Ohio
    "GA",  # Georgia
    "VA",  # Virginia
    "NC",  # North Carolina
    "SC",  # South Carolina
    "PA",  # Pennsylvania
    "NJ",  # New Jersey
    "NY",  # New York
    "AZ",  # Arizona
    "NV",  # Nevada
    "CO",  # Colorado
    "IL",  # Illinois
    "MN",  # Minnesota
    "WI",  # Wisconsin
]

# State names mapping
STATE_NAMES = {
    "OH": "Ohio",
    "GA": "Georgia",
    "VA": "Virginia",
    "NC": "North Carolina",
    "SC": "South Carolina",
    "PA": "Pennsylvania",
    "NJ": "New Jersey",
    "NY": "New York",
    "AZ": "Arizona",
    "NV": "Nevada",
    "CO": "Colorado",
    "IL": "Illinois",
    "MN": "Minnesota",
    "WI": "Wisconsin",
}


@dataclass
class StateRequirements:
    """Extracted requirements for a state."""
    state_code: str
    state_name: str
    raw_text: str
    initiation: dict[str, Any] = field(default_factory=dict)
    compensation: dict[str, Any] = field(default_factory=dict)
    owner_rights: dict[str, Any] = field(default_factory=dict)
    public_use: dict[str, Any] = field(default_factory=dict)
    citations: dict[str, Any] = field(default_factory=dict)
    deadline_chains: list[dict] = field(default_factory=list)
    triggers: list[dict] = field(default_factory=list)


def load_schema() -> dict[str, Any]:
    """Load the JSON schema for validation."""
    if not SCHEMA_PATH.exists():
        logger.warning(f"Schema not found at {SCHEMA_PATH}")
        return {}
    
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def extract_state_section(content: str, state_name: str) -> Optional[str]:
    """Extract the section for a specific state from the requirements doc.
    
    Args:
        content: Full document content
        state_name: Full state name (e.g., "Ohio")
        
    Returns:
        Section text or None if not found
    """
    # Look for state header patterns
    patterns = [
        rf"##\s*{state_name}\s*\n(.*?)(?=##\s*[A-Z]|\Z)",
        rf"###\s*{state_name}\s*\n(.*?)(?=###\s*[A-Z]|\Z)",
        rf"\*\*{state_name}\*\*\s*\n(.*?)(?=\*\*[A-Z]|\Z)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # Try simpler pattern - look for state name followed by content
    pattern = rf"{state_name}[\s\S]*?(?=\n\n[A-Z][a-z]+\s*\n|\Z)"
    match = re.search(pattern, content, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    
    return None


def parse_requirements_manually(state_code: str, raw_text: str) -> StateRequirements:
    """Parse requirements using regex patterns (fallback when AI unavailable).
    
    This extracts common patterns from the requirements text.
    """
    state_name = STATE_NAMES.get(state_code, state_code)
    reqs = StateRequirements(
        state_code=state_code,
        state_name=state_name,
        raw_text=raw_text,
    )
    
    text_lower = raw_text.lower()
    
    # Extract citations
    citation_patterns = [
        (r"([A-Z]{2,3}\.\s*Code\s*§\s*[\d\-\.]+)", "primary"),
        (r"(Const\.\s*Art\.\s*[IVX]+\s*§\s*\d+)", "constitution"),
        (r"(\d+\s+[A-Z][a-z]+\.\s*[\d\-]+)", "additional"),
    ]
    
    for pattern, key in citation_patterns:
        matches = re.findall(pattern, raw_text)
        if matches:
            if key == "additional":
                reqs.citations[key] = matches[:5]
            else:
                reqs.citations[key] = matches[0] if matches else None
    
    # Extract initiation requirements
    reqs.initiation = {
        "landowner_bill_of_rights": "bill of rights" in text_lower,
        "pre_condemnation_offer_required": "offer" in text_lower and ("required" in text_lower or "must" in text_lower),
        "appraisal_based_offer": "appraisal" in text_lower,
        "good_faith_negotiation": "good faith" in text_lower or "negotiate" in text_lower,
        "resolution_required": "resolution" in text_lower and "necessity" in text_lower,
        "public_hearing_required": "public hearing" in text_lower,
    }
    
    # Extract days patterns
    days_pattern = r"(\d+)\s*days?"
    day_matches = re.findall(days_pattern, text_lower)
    if day_matches:
        days = [int(d) for d in day_matches]
        if days:
            reqs.initiation["initial_offer_days"] = min(d for d in days if d >= 14) if any(d >= 14 for d in days) else 30
    
    # Quick-take
    quick_take_available = any(term in text_lower for term in ["quick take", "quick-take", "immediate possession", "deposit and take"])
    reqs.initiation["quick_take"] = {
        "available": quick_take_available,
        "type": "deposit_and_possession" if quick_take_available else None,
        "court_approval_required": "court approval" in text_lower if quick_take_available else None,
        "deposit_required": "deposit" in text_lower if quick_take_available else None,
    }
    
    # Extract compensation rules
    reqs.compensation = {
        "base": "fair_market_value",
        "highest_and_best_use": "highest and best" in text_lower,
        "includes_severance": "severance" in text_lower,
        "business_goodwill": "goodwill" in text_lower and "compensable" in text_lower,
        "business_losses": "business loss" in text_lower,
        "lost_access": "loss of access" in text_lower or "lost access" in text_lower,
        "attorney_fees": {
            "automatic": "automatic" in text_lower and "attorney" in text_lower,
            "threshold_based": "threshold" in text_lower or "exceeds" in text_lower,
        },
        "relocation_assistance": "relocation" in text_lower,
    }
    
    # Check for multipliers
    mult_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:percent|%)\s*(?:multiplier|premium|additional)", text_lower)
    if mult_match:
        mult_value = float(mult_match.group(1)) / 100 + 1
        if "residence" in text_lower or "homeowner" in text_lower:
            reqs.compensation["residence_multiplier"] = mult_value
    
    # Extract owner rights
    reqs.owner_rights = {
        "jury_trial": "jury" in text_lower and "trial" in text_lower,
        "bench_trial": "bench trial" in text_lower or "judge determines" in text_lower,
        "public_use_challenge": "challenge" in text_lower and "public use" in text_lower,
        "necessity_challenge": "necessity" in text_lower and "challenge" in text_lower,
        "commissioners_panel": "commissioners" in text_lower or "special masters" in text_lower,
    }
    
    if "commissioners" in text_lower:
        if "three" in text_lower or "3" in text_lower:
            reqs.owner_rights["commissioners_panel"] = "three_commissioners"
        else:
            reqs.owner_rights["commissioners_panel"] = "special_commissioners"
    
    # Extract public use limitations
    reqs.public_use = {
        "economic_development_banned": (
            "economic development" in text_lower and 
            ("banned" in text_lower or "prohibited" in text_lower or "cannot" in text_lower)
        ),
        "tax_revenue_purpose_banned": "tax revenue" in text_lower and ("banned" in text_lower or "prohibited" in text_lower),
        "blight_for_private": "restricted" if "blight" in text_lower and "private" in text_lower else "allowed",
        "blight_parcel_specific": "parcel" in text_lower and "specific" in text_lower,
    }
    
    # Reform year detection
    reform_match = re.search(r"(?:20\d\d|19\d\d)\s*(?:reform|amendment|kelo)", text_lower)
    if reform_match:
        year_match = re.search(r"(20\d\d|19\d\d)", reform_match.group(0))
        if year_match:
            reqs.public_use["post_kelo_reform_year"] = int(year_match.group(1))
            reqs.public_use["reform_type"] = "statutory"
    
    return reqs


async def parse_requirements_with_ai(state_code: str, raw_text: str) -> StateRequirements:
    """Parse requirements using Gemini AI for intelligent extraction.
    
    Falls back to manual parsing if AI is unavailable.
    """
    try:
        from app.services.ai_pipeline import get_gemini_model
        
        model = get_gemini_model()
        if model is None:
            logger.info("Gemini model unavailable, using manual parsing")
            return parse_requirements_manually(state_code, raw_text)
        
        state_name = STATE_NAMES.get(state_code, state_code)
        
        prompt = f"""Extract eminent domain requirements for {state_name} ({state_code}) from the following text.

Return a JSON object with these sections:
1. citations: primary statute, constitutional provision, additional citations
2. initiation: bill of rights required, pre-condemnation offer, appraisal required, good faith negotiation, resolution required, public hearing required, initial offer days, final offer days, quick-take details
3. compensation: base standard, highest and best use, severance damages, business goodwill, attorney fees rules, relocation assistance, any multipliers
4. owner_rights: jury trial, bench trial, commissioners panel type, public use challenge, necessity challenge, notice periods
5. public_use: economic development banned, tax revenue purpose banned, blight for private transfer, post-kelo reform year and type

TEXT:
{raw_text[:8000]}

Return ONLY valid JSON, no explanation."""

        response = await model.generate_content_async(prompt)
        
        if response.candidates and len(response.candidates) > 0:
            text = response.candidates[0].content.parts[0].text
            
            # Parse JSON from response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(text)
            
            return StateRequirements(
                state_code=state_code,
                state_name=state_name,
                raw_text=raw_text,
                citations=data.get("citations", {}),
                initiation=data.get("initiation", {}),
                compensation=data.get("compensation", {}),
                owner_rights=data.get("owner_rights", {}),
                public_use=data.get("public_use", {}),
            )
        
    except Exception as e:
        logger.warning(f"AI parsing failed for {state_code}: {e}")
    
    return parse_requirements_manually(state_code, raw_text)


def generate_yaml_content(reqs: StateRequirements) -> str:
    """Generate YAML content from extracted requirements."""
    
    # Build the rule pack structure
    rule_pack = {
        "version": "1.0.0",
        "jurisdiction": reqs.state_code,
        "extends": "base",
        "maintainer": "AI Generated - Review Required",
        "description": f"{reqs.state_name} eminent domain procedural rules",
    }
    
    # Add citations
    if reqs.citations:
        rule_pack["citations"] = {
            "primary": reqs.citations.get("primary", f"{reqs.state_code} Code"),
            "constitution": reqs.citations.get("constitution"),
            "additional": reqs.citations.get("additional", []),
        }
    
    # Add initiation section
    if reqs.initiation:
        rule_pack["initiation"] = {
            "landowner_bill_of_rights": reqs.initiation.get("landowner_bill_of_rights", False),
            "pre_condemnation_offer_required": reqs.initiation.get("pre_condemnation_offer_required", True),
            "appraisal_based_offer": reqs.initiation.get("appraisal_based_offer", True),
            "good_faith_negotiation": reqs.initiation.get("good_faith_negotiation", True),
            "resolution_required": reqs.initiation.get("resolution_required", False),
            "public_hearing_required": reqs.initiation.get("public_hearing_required", False),
            "initial_offer_days": reqs.initiation.get("initial_offer_days", 30),
            "final_offer_days": reqs.initiation.get("final_offer_days", 14),
        }
        
        # Add quick-take if present
        quick_take = reqs.initiation.get("quick_take", {})
        if quick_take:
            rule_pack["initiation"]["quick_take"] = {
                "available": quick_take.get("available", False),
                "type": quick_take.get("type"),
                "court_approval_required": quick_take.get("court_approval_required"),
                "deposit_required": quick_take.get("deposit_required"),
            }
    
    # Add compensation section
    if reqs.compensation:
        rule_pack["compensation"] = {
            "base": reqs.compensation.get("base", "fair_market_value"),
            "highest_and_best_use": reqs.compensation.get("highest_and_best_use", True),
            "includes_severance": reqs.compensation.get("includes_severance", True),
            "business_goodwill": reqs.compensation.get("business_goodwill", False),
            "business_losses": reqs.compensation.get("business_losses", False),
            "lost_access": reqs.compensation.get("lost_access", False),
            "relocation_assistance": reqs.compensation.get("relocation_assistance", True),
        }
        
        # Add residence multiplier if present
        if reqs.compensation.get("residence_multiplier"):
            rule_pack["compensation"]["residence_multiplier"] = reqs.compensation["residence_multiplier"]
        
        # Add attorney fees
        attorney_fees = reqs.compensation.get("attorney_fees", {})
        if attorney_fees:
            rule_pack["compensation"]["attorney_fees"] = {
                "automatic": attorney_fees.get("automatic", False),
                "threshold_based": attorney_fees.get("threshold_based", False),
            }
    
    # Add owner rights section
    if reqs.owner_rights:
        rule_pack["owner_rights"] = {
            "jury_trial": reqs.owner_rights.get("jury_trial", True),
            "bench_trial": reqs.owner_rights.get("bench_trial", False),
            "commissioners_panel": reqs.owner_rights.get("commissioners_panel"),
            "public_use_challenge": reqs.owner_rights.get("public_use_challenge", True),
            "necessity_challenge": reqs.owner_rights.get("necessity_challenge", True),
        }
        
        # Add notice periods if present
        notice_periods = reqs.owner_rights.get("notice_periods", {})
        if notice_periods:
            rule_pack["owner_rights"]["notice_periods"] = notice_periods
    
    # Add public use section
    if reqs.public_use:
        rule_pack["public_use"] = {
            "economic_development_banned": reqs.public_use.get("economic_development_banned", False),
            "tax_revenue_purpose_banned": reqs.public_use.get("tax_revenue_purpose_banned", False),
            "blight_for_private": reqs.public_use.get("blight_for_private", "allowed"),
            "blight_parcel_specific": reqs.public_use.get("blight_parcel_specific", False),
        }
        
        # Add reform info if present
        if reqs.public_use.get("post_kelo_reform_year"):
            rule_pack["public_use"]["post_kelo_reform_year"] = reqs.public_use["post_kelo_reform_year"]
            rule_pack["public_use"]["reform_type"] = reqs.public_use.get("reform_type", "statutory")
    
    # Add placeholder deadline chains
    rule_pack["deadline_chains"] = [
        {
            "anchor_event": "offer_served",
            "description": "Deadlines triggered by serving the initial offer",
            "deadlines": [
                {
                    "id": "owner_response_deadline",
                    "description": "Owner must respond to offer",
                    "offset_days": rule_pack.get("initiation", {}).get("initial_offer_days", 30),
                    "direction": "after",
                    "citation": rule_pack.get("citations", {}).get("primary", f"{reqs.state_code} Code"),
                    "type": "deadline",
                }
            ]
        }
    ]
    
    # Add placeholder triggers
    rule_pack["triggers"] = [
        {
            "id": "valuation_threshold",
            "description": "Trigger when parcel meets valuation threshold",
            "match": "parcel.assessed_value >= 100000",
            "deadline_chain": "offer_served",
        }
    ]
    
    # Convert to YAML with comments
    yaml_str = yaml.dump(rule_pack, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    # Add header comment
    header = f"""# {reqs.state_name} Eminent Domain Rules
# Auto-generated from requirements document - REVIEW REQUIRED
# Generated by: scripts/generate_state_packs.py

"""
    
    return header + yaml_str


def validate_rule_pack(yaml_content: str, schema: dict) -> list[str]:
    """Validate a rule pack against the JSON schema.
    
    Returns list of validation errors.
    """
    try:
        import jsonschema
        
        data = yaml.safe_load(yaml_content)
        
        validator = jsonschema.Draft7Validator(schema)
        errors = list(validator.iter_errors(data))
        
        return [f"{e.path}: {e.message}" for e in errors]
        
    except ImportError:
        logger.warning("jsonschema not installed, skipping validation")
        return []
    except Exception as e:
        return [str(e)]


def generate_test_file(state_code: str, rule_pack: dict) -> str:
    """Generate a pytest test file for the rule pack."""
    
    test_content = f'''"""Regression tests for {state_code} rule pack."""

import pytest
from app.services.rules_engine import (
    load_rule,
    evaluate_rules,
    get_jurisdiction_config,
    is_quick_take_available,
    is_economic_development_banned,
)


@pytest.fixture
def {state_code.lower()}_rules():
    """Load {state_code} rules."""
    return load_rule("{state_code}")


@pytest.fixture
def base_case_payload():
    """Base case payload for testing."""
    return {{
        "parcel.assessed_value": 500000,
        "event.offer_served": True,
        "event.offer_date": "2026-01-15",
    }}


class Test{state_code}RuleLoading:
    """Test that {state_code} rules load correctly."""
    
    def test_load_rules(self, {state_code.lower()}_rules):
        """Test that rules file loads without errors."""
        assert {state_code.lower()}_rules is not None
        assert {state_code.lower()}_rules.get("jurisdiction") == "{state_code}"
        assert {state_code.lower()}_rules.get("version") is not None
    
    def test_extends_base(self, {state_code.lower()}_rules):
        """Test that rules extend base."""
        assert {state_code.lower()}_rules.get("extends") == "base"


class Test{state_code}InitiationRules:
    """Test {state_code} initiation requirements."""
    
    def test_initiation_exists(self, {state_code.lower()}_rules):
        """Test initiation section exists."""
        assert "initiation" in {state_code.lower()}_rules
    
    def test_quick_take_availability(self):
        """Test quick-take availability check."""
        available = is_quick_take_available("{state_code}")
        assert isinstance(available, bool)


class Test{state_code}CompensationRules:
    """Test {state_code} compensation requirements."""
    
    def test_compensation_exists(self, {state_code.lower()}_rules):
        """Test compensation section exists."""
        assert "compensation" in {state_code.lower()}_rules
    
    def test_compensation_base(self, {state_code.lower()}_rules):
        """Test compensation base standard."""
        comp = {state_code.lower()}_rules.get("compensation", {{}})
        assert comp.get("base") in ["fair_market_value", "full_compensation"]


class Test{state_code}PublicUse:
    """Test {state_code} public use limitations."""
    
    def test_public_use_exists(self, {state_code.lower()}_rules):
        """Test public use section exists."""
        assert "public_use" in {state_code.lower()}_rules
    
    def test_economic_development_banned(self):
        """Test economic development ban check."""
        banned = is_economic_development_banned("{state_code}")
        assert isinstance(banned, bool)


class Test{state_code}TriggerEvaluation:
    """Test {state_code} trigger evaluation."""
    
    def test_evaluate_basic_triggers(self, base_case_payload):
        """Test that basic triggers evaluate."""
        results = evaluate_rules("{state_code}", base_case_payload)
        assert isinstance(results, list)
'''
    
    return test_content


async def generate_state_pack(
    state_code: str,
    requirements_content: str,
    dry_run: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """Generate a state rule pack.
    
    Args:
        state_code: Two-letter state code
        requirements_content: Full requirements document content
        dry_run: Don't write files
        validate: Validate against schema
        
    Returns:
        Generation result dict
    """
    state_name = STATE_NAMES.get(state_code, state_code)
    logger.info(f"Generating rule pack for {state_name} ({state_code})")
    
    result = {
        "state_code": state_code,
        "state_name": state_name,
        "success": False,
        "errors": [],
        "warnings": [],
        "files_created": [],
    }
    
    # Extract state section
    state_section = extract_state_section(requirements_content, state_name)
    
    if not state_section:
        result["errors"].append(f"Could not find section for {state_name}")
        # Use minimal fallback
        state_section = f"{state_name} eminent domain requirements"
        result["warnings"].append("Using minimal fallback data")
    
    # Parse requirements
    try:
        reqs = await parse_requirements_with_ai(state_code, state_section)
    except Exception as e:
        result["errors"].append(f"Parsing failed: {e}")
        return result
    
    # Generate YAML content
    yaml_content = generate_yaml_content(reqs)
    
    # Validate if requested
    if validate:
        schema = load_schema()
        if schema:
            validation_errors = validate_rule_pack(yaml_content, schema)
            if validation_errors:
                result["warnings"].extend(validation_errors)
    
    # Generate test file
    rule_pack = yaml.safe_load(yaml_content)
    test_content = generate_test_file(state_code, rule_pack)
    
    # Write files
    if not dry_run:
        # Write rule pack
        rule_path = RULES_DIR / f"{state_code.lower()}.yaml"
        rule_path.write_text(yaml_content)
        result["files_created"].append(str(rule_path))
        logger.info(f"Created {rule_path}")
        
        # Write test file
        test_dir = ROOT_DIR / "backend" / "tests" / "rules"
        test_dir.mkdir(parents=True, exist_ok=True)
        test_path = test_dir / f"test_{state_code.lower()}.py"
        test_path.write_text(test_content)
        result["files_created"].append(str(test_path))
        logger.info(f"Created {test_path}")
    else:
        logger.info(f"[DRY RUN] Would create {RULES_DIR / f'{state_code.lower()}.yaml'}")
        logger.info(f"[DRY RUN] Would create test file")
    
    result["success"] = len(result["errors"]) == 0
    return result


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate state rule packs")
    parser.add_argument("--state", type=str, help="Generate for specific state (e.g., OH)")
    parser.add_argument("--all", action="store_true", help="Generate all priority states")
    parser.add_argument("--validate", action="store_true", help="Validate against schema")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files")
    parser.add_argument("--list", action="store_true", help="List priority states")
    
    args = parser.parse_args()
    
    if args.list:
        print("Priority states for rule pack generation:")
        for code in PRIORITY_STATES:
            name = STATE_NAMES.get(code, code)
            rule_file = RULES_DIR / f"{code.lower()}.yaml"
            exists = "✓ exists" if rule_file.exists() else "✗ missing"
            print(f"  {code}: {name} [{exists}]")
        return
    
    # Load requirements document
    if not REQUIREMENTS_PATH.exists():
        logger.error(f"Requirements file not found: {REQUIREMENTS_PATH}")
        sys.exit(1)
    
    requirements_content = REQUIREMENTS_PATH.read_text()
    
    # Determine which states to generate
    states_to_generate = []
    if args.state:
        state = args.state.upper()
        if state not in STATE_NAMES:
            logger.warning(f"Unknown state: {state}, but will attempt generation")
        states_to_generate = [state]
    elif args.all:
        states_to_generate = PRIORITY_STATES
    else:
        # Default: generate states that don't have rule files yet
        for code in PRIORITY_STATES:
            rule_file = RULES_DIR / f"{code.lower()}.yaml"
            if not rule_file.exists():
                states_to_generate.append(code)
        
        if not states_to_generate:
            logger.info("All priority states already have rule packs")
            return
    
    logger.info(f"Generating rule packs for: {', '.join(states_to_generate)}")
    
    # Generate each state
    results = []
    for state_code in states_to_generate:
        result = await generate_state_pack(
            state_code,
            requirements_content,
            dry_run=args.dry_run,
            validate=args.validate,
        )
        results.append(result)
    
    # Summary
    print("\n" + "=" * 60)
    print("GENERATION SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r["success"])
    print(f"Total: {len(results)}, Success: {success_count}, Failed: {len(results) - success_count}")
    
    for result in results:
        status = "✓" if result["success"] else "✗"
        print(f"\n{status} {result['state_code']} ({result['state_name']})")
        
        if result["files_created"]:
            for f in result["files_created"]:
                print(f"  Created: {f}")
        
        if result["errors"]:
            for e in result["errors"]:
                print(f"  ERROR: {e}")
        
        if result["warnings"]:
            for w in result["warnings"]:
                print(f"  WARNING: {w}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
