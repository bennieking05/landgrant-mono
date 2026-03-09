"""State Summary and Comparison Service.

Generates:
- Common-core requirements across all states
- Clustered groupings (quick-take, commissioner states, etc.)
- State-specific deltas
- Markdown exports for documentation

Useful for understanding state similarities/differences at a glance.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class StateCluster:
    """A cluster of states sharing characteristics."""
    name: str
    description: str
    states: list[str]
    characteristic_key: str
    characteristic_value: Any
    citation: Optional[str] = None


@dataclass
class StateDelta:
    """Delta showing how a state differs from common core."""
    state: str
    requirement_id: str
    common_core_value: Any
    state_value: Any
    category: str
    citation: Optional[str] = None


@dataclass
class CommonCoreRequirement:
    """A requirement common to all (or most) states."""
    requirement_id: str
    description: str
    applies_to_all: bool
    states_count: int
    total_states: int
    exceptions: list[str]
    category: str


class StateSummaryService:
    """Service for state comparison and summarization."""

    def __init__(self, rules_path: Optional[Path] = None):
        """Initialize the service.
        
        Args:
            rules_path: Path to rules directory
        """
        self.rules_path = rules_path or Path(__file__).resolve().parents[3] / "rules"
        self._state_configs: dict[str, dict[str, Any]] = {}
        self._load_all_states()

    def _load_all_states(self) -> None:
        """Load all state configurations."""
        for path in self.rules_path.glob("*.yaml"):
            if path.stem in ["base", "schema"] or len(path.stem) != 2:
                continue
            
            try:
                state_code = path.stem.upper()
                content = yaml.safe_load(path.read_text())
                self._state_configs[state_code] = content
            except Exception:
                continue  # Skip invalid files

    def get_common_core(self) -> list[CommonCoreRequirement]:
        """Get requirements common to all states.
        
        Returns:
            List of common core requirements
        """
        if not self._state_configs:
            return []
        
        common = []
        total_states = len(self._state_configs)
        
        # Check initiation requirements
        common.extend(self._analyze_initiation_commonality(total_states))
        
        # Check compensation requirements
        common.extend(self._analyze_compensation_commonality(total_states))
        
        # Check owner rights
        common.extend(self._analyze_owner_rights_commonality(total_states))
        
        return common

    def _analyze_initiation_commonality(
        self, total_states: int
    ) -> list[CommonCoreRequirement]:
        """Analyze initiation requirements for commonality."""
        common = []
        
        # Pre-condemnation offer
        states_requiring = []
        states_not_requiring = []
        
        for state, config in self._state_configs.items():
            initiation = config.get("initiation", {})
            if initiation.get("pre_condemnation_offer_required"):
                states_requiring.append(state)
            else:
                states_not_requiring.append(state)
        
        common.append(CommonCoreRequirement(
            requirement_id="initiation.pre_condemnation_offer",
            description="Pre-condemnation written offer before filing",
            applies_to_all=len(states_not_requiring) == 0,
            states_count=len(states_requiring),
            total_states=total_states,
            exceptions=states_not_requiring,
            category="initiation",
        ))
        
        # Appraisal-based offer
        states_requiring = []
        states_not_requiring = []
        
        for state, config in self._state_configs.items():
            initiation = config.get("initiation", {})
            if initiation.get("appraisal_based_offer"):
                states_requiring.append(state)
            else:
                states_not_requiring.append(state)
        
        common.append(CommonCoreRequirement(
            requirement_id="initiation.appraisal_based_offer",
            description="Initial offer must be based on appraisal",
            applies_to_all=len(states_not_requiring) == 0,
            states_count=len(states_requiring),
            total_states=total_states,
            exceptions=states_not_requiring,
            category="initiation",
        ))
        
        # Good faith negotiation
        states_requiring = []
        states_not_requiring = []
        
        for state, config in self._state_configs.items():
            initiation = config.get("initiation", {})
            if initiation.get("good_faith_negotiation"):
                states_requiring.append(state)
            else:
                states_not_requiring.append(state)
        
        common.append(CommonCoreRequirement(
            requirement_id="initiation.good_faith_negotiation",
            description="Good faith negotiation attempt required",
            applies_to_all=len(states_not_requiring) == 0,
            states_count=len(states_requiring),
            total_states=total_states,
            exceptions=states_not_requiring,
            category="initiation",
        ))
        
        return common

    def _analyze_compensation_commonality(
        self, total_states: int
    ) -> list[CommonCoreRequirement]:
        """Analyze compensation requirements for commonality."""
        common = []
        
        # Fair market value as base
        states_fmv = []
        states_other = []
        
        for state, config in self._state_configs.items():
            compensation = config.get("compensation", {})
            base = compensation.get("base", "fair_market_value")
            if base == "fair_market_value":
                states_fmv.append(state)
            else:
                states_other.append(state)
        
        common.append(CommonCoreRequirement(
            requirement_id="compensation.base_standard",
            description="Fair Market Value as base compensation standard",
            applies_to_all=len(states_other) == 0,
            states_count=len(states_fmv),
            total_states=total_states,
            exceptions=states_other,
            category="compensation",
        ))
        
        # Severance damages
        states_with = []
        states_without = []
        
        for state, config in self._state_configs.items():
            compensation = config.get("compensation", {})
            if compensation.get("includes_severance"):
                states_with.append(state)
            else:
                states_without.append(state)
        
        common.append(CommonCoreRequirement(
            requirement_id="compensation.severance_damages",
            description="Severance damages for remainder property",
            applies_to_all=len(states_without) == 0,
            states_count=len(states_with),
            total_states=total_states,
            exceptions=states_without,
            category="compensation",
        ))
        
        # Relocation assistance
        states_with = []
        states_without = []
        
        for state, config in self._state_configs.items():
            compensation = config.get("compensation", {})
            if compensation.get("relocation_assistance"):
                states_with.append(state)
            else:
                states_without.append(state)
        
        common.append(CommonCoreRequirement(
            requirement_id="compensation.relocation_assistance",
            description="Relocation assistance for displaced owners",
            applies_to_all=len(states_without) == 0,
            states_count=len(states_with),
            total_states=total_states,
            exceptions=states_without,
            category="compensation",
        ))
        
        return common

    def _analyze_owner_rights_commonality(
        self, total_states: int
    ) -> list[CommonCoreRequirement]:
        """Analyze owner rights for commonality."""
        common = []
        
        # Jury trial available
        states_with = []
        states_without = []
        
        for state, config in self._state_configs.items():
            owner_rights = config.get("owner_rights", {})
            if owner_rights.get("jury_trial"):
                states_with.append(state)
            else:
                states_without.append(state)
        
        common.append(CommonCoreRequirement(
            requirement_id="owner_rights.jury_trial",
            description="Right to jury trial on compensation amount",
            applies_to_all=len(states_without) == 0,
            states_count=len(states_with),
            total_states=total_states,
            exceptions=states_without,
            category="owner_rights",
        ))
        
        # Public use challenge
        states_with = []
        states_without = []
        
        for state, config in self._state_configs.items():
            owner_rights = config.get("owner_rights", {})
            if owner_rights.get("public_use_challenge"):
                states_with.append(state)
            else:
                states_without.append(state)
        
        common.append(CommonCoreRequirement(
            requirement_id="owner_rights.public_use_challenge",
            description="Right to challenge public use in court",
            applies_to_all=len(states_without) == 0,
            states_count=len(states_with),
            total_states=total_states,
            exceptions=states_without,
            category="owner_rights",
        ))
        
        return common

    def get_clusters(self) -> list[StateCluster]:
        """Get state clusters based on characteristics.
        
        Returns:
            List of state clusters
        """
        clusters = []
        
        # Quick-take states
        quick_take_states = []
        for state, config in self._state_configs.items():
            quick_take = config.get("initiation", {}).get("quick_take", {})
            if quick_take.get("available"):
                quick_take_states.append(state)
        
        clusters.append(StateCluster(
            name="Quick-Take States",
            description="States allowing possession before final compensation determination",
            states=sorted(quick_take_states),
            characteristic_key="initiation.quick_take.available",
            characteristic_value=True,
        ))
        
        # Deposit and possession
        deposit_states = []
        for state, config in self._state_configs.items():
            quick_take = config.get("initiation", {}).get("quick_take", {})
            if quick_take.get("type") == "deposit_and_possession":
                deposit_states.append(state)
        
        clusters.append(StateCluster(
            name="Deposit & Possession States",
            description="Quick-take via deposit of estimated compensation",
            states=sorted(deposit_states),
            characteristic_key="initiation.quick_take.type",
            characteristic_value="deposit_and_possession",
        ))
        
        # Order of taking states
        order_states = []
        for state, config in self._state_configs.items():
            quick_take = config.get("initiation", {}).get("quick_take", {})
            if quick_take.get("type") == "order_of_taking":
                order_states.append(state)
        
        clusters.append(StateCluster(
            name="Order of Taking States",
            description="Quick-take via court order of taking",
            states=sorted(order_states),
            characteristic_key="initiation.quick_take.type",
            characteristic_value="order_of_taking",
        ))
        
        # Commissioner states
        commissioner_states = []
        for state, config in self._state_configs.items():
            owner_rights = config.get("owner_rights", {})
            panel = owner_rights.get("commissioners_panel")
            if panel in ["three_commissioners", "special_commissioners", "appraisers"]:
                commissioner_states.append(state)
        
        clusters.append(StateCluster(
            name="Commissioner/Appraiser States",
            description="Use commissioners or appraisers for initial valuation",
            states=sorted(commissioner_states),
            characteristic_key="owner_rights.commissioners_panel",
            characteristic_value="commissioners",
        ))
        
        # Bill of Rights states
        bill_of_rights_states = []
        for state, config in self._state_configs.items():
            initiation = config.get("initiation", {})
            if initiation.get("landowner_bill_of_rights"):
                bill_of_rights_states.append(state)
        
        clusters.append(StateCluster(
            name="Landowner Bill of Rights States",
            description="Require providing Landowner Bill of Rights document",
            states=sorted(bill_of_rights_states),
            characteristic_key="initiation.landowner_bill_of_rights",
            characteristic_value=True,
        ))
        
        # Multiplier states
        multiplier_states = []
        for state, config in self._state_configs.items():
            compensation = config.get("compensation", {})
            if compensation.get("residence_multiplier") or compensation.get("heritage_multiplier"):
                multiplier_states.append(state)
        
        clusters.append(StateCluster(
            name="Enhanced Compensation States",
            description="Provide multipliers for residence, homestead, or heritage property",
            states=sorted(multiplier_states),
            characteristic_key="compensation.multipliers",
            characteristic_value=True,
        ))
        
        # Automatic attorney fee states
        auto_fee_states = []
        for state, config in self._state_configs.items():
            compensation = config.get("compensation", {})
            fees = compensation.get("attorney_fees", {})
            if fees.get("automatic"):
                auto_fee_states.append(state)
        
        clusters.append(StateCluster(
            name="Automatic Attorney Fee States",
            description="Condemnor automatically pays landowner attorney fees",
            states=sorted(auto_fee_states),
            characteristic_key="compensation.attorney_fees.automatic",
            characteristic_value=True,
        ))
        
        # Post-Kelo reform states
        reform_states = []
        for state, config in self._state_configs.items():
            public_use = config.get("public_use", {})
            if public_use.get("economic_development_banned"):
                reform_states.append(state)
        
        clusters.append(StateCluster(
            name="Post-Kelo Reform States",
            description="Banned takings for economic development after Kelo v. City of New London",
            states=sorted(reform_states),
            characteristic_key="public_use.economic_development_banned",
            characteristic_value=True,
        ))
        
        return clusters

    def get_state_delta(self, state: str) -> list[StateDelta]:
        """Get deltas showing how a state differs from common core.
        
        Args:
            state: State code
            
        Returns:
            List of deltas
        """
        state = state.upper()
        if state not in self._state_configs:
            return []
        
        config = self._state_configs[state]
        deltas = []
        
        # Check for unique characteristics
        initiation = config.get("initiation", {})
        compensation = config.get("compensation", {})
        owner_rights = config.get("owner_rights", {})
        public_use = config.get("public_use", {})
        
        # Bill of Rights (TX specific)
        if initiation.get("landowner_bill_of_rights"):
            deltas.append(StateDelta(
                state=state,
                requirement_id="initiation.landowner_bill_of_rights",
                common_core_value=False,
                state_value=True,
                category="initiation",
                citation=initiation.get("bill_of_rights_citation"),
            ))
        
        # Residence multiplier (MI)
        if compensation.get("residence_multiplier"):
            deltas.append(StateDelta(
                state=state,
                requirement_id="compensation.residence_multiplier",
                common_core_value=None,
                state_value=compensation["residence_multiplier"],
                category="compensation",
            ))
        
        # Heritage multiplier (MO)
        if compensation.get("heritage_multiplier"):
            deltas.append(StateDelta(
                state=state,
                requirement_id="compensation.heritage_multiplier",
                common_core_value=None,
                state_value=compensation["heritage_multiplier"],
                category="compensation",
            ))
        
        # Business goodwill (CA)
        if compensation.get("business_goodwill"):
            deltas.append(StateDelta(
                state=state,
                requirement_id="compensation.business_goodwill",
                common_core_value=False,
                state_value=True,
                category="compensation",
            ))
        
        # Full compensation standard (FL)
        if compensation.get("base") == "full_compensation":
            deltas.append(StateDelta(
                state=state,
                requirement_id="compensation.base_standard",
                common_core_value="fair_market_value",
                state_value="full_compensation",
                category="compensation",
            ))
        
        # Automatic attorney fees (FL, MI)
        fees = compensation.get("attorney_fees", {})
        if fees.get("automatic"):
            deltas.append(StateDelta(
                state=state,
                requirement_id="compensation.attorney_fees",
                common_core_value="threshold_based",
                state_value="automatic",
                category="compensation",
                citation=fees.get("citation"),
            ))
        
        # Threshold-based attorney fees
        if fees.get("threshold_based") and fees.get("threshold_percent"):
            deltas.append(StateDelta(
                state=state,
                requirement_id="compensation.attorney_fee_threshold",
                common_core_value=None,
                state_value=f"{fees['threshold_percent']}%",
                category="compensation",
                citation=fees.get("citation"),
            ))
        
        # Resolution of Necessity required (CA)
        if initiation.get("resolution_required"):
            deltas.append(StateDelta(
                state=state,
                requirement_id="initiation.resolution_required",
                common_core_value=False,
                state_value=True,
                category="initiation",
            ))
        
        # Public hearing required
        if initiation.get("public_hearing_required"):
            deltas.append(StateDelta(
                state=state,
                requirement_id="initiation.public_hearing_required",
                common_core_value=False,
                state_value=True,
                category="initiation",
            ))
        
        # Specific notice periods
        notice_periods = owner_rights.get("notice_periods", {})
        for key, value in notice_periods.items():
            if value:
                deltas.append(StateDelta(
                    state=state,
                    requirement_id=f"owner_rights.notice_periods.{key}",
                    common_core_value=None,
                    state_value=value,
                    category="timeline",
                ))
        
        return deltas

    def get_state_summary(self, state: str) -> dict[str, Any]:
        """Get complete summary for a state.
        
        Args:
            state: State code
            
        Returns:
            State summary
        """
        state = state.upper()
        if state not in self._state_configs:
            return {"error": f"State {state} not found"}
        
        config = self._state_configs[state]
        deltas = self.get_state_delta(state)
        
        # Find which clusters this state belongs to
        clusters = self.get_clusters()
        state_clusters = [c.name for c in clusters if state in c.states]
        
        return {
            "state": state,
            "version": config.get("version"),
            "citations": config.get("citations", {}),
            "key_characteristics": {
                "quick_take_available": config.get("initiation", {}).get("quick_take", {}).get("available", False),
                "landowner_bill_of_rights": config.get("initiation", {}).get("landowner_bill_of_rights", False),
                "compensation_base": config.get("compensation", {}).get("base", "fair_market_value"),
                "attorney_fees_automatic": config.get("compensation", {}).get("attorney_fees", {}).get("automatic", False),
                "economic_development_banned": config.get("public_use", {}).get("economic_development_banned", False),
                "jury_trial_available": config.get("owner_rights", {}).get("jury_trial", True),
            },
            "clusters": state_clusters,
            "deltas_from_common": [
                {"requirement": d.requirement_id, "value": d.state_value}
                for d in deltas
            ],
            "initiation": config.get("initiation", {}),
            "compensation": config.get("compensation", {}),
            "owner_rights": config.get("owner_rights", {}),
            "public_use": config.get("public_use", {}),
        }

    def export_markdown(self) -> str:
        """Export comparison as markdown.
        
        Returns:
            Markdown formatted comparison
        """
        lines = [
            "# State Eminent Domain Comparison",
            "",
            f"*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*",
            "",
            "## Common Core Requirements",
            "",
        ]
        
        common = self.get_common_core()
        for req in common:
            coverage = f"{req.states_count}/{req.total_states}"
            exceptions_str = f" (except: {', '.join(req.exceptions)})" if req.exceptions else ""
            lines.append(f"- **{req.requirement_id}**: {req.description} [{coverage}]{exceptions_str}")
        
        lines.extend([
            "",
            "## State Clusters",
            "",
        ])
        
        clusters = self.get_clusters()
        for cluster in clusters:
            if cluster.states:
                lines.append(f"### {cluster.name}")
                lines.append(f"*{cluster.description}*")
                lines.append("")
                lines.append(f"States: {', '.join(cluster.states)}")
                lines.append("")
        
        lines.extend([
            "## Individual State Summaries",
            "",
        ])
        
        for state in sorted(self._state_configs.keys()):
            summary = self.get_state_summary(state)
            lines.append(f"### {state}")
            
            key_chars = summary.get("key_characteristics", {})
            lines.append(f"- Quick-take: {'Yes' if key_chars.get('quick_take_available') else 'No'}")
            lines.append(f"- Bill of Rights: {'Yes' if key_chars.get('landowner_bill_of_rights') else 'No'}")
            lines.append(f"- Compensation: {key_chars.get('compensation_base', 'FMV')}")
            lines.append(f"- Auto Attorney Fees: {'Yes' if key_chars.get('attorney_fees_automatic') else 'No'}")
            lines.append(f"- Econ Dev Banned: {'Yes' if key_chars.get('economic_development_banned') else 'No'}")
            lines.append("")
        
        return "\n".join(lines)

    def export_json(self) -> dict[str, Any]:
        """Export comparison as JSON.
        
        Returns:
            JSON-serializable comparison data
        """
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "states_count": len(self._state_configs),
            "common_core": [
                {
                    "requirement_id": r.requirement_id,
                    "description": r.description,
                    "applies_to_all": r.applies_to_all,
                    "coverage": f"{r.states_count}/{r.total_states}",
                    "exceptions": r.exceptions,
                    "category": r.category,
                }
                for r in self.get_common_core()
            ],
            "clusters": [
                {
                    "name": c.name,
                    "description": c.description,
                    "states": c.states,
                    "count": len(c.states),
                }
                for c in self.get_clusters()
            ],
            "states": {
                state: self.get_state_summary(state)
                for state in sorted(self._state_configs.keys())
            },
        }
