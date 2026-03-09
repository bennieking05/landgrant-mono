"""
Deadline derivation service for calculating statutory deadlines from anchor events.

Given a jurisdiction and a set of anchor dates (e.g., offer_served, complaint_filed),
this service loads the rules YAML and computes the resulting deadlines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

ROOT_DIR = Path(__file__).resolve().parents[3]
RULES_DIR = ROOT_DIR / "rules"


@dataclass
class DerivedDeadline:
    """A deadline derived from an anchor event and jurisdiction rules."""

    id: str
    title: str
    description: str
    due_date: date
    anchor_event: str
    anchor_date: date
    offset_days: int
    citation: str
    deadline_type: str  # deadline, floor, eligibility, service_requirement
    extendable: bool = False
    max_extension_days: int = 0
    notes: str | None = None
    warning_days: list[int] = field(default_factory=list)


@dataclass
class DerivationResult:
    """Result of deadline derivation for a jurisdiction."""

    jurisdiction: str
    anchor_events: dict[str, date]
    deadlines: list[DerivedDeadline]
    errors: list[str] = field(default_factory=list)


def load_jurisdiction_rules(jurisdiction: str) -> dict[str, Any] | None:
    """Load rules YAML for a jurisdiction."""
    file_path = RULES_DIR / f"{jurisdiction.lower()}.yaml"
    if not file_path.exists():
        return None
    return yaml.safe_load(file_path.read_text())


def _parse_date(value: str | date | datetime) -> date:
    """Parse a date from various input formats."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        # Handle ISO format with optional time
        date_str = value.split("T")[0]
        return date.fromisoformat(date_str)
    raise ValueError(f"Cannot parse date from: {value}")


def _compute_due_date(anchor_date: date, offset_days: int, direction: str) -> date:
    """Compute due date from anchor and offset."""
    if direction in ("after", "after_hearing", "after_settlement_offer"):
        return anchor_date + timedelta(days=offset_days)
    elif direction in ("before", "before_hearing"):
        return anchor_date - timedelta(days=abs(offset_days))
    else:
        # Default to after
        return anchor_date + timedelta(days=offset_days)


def _format_deadline_title(deadline_id: str) -> str:
    """Convert deadline ID to human-readable title."""
    return deadline_id.replace("_", " ").title()


