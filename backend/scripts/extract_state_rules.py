#!/usr/bin/env python3
"""
Extract state requirements from specification document into YAML rule files.

This script parses the States requirements.md document and generates
structured YAML rule files for each state following the schema defined
in rules/schema/state_rules.schema.json.

Usage:
    python -m scripts.extract_state_rules [--state STATE] [--dry-run]
    
Options:
    --state STATE   Extract rules for a specific state only (e.g., OH, VA)
    --dry-run       Print extracted data without writing files
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT_DIR = Path(__file__).resolve().parents[2]
RULES_DIR = ROOT_DIR / "rules"
SPEC_FILE = ROOT_DIR / "States requitments.md"


@dataclass
class StateRequirement:
    """Extracted requirements for a single state."""
    state_code: str
    state_name: str
    initiation_procedure: str = ""
    compensation_valuation: str = ""
    owner_rights_notice: str = ""
    public_use_limits: str = ""


@dataclass
class ParsedStateRules:
    """Structured rules parsed from requirements text."""
    state_code: str
    version: str = "1.0.0"
    extends: str = "base"
    maintainer: str = "Auto-generated"
    description: str = ""
    citations: dict[str, Any] = field(default_factory=dict)
    initiation: dict[str, Any] = field(default_factory=dict)
    compensation: dict[str, Any] = field(default_factory=dict)
    owner_rights: dict[str, Any] = field(default_factory=dict)
    public_use: dict[str, Any] = field(default_factory=dict)
    deadline_chains: list[dict[str, Any]] = field(default_factory=list)
    triggers: list[dict[str, Any]] = field(default_factory=list)
    critical_periods: list[dict[str, Any]] = field(default_factory=list)


# State name to code mapping
STATE_CODES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY"
}

# States that already have detailed rules files
EXISTING_DETAILED_RULES = {"TX", "IN", "FL", "CA", "MI", "MO"}


def parse_spec_file() -> dict[str, StateRequirement]:
    """Parse the States requirements.md file and extract per-state data."""
    if not SPEC_FILE.exists():
        print(f"Error: Specification file not found: {SPEC_FILE}")
        sys.exit(1)
    
    content = SPEC_FILE.read_text(encoding="utf-8")
    states: dict[str, StateRequirement] = {}
    
    # Find the table section (starts after "State\tInitiation Procedure")
    table_match = re.search(
        r"State\s+Initiation Procedure.*?\n(.*?)(?:\n\nSources:|$)",
        content,
        re.DOTALL
    )
    
    if not table_match:
        print("Warning: Could not find state table in specification file")
        return states
    
    table_content = table_match.group(1)
    
    # Parse each state row (tab-separated)
    for state_name, state_code in STATE_CODES.items():
        # Look for the state name at the start of a line
        pattern = rf"^{re.escape(state_name)}\t(.+?)(?=\n[A-Z][a-z]+\t|\Z)"
        match = re.search(pattern, table_content, re.MULTILINE | re.DOTALL)
        
        if match:
            row_content = match.group(1)
            # Split by tabs to get the four columns
            columns = row_content.split("\t")
            
            if len(columns) >= 4:
                states[state_code] = StateRequirement(
                    state_code=state_code,
                    state_name=state_name,
                    initiation_procedure=columns[0].strip(),
                    compensation_valuation=columns[1].strip(),
                    owner_rights_notice=columns[2].strip(),
                    public_use_limits=columns[3].strip(),
                )
    
    return states


def extract_citations(text: str) -> list[str]:
    """Extract statutory citations from text."""
    citations = []
    
    # Common citation patterns
    patterns = [
        r"[A-Z][a-z]*\.?\s*(?:Const\.|Constitution)\s*(?:Art\.?\s*[IVX]+)?\s*§\s*[\d\-\.]+",
        r"[A-Z]{2,}\s*§\s*[\d\-\.]+(?:\([a-z]\))?",
        r"\d+\s+[A-Z][a-z]*\.?\s*(?:Code|Stat\.?)?\s*§\s*[\d\-\.]+",
        r"[A-Z][a-z]+\s+Code\s+(?:of\s+)?(?:Civ\.\s+)?Proc\.\s*§\s*[\d\-\.]+",
        r"[A-Z]{2,3}(?:\s+[A-Z][a-z]+)*\s+§\s*[\d\-\.]+",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        citations.extend(matches)
    
    return list(set(citations))


def extract_days(text: str, keyword: str) -> int | None:
    """Extract number of days associated with a keyword from text."""
    patterns = [
        rf"(\d+)\s*(?:days?|day)\s*(?:before|after|from|to)?\s*{keyword}",
        rf"{keyword}.*?(\d+)\s*(?:days?|day)",
        rf"(?:at least|minimum|within)\s*(\d+)\s*(?:days?|day).*?{keyword}",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    
    return None


def extract_percentage(text: str, keyword: str) -> float | None:
    """Extract percentage associated with a keyword from text."""
    patterns = [
        rf"(\d+(?:\.\d+)?)\s*%.*?{keyword}",
        rf"{keyword}.*?(\d+(?:\.\d+)?)\s*%",
        rf"(\d+(?:\.\d+)?)\s*percent.*?{keyword}",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    
    return None


def extract_multiplier(text: str) -> dict[str, Any]:
    """Extract compensation multipliers from text."""
    multipliers = {}
    
    # Look for 125% residence multiplier
    if re.search(r"125\s*%.*(?:residence|home|owner-occupied)", text, re.IGNORECASE):
        multipliers["residence_multiplier"] = 1.25
    
    # Look for heritage/family ownership multipliers
    heritage_match = re.search(
        r"(\d+)\s*%.*(?:family|heritage|50\+?\s*years?)",
        text,
        re.IGNORECASE
    )
    if heritage_match:
        pct = int(heritage_match.group(1))
        multipliers["heritage_multiplier"] = {
            "long_term_family": {"multiplier": pct / 100.0}
        }
    
    return multipliers


def parse_requirements_to_rules(req: StateRequirement) -> ParsedStateRules:
    """Convert extracted requirements into structured rules."""
    rules = ParsedStateRules(
        state_code=req.state_code,
        description=f"{req.state_name} eminent domain procedural rules",
    )
    
    # Extract citations
    all_citations = (
        extract_citations(req.initiation_procedure) +
        extract_citations(req.compensation_valuation) +
        extract_citations(req.owner_rights_notice) +
        extract_citations(req.public_use_limits)
    )
    if all_citations:
        rules.citations["additional"] = list(set(all_citations))[:5]
    
    # Parse initiation procedure
    init_text = req.initiation_procedure.lower()
    rules.initiation = {
        "pre_condemnation_offer_required": "offer" in init_text and "required" in init_text,
        "appraisal_based_offer": "appraisal" in init_text,
        "good_faith_negotiation": "good faith" in init_text or "negotiate" in init_text,
        "resolution_required": "resolution" in init_text,
        "public_hearing_required": "public hearing" in init_text or "hearing" in init_text,
        "quick_take": {
            "available": "quick" in init_text or "immediate" in init_text,
        }
    }
    
    # Extract notice days
    offer_days = extract_days(req.initiation_procedure, "offer")
    if offer_days:
        rules.initiation["initial_offer_days"] = offer_days
    
    notice_days = extract_days(req.initiation_procedure, "notice")
    if notice_days:
        rules.initiation["intent_notice_days"] = notice_days
    
    # Parse compensation rules
    comp_text = req.compensation_valuation.lower()
    rules.compensation = {
        "base": "full_compensation" if "full compensation" in comp_text else "fair_market_value",
        "highest_and_best_use": "highest" in comp_text or "best use" in comp_text,
        "includes_severance": "severance" in comp_text,
        "business_goodwill": "goodwill" in comp_text,
        "business_losses": "business loss" in comp_text or "interruption" in comp_text,
        "relocation_assistance": "relocation" in comp_text,
    }
    
    # Extract multipliers
    multipliers = extract_multiplier(req.compensation_valuation)
    rules.compensation.update(multipliers)
    
    # Attorney fees
    fee_text = req.compensation_valuation
    rules.compensation["attorney_fees"] = {
        "automatic": "automatic" in fee_text.lower() or "must pay" in fee_text.lower(),
        "threshold_based": "%" in fee_text and "award" in fee_text.lower(),
    }
    
    threshold = extract_percentage(fee_text, "offer|award")
    if threshold:
        rules.compensation["attorney_fees"]["threshold_percent"] = threshold
    
    # Parse owner rights
    rights_text = req.owner_rights_notice.lower()
    rules.owner_rights = {
        "jury_trial": "jury" in rights_text,
        "public_use_challenge": "challenge" in rights_text or "contest" in rights_text,
        "commissioners_panel": "commissioner" in rights_text or "appraiser" in rights_text,
    }
    
    # Extract objection window days
    obj_days = extract_days(req.owner_rights_notice, "object|appeal|challenge")
    if obj_days:
        rules.owner_rights["notice_periods"] = {"objection_window_days": obj_days}
    
    # Parse public use limits
    pub_text = req.public_use_limits.lower()
    rules.public_use = {
        "economic_development_banned": (
            "economic development" in pub_text and
            ("prohibit" in pub_text or "ban" in pub_text or "forbid" in pub_text or "not" in pub_text)
        ),
        "blight_for_private": (
            "prohibited" if "blight" in pub_text and "prohibit" in pub_text
            else "restricted" if "blight" in pub_text
            else "allowed"
        ),
    }
    
    # Extract reform year
    year_match = re.search(r"(200[4-9]|201[0-9]|202[0-6])", req.public_use_limits)
    if year_match:
        rules.public_use["post_kelo_reform_year"] = int(year_match.group(1))
    
    # Determine reform type
    if "constitutional" in pub_text and "statute" in pub_text:
        rules.public_use["reform_type"] = "both"
    elif "constitutional" in pub_text or "constitution" in pub_text:
        rules.public_use["reform_type"] = "constitutional"
    elif "statute" in pub_text or "law" in pub_text:
        rules.public_use["reform_type"] = "statutory"
    
    # Add basic triggers
    rules.triggers = [
        {
            "id": f"{req.state_code.lower()}_offer_served",
            "description": f"Generate deadline chain when offer is served in {req.state_name}",
            "match": f"case.jurisdiction == '{req.state_code}' and events.offer_served is not None",
            "evidence_hooks": [
                {
                    "fields": [
                        "events.offer_served",
                        "offer.total_amount",
                        "owner.name",
                        "parcel.pin"
                    ]
                }
            ]
        }
    ]
    
    return rules


def rules_to_yaml(rules: ParsedStateRules) -> str:
    """Convert ParsedStateRules to YAML string."""
    data = {
        "version": rules.version,
        "jurisdiction": rules.state_code,
        "extends": rules.extends,
        "maintainer": rules.maintainer,
        "description": rules.description,
    }
    
    if rules.citations:
        data["citations"] = rules.citations
    
    data["initiation"] = rules.initiation
    data["compensation"] = rules.compensation
    data["owner_rights"] = rules.owner_rights
    data["public_use"] = rules.public_use
    
    if rules.deadline_chains:
        data["deadline_chains"] = rules.deadline_chains
    
    if rules.triggers:
        data["triggers"] = rules.triggers
    
    if rules.critical_periods:
        data["critical_periods"] = rules.critical_periods
    
    # Add header comment
    header = f"""# {STATE_CODES.get(rules.state_code, rules.state_code)} Eminent Domain Rules
