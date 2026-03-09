from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import operator
from types import SimpleNamespace
import copy
import yaml

ROOT_DIR = Path(__file__).resolve().parents[3]
RULES_DIR = ROOT_DIR / "rules"


@dataclass
class RuleResultPayload:
    rule_id: str
    version: str
    citation: str
    fired: bool
    evidence: dict[str, Any]


@dataclass
class JurisdictionConfig:
    """Configuration extracted from a jurisdiction's rules."""
    jurisdiction: str
    version: str
    initiation: dict[str, Any] = field(default_factory=dict)
    compensation: dict[str, Any] = field(default_factory=dict)
    owner_rights: dict[str, Any] = field(default_factory=dict)
    public_use: dict[str, Any] = field(default_factory=dict)
    citations: dict[str, Any] = field(default_factory=dict)


SAFE_FUNCS = {
    "max": max,
    "min": min,
    "abs": abs,
}

SAFE_OPERATORS = {name: getattr(operator, name) for name in dir(operator) if not name.startswith("_")}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Deep merge two dictionaries. Override values take precedence.
    
    - If both values are dicts, recursively merge them
    - If override has a value (including None explicitly set), use it
    - Otherwise, use base value
    """
    result = copy.deepcopy(base)
    
    for key, override_value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(override_value, dict):
            result[key] = _deep_merge(result[key], override_value)
        else:
            result[key] = copy.deepcopy(override_value)
    
    return result


def _tree_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    tree: dict[str, Any] = {}
    for key, value in payload.items():
        parts = key.split(".")
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return tree


def _to_namespace(value: Any) -> Any:
    if isinstance(value, dict):
        return SimpleNamespace(**{k: _to_namespace(v) for k, v in value.items()})
    return value


def _attribute_names(value: Any) -> set[str]:
    names: set[str] = set()
    if isinstance(value, SimpleNamespace):
        for key, nested in vars(value).items():
            names.add(key)
            names |= _attribute_names(nested)
    return names


def _safe_eval(expr: str, context: dict[str, Any]) -> bool:
    structured = {k: _to_namespace(v) for k, v in _tree_from_payload(context).items()}
    attr_names = set().union(*(_attribute_names(v) for v in structured.values()))
    allowed_names = {**context, **structured, **SAFE_FUNCS}
    for name in attr_names:
        allowed_names.setdefault(name, None)
    code = compile(expr, "<rule>", "eval")
    for name in code.co_names:
        if name not in allowed_names:
            raise ValueError(f"Unsafe name {name} in expression {expr}")
    return bool(eval(code, {"__builtins__": {}}, allowed_names))


def load_base_rules() -> dict[str, Any]:
    """Load the base rules file."""
    base_path = RULES_DIR / "base.yaml"
    if not base_path.exists():
        return {}
    return yaml.safe_load(base_path.read_text()) or {}


def load_rule(jurisdiction: str) -> dict[str, Any]:
    """
    Load rules for a jurisdiction, merging with base rules if 'extends: base' is specified.
    
    Args:
        jurisdiction: Two-letter state code (e.g., 'TX', 'CA')
    
    Returns:
        Merged rules dictionary with base defaults and state-specific overrides.
    """
    file_path = RULES_DIR / f"{jurisdiction.lower()}.yaml"
    if not file_path.exists():
        raise FileNotFoundError(f"No rules file found for jurisdiction: {jurisdiction}")
    
    state_rules = yaml.safe_load(file_path.read_text()) or {}
    
    # Check if this rule extends base
    if state_rules.get("extends") == "base":
        base_rules = load_base_rules()
        
        # Map base defaults to state rule structure
        base_defaults = {
            "initiation": base_rules.get("initiation_defaults", {}),
            "compensation": base_rules.get("compensation_defaults", {}),
            "owner_rights": base_rules.get("owner_rights_defaults", {}),
            "public_use": base_rules.get("public_use_defaults", {}),
            "notice_defaults": base_rules.get("notice_defaults", {}),
            "anchor_events": base_rules.get("anchor_events", []),
            "evidence_fields": base_rules.get("evidence_fields", {}),
            "template_defaults": base_rules.get("template_defaults", {}),
        }
        
        # Merge base defaults with state-specific rules
        merged = _deep_merge(base_defaults, state_rules)
        return merged
    
    return state_rules


def get_jurisdiction_config(jurisdiction: str) -> JurisdictionConfig:
    """
    Get structured configuration for a jurisdiction.
    
    Useful for accessing initiation, compensation, owner_rights, and public_use
    settings without loading the full rules with triggers/deadlines.
    """
    rules = load_rule(jurisdiction)
    
    return JurisdictionConfig(
        jurisdiction=rules.get("jurisdiction", jurisdiction.upper()),
        version=rules.get("version", "1.0.0"),
        initiation=rules.get("initiation", {}),
        compensation=rules.get("compensation", {}),
        owner_rights=rules.get("owner_rights", {}),
        public_use=rules.get("public_use", {}),
        citations=rules.get("citations", {}),
    )


def get_compensation_multiplier(jurisdiction: str, parcel_data: dict[str, Any]) -> float:
    """
    Calculate the compensation multiplier for a parcel based on jurisdiction rules.
    
    Handles MI (125% for owner-occupied residence) and MO (150%/125% heritage value).
    
    Args:
        jurisdiction: Two-letter state code
        parcel_data: Dict with parcel info (owner_occupied, principal_residence, family_ownership_years)
    
    Returns:
        Multiplier to apply to fair market value (1.0 if no multiplier applies)
    """
    config = get_jurisdiction_config(jurisdiction)
    compensation = config.compensation
    
    # Check for residence multiplier (MI)
    residence_mult = compensation.get("residence_multiplier")
    if residence_mult and parcel_data.get("owner_occupied") and parcel_data.get("principal_residence"):
        return float(residence_mult)
    
    # Check for heritage multiplier (MO)
    heritage = compensation.get("heritage_multiplier")
    if heritage:
        family_years = parcel_data.get("family_ownership_years", 0)
        
        # Check long-term family (50+ years = 150%)
        long_term = heritage.get("long_term_family", {})
        if isinstance(long_term, dict):
            years_required = long_term.get("years_required", 50)
            mult = long_term.get("multiplier", 1.0)
            if family_years >= years_required:
                return float(mult)
        
        # Check homestead (125%)
        homestead = heritage.get("homestead", {})
        if isinstance(homestead, dict):
            mult = homestead.get("multiplier", 1.0)
            if parcel_data.get("owner_occupied") and family_years < 50:
                return float(mult)
    
    return 1.0


def get_notice_requirements(jurisdiction: str) -> dict[str, Any]:
    """
    Get notice requirements for a jurisdiction.
    
    Returns dict with keys like:
    - offer_notice_days
    - final_offer_notice_days
    - intent_notice_days
    - response_window_days
    """
    config = get_jurisdiction_config(jurisdiction)
    initiation = config.initiation
    owner_rights = config.owner_rights
    
    notice_periods = owner_rights.get("notice_periods", {})
    
    return {
        "offer_notice_days": initiation.get("initial_offer_days", 30),
        "final_offer_notice_days": initiation.get("final_offer_days", 14),
        "intent_notice_days": initiation.get("notice_of_intent_days") or initiation.get("intent_notice_days"),
        "bill_of_rights_days": notice_periods.get("landowner_bill_of_rights"),
        "response_window_days": notice_periods.get("final_offer_consideration") or initiation.get("initial_offer_days", 30),
        "objection_window_days": notice_periods.get("objection_window_days"),
        "landowner_bill_of_rights_required": initiation.get("landowner_bill_of_rights", False),
    }


def get_attorney_fee_rules(jurisdiction: str) -> dict[str, Any]:
    """
    Get attorney fee rules for a jurisdiction.
    
    Returns dict with keys:
    - automatic: bool - whether fees are automatically awarded (FL)
    - threshold_based: bool - whether fees depend on award exceeding offer
    - threshold_percent: float - percent above offer that triggers fees
    - mandatory: bool - whether condemnor must pay fees (MI)
    """
    config = get_jurisdiction_config(jurisdiction)
    fees = config.compensation.get("attorney_fees", {})
    
    return {
        "automatic": fees.get("automatic", False),
        "threshold_based": fees.get("threshold_based", False),
        "threshold_percent": fees.get("threshold_percent"),
        "mandatory": fees.get("mandatory", False),
        "includes_expert_fees": fees.get("includes_expert_fees", False),
        "citation": fees.get("citation"),
    }


def is_quick_take_available(jurisdiction: str) -> bool:
    """Check if quick-take is available in this jurisdiction."""
    config = get_jurisdiction_config(jurisdiction)
    quick_take = config.initiation.get("quick_take", {})
    return quick_take.get("available", False)


def is_economic_development_banned(jurisdiction: str) -> bool:
    """Check if takings for economic development are banned in this jurisdiction."""
    config = get_jurisdiction_config(jurisdiction)
    return config.public_use.get("economic_development_banned", False)


def evaluate_rules(jurisdiction: str, payload: dict[str, Any]) -> list[RuleResultPayload]:
    """
    Evaluate all triggers in a jurisdiction's rules against the provided payload.
    
    Args:
        jurisdiction: Two-letter state code
        payload: Dict of case/parcel data to evaluate triggers against
    
    Returns:
        List of RuleResultPayload for each trigger (fired or not)
    """
    rules_doc = load_rule(jurisdiction)
    results: list[RuleResultPayload] = []
    
    for trigger in rules_doc.get("triggers", []):
        match_expr = trigger.get("match", "False")
        fired = _safe_eval(match_expr, payload)
        evidence = {}
        
        if fired:
            for hook in trigger.get("evidence_hooks", []):
                evidence[hook["citation"]] = {
                    field: payload.get(field) for field in hook.get("fields", [])
                }
        
        # Get citation from first deadline or trigger itself
        deadlines = trigger.get("deadlines", [{}])
        citation = deadlines[0].get("citation", "") if deadlines else ""
        
        results.append(
            RuleResultPayload(
                rule_id=trigger["id"],
                version=rules_doc.get("version", "1.0.0"),
                citation=citation,
                fired=fired,
                evidence=evidence,
            )
        )
    
    return results


def list_available_jurisdictions() -> list[str]:
    """List all jurisdictions that have rules files."""
    jurisdictions = []
    for path in RULES_DIR.glob("*.yaml"):
        if path.stem != "base":
            jurisdictions.append(path.stem.upper())
    return sorted(jurisdictions)


def validate_rules_file(jurisdiction: str) -> list[str]:
    """
    Validate a jurisdiction's rules file for common issues.
    
    Returns list of warning/error messages.
    """
    errors: list[str] = []
    
    try:
        rules = load_rule(jurisdiction)
    except FileNotFoundError:
        return [f"Rules file not found for jurisdiction: {jurisdiction}"]
    except yaml.YAMLError as e:
        return [f"YAML parse error: {e}"]
    
    # Check required fields
    if not rules.get("version"):
        errors.append("Missing 'version' field")
    if not rules.get("jurisdiction"):
        errors.append("Missing 'jurisdiction' field")
    
    # Check triggers have required fields
    for i, trigger in enumerate(rules.get("triggers", [])):
        if not trigger.get("id"):
            errors.append(f"Trigger {i} missing 'id' field")
        if not trigger.get("match"):
            errors.append(f"Trigger {trigger.get('id', i)} missing 'match' expression")
    
    # Check deadline chains have required fields
    for i, chain in enumerate(rules.get("deadline_chains", [])):
        if not chain.get("anchor_event"):
            errors.append(f"Deadline chain {i} missing 'anchor_event'")
        for j, deadline in enumerate(chain.get("deadlines", [])):
            if not deadline.get("id"):
                errors.append(f"Deadline {j} in chain {i} missing 'id'")
            if deadline.get("offset_days") is None:
                errors.append(f"Deadline {deadline.get('id', j)} missing 'offset_days'")
    
    return errors