def derive_deadlines(
    jurisdiction: str,
    anchor_events: dict[str, str | date | datetime],
) -> DerivationResult:
    """
    Derive statutory deadlines from anchor events for a jurisdiction.

    Args:
        jurisdiction: Two-letter state code (e.g., 'IN', 'TX')
        anchor_events: Dict mapping event names to dates, e.g.:
            {
                'offer_served': '2025-02-06',
                'complaint_filed': '2025-03-15',
                'notice_served': '2025-03-20',
                'appraisers_report_mailed': '2025-05-01',
                'trial_date_set': '2025-09-15'
            }

    Returns:
        DerivationResult with computed deadlines and any errors.
    """
    result = DerivationResult(
        jurisdiction=jurisdiction.upper(),
        anchor_events={},
        deadlines=[],
        errors=[],
    )

    # Load rules
    rules = load_jurisdiction_rules(jurisdiction)
    if rules is None:
        result.errors.append(f"No rules found for jurisdiction: {jurisdiction}")
        return result

    # Parse anchor dates
    parsed_anchors: dict[str, date] = {}
    for event_name, event_date in anchor_events.items():
        try:
            parsed_anchors[event_name] = _parse_date(event_date)
        except ValueError as e:
            result.errors.append(f"Invalid date for {event_name}: {e}")

    result.anchor_events = parsed_anchors

    # Build warning days lookup from critical_periods
    warning_lookup: dict[str, list[int]] = {}
    for period in rules.get("critical_periods", []):
        # Map period IDs to deadline IDs that might match
        period_id = period.get("id", "")
        warning_days = period.get("warning_days", [])
        warning_lookup[period_id] = warning_days

    # Process deadline chains
    for chain in rules.get("deadline_chains", []):
        anchor_event = chain.get("anchor_event")
        if anchor_event not in parsed_anchors:
            continue

        anchor_date = parsed_anchors[anchor_event]

        for dl in chain.get("deadlines", []):
            deadline_id = dl.get("id", "unknown")
            offset_days = dl.get("offset_days", 0)
            direction = dl.get("direction", "after")

            # Handle relative deadlines (e.g., relative_to: settlement_offer_served)
            relative_to = dl.get("relative_to")
            if relative_to and relative_to in parsed_anchors:
                base_date = parsed_anchors[relative_to]
            else:
                base_date = anchor_date

            due_date = _compute_due_date(base_date, offset_days, direction)

            # Determine warning days from critical periods
            warn_days: list[int] = []
            for period_id, days in warning_lookup.items():
                if period_id in deadline_id:
                    warn_days = days
                    break

            derived = DerivedDeadline(
                id=deadline_id,
                title=_format_deadline_title(deadline_id),
                description=dl.get("description", ""),
                due_date=due_date,
                anchor_event=anchor_event,
                anchor_date=anchor_date,
                offset_days=offset_days,
                citation=dl.get("citation", ""),
                deadline_type=dl.get("type", "deadline"),
                extendable=dl.get("extendable", False),
                max_extension_days=dl.get("max_extension_days", 0),
                notes=dl.get("notes"),
                warning_days=warn_days,
            )
            result.deadlines.append(derived)

    # Sort deadlines by due date
    result.deadlines.sort(key=lambda d: d.due_date)

    return result


def derive_deadlines_from_template_render(
    jurisdiction: str,
    template_id: str,
    render_variables: dict[str, Any],
    additional_anchors: dict[str, str | date | datetime] | None = None,
) -> DerivationResult:
    """
    Derive deadlines from a template render's variables.

    This extracts anchor dates from template variables (e.g., service_date, appraisal_date)
    and computes the corresponding statutory deadlines.

    Args:
        jurisdiction: Two-letter state code
        template_id: Template ID (e.g., 'in_offer')
        render_variables: Variables used to render the template
        additional_anchors: Additional anchor events not in template variables

    Returns:
        DerivationResult with computed deadlines.
    """
    # Map template variables to anchor events
    variable_to_anchor = {
        "service_date": "offer_served",
        "appraisal_date": "appraisal_completed",
        "complaint_date": "complaint_filed",
        "notice_date": "notice_served",
        "report_mailed_date": "appraisers_report_mailed",
        "trial_date": "trial_date_set",
    }

    anchor_events: dict[str, Any] = {}

    # Extract anchors from template variables
    for var_name, anchor_name in variable_to_anchor.items():
        if var_name in render_variables and render_variables[var_name]:
            anchor_events[anchor_name] = render_variables[var_name]

    # Merge additional anchors
    if additional_anchors:
        anchor_events.update(additional_anchors)

    return derive_deadlines(jurisdiction, anchor_events)


def get_upcoming_warnings(
    deadlines: list[DerivedDeadline],
    as_of: date | None = None,
) -> list[tuple[DerivedDeadline, int]]:
    """
    Get deadlines that have upcoming warnings.

    Args:
        deadlines: List of derived deadlines
        as_of: Reference date (defaults to today)

    Returns:
        List of (deadline, days_until) tuples for deadlines with active warnings.
    """
    if as_of is None:
        as_of = date.today()

    warnings: list[tuple[DerivedDeadline, int]] = []

    for dl in deadlines:
        days_until = (dl.due_date - as_of).days
        if days_until < 0:
            continue  # Past due

        for warn_day in dl.warning_days:
            if days_until <= warn_day:
                warnings.append((dl, days_until))
                break

    return sorted(warnings, key=lambda x: x[1])