# Auto-generated from States requirements specification
# Review and enhance with specific statutory citations

"""
    
    return header + yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


def write_rules_file(rules: ParsedStateRules, dry_run: bool = False) -> None:
    """Write rules to YAML file."""
    yaml_content = rules_to_yaml(rules)
    file_path = RULES_DIR / f"{rules.state_code.lower()}.yaml"
    
    if dry_run:
        print(f"\n{'=' * 60}")
        print(f"Would write to: {file_path}")
        print("=" * 60)
        print(yaml_content[:1000])
        if len(yaml_content) > 1000:
            print(f"... ({len(yaml_content)} total characters)")
    else:
        file_path.write_text(yaml_content, encoding="utf-8")
        print(f"Wrote: {file_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract state requirements into YAML rule files"
    )
    parser.add_argument(
        "--state",
        type=str,
        help="Extract rules for a specific state (e.g., OH, VA)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print extracted data without writing files"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing detailed rules files"
    )
    
    args = parser.parse_args()
    
    print(f"Parsing specification file: {SPEC_FILE}")
    states = parse_spec_file()
    print(f"Found {len(states)} states in specification")
    
    if args.state:
        state_code = args.state.upper()
        if state_code not in states:
            print(f"Error: State {state_code} not found in specification")
            sys.exit(1)
        states = {state_code: states[state_code]}
    
    processed = 0
    skipped = 0
    
    for state_code, requirement in sorted(states.items()):
        # Skip states that already have detailed rules unless --force
        if state_code in EXISTING_DETAILED_RULES and not args.force:
            print(f"Skipping {state_code} (already has detailed rules, use --force to overwrite)")
            skipped += 1
            continue
        
        rules = parse_requirements_to_rules(requirement)
        write_rules_file(rules, dry_run=args.dry_run)
        processed += 1
    
    print(f"\nProcessed: {processed}, Skipped: {skipped}")
    
    if args.dry_run:
        print("\nDry run complete. No files were written.")


if __name__ == "__main__":
    main()
