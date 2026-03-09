"""Requirements Operations Service for 50-State Management.

This service handles:
- State requirement pack ingestion and normalization
- Version management and diffing
- Validation and publishing
- Regulatory update monitoring

Usage:
    from app.services.requirements_ops import RequirementsOpsService
    
    service = RequirementsOpsService()
    pack = await service.import_state_pack("TX", yaml_content, citations)
    validation = await service.validate_pack(pack.id)
    await service.publish_pack(pack.id, user_id)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from app.services.hashing import sha256_hex


# Canonical requirement schema fields
CANONICAL_REQUIREMENT_FIELDS = [
    "requirement_id",
    "state",
    "topic",
    "trigger_event",
    "required_action",
    "deadline_rule",
    "deadline_days",
    "doc_requirements",
    "citations",
    "authority_level",
    "effective_date",
    "version",
    "confidence",
    "notes",
]

# Valid topics for requirements
VALID_TOPICS = [
    "notice",
    "offer",
    "appraisal",
    "compensation",
    "timeline",
    "filing",
    "hearing",
    "trial",
    "appeal",
    "relocation",
    "public_use",
    "blight",
    "attorney_fees",
]

# Authority levels in order of precedence
AUTHORITY_LEVELS = [
    "constitution",
    "statute",
    "case_law",
    "regulation",
    "local_rule",
    "administrative",
    "secondary",
]


@dataclass
class ValidationResult:
    """Result of pack validation."""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    requirements_count: int = 0
    topics_covered: list[str] = field(default_factory=list)


@dataclass
class PackDiff:
    """Diff between two pack versions."""
    from_version: str
    to_version: str
    added: list[dict[str, Any]] = field(default_factory=list)
    removed: list[dict[str, Any]] = field(default_factory=list)
    modified: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""


@dataclass
class NormalizedRequirement:
    """A requirement normalized to canonical schema."""
    requirement_id: str
    state: str
    topic: str
    trigger_event: Optional[str]
    required_action: str
    deadline_rule: Optional[str]
    deadline_days: Optional[int]
    doc_requirements: list[str]
    citations: list[dict[str, Any]]
    authority_level: str
    effective_date: Optional[datetime]
    version: str
    confidence: float
    notes: Optional[str]
    is_common_core: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "requirement_id": self.requirement_id,
            "state": self.state,
            "topic": self.topic,
            "trigger_event": self.trigger_event,
            "required_action": self.required_action,
            "deadline_rule": self.deadline_rule,
            "deadline_days": self.deadline_days,
            "doc_requirements": self.doc_requirements,
            "citations": self.citations,
            "authority_level": self.authority_level,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "version": self.version,
            "confidence": self.confidence,
            "notes": self.notes,
            "is_common_core": self.is_common_core,
        }


class RequirementsOpsService:
    """Service for managing 50-state requirement packs."""

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize the service.
        
        Args:
            storage_path: Path for storing pack artifacts (defaults to rules/)
        """
        self.storage_path = storage_path or Path(__file__).resolve().parents[3] / "rules"
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Ensure storage directories exist."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        (self.storage_path / "archive").mkdir(exist_ok=True)
        (self.storage_path / "staging").mkdir(exist_ok=True)

    def import_state_pack(
        self,
        jurisdiction: str,
        yaml_content: str,
        citations: Optional[list[dict[str, Any]]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Import a state requirement pack from YAML.
        
        Args:
            jurisdiction: Two-letter state code
            yaml_content: YAML content for the pack
            citations: Optional list of citation objects
            metadata: Optional metadata
            
        Returns:
            Pack information including ID and status
        """
        # Parse YAML
        try:
            pack_data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")

        # Validate jurisdiction
        if not pack_data.get("jurisdiction"):
            pack_data["jurisdiction"] = jurisdiction.upper()
        
        if pack_data["jurisdiction"].upper() != jurisdiction.upper():
            raise ValueError(
                f"Jurisdiction mismatch: expected {jurisdiction}, got {pack_data['jurisdiction']}"
            )

        # Generate pack ID and version
        pack_id = f"pack_{jurisdiction.lower()}_{uuid.uuid4().hex[:8]}"
        version = pack_data.get("version", "1.0.0")
        content_hash = sha256_hex(yaml_content.encode())

        # Normalize requirements
        requirements = self._normalize_pack_to_requirements(pack_data, jurisdiction)

        # Create pack record
        pack = {
            "id": pack_id,
            "jurisdiction": jurisdiction.upper(),
            "version": version,
            "status": "draft",
            "yaml_content": yaml_content,
            "content_hash": content_hash,
            "citations_json": citations or [],
            "requirements_count": len(requirements),
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store in staging
        staging_path = self.storage_path / "staging" / f"{pack_id}.yaml"
        staging_path.write_text(yaml_content)

        return {
            "pack": pack,
            "requirements": [r.to_dict() for r in requirements],
            "staging_path": str(staging_path),
        }

    def _normalize_pack_to_requirements(
        self, 
        pack_data: dict[str, Any], 
        jurisdiction: str
    ) -> list[NormalizedRequirement]:
        """Normalize pack data to canonical requirements.
        
        Extracts structured requirements from various pack sections.
        """
        requirements = []
        version = pack_data.get("version", "1.0.0")
        base_citations = pack_data.get("citations", {})

        # Extract from initiation section
        initiation = pack_data.get("initiation", {})
        requirements.extend(
            self._extract_initiation_requirements(initiation, jurisdiction, version, base_citations)
        )

        # Extract from compensation section
        compensation = pack_data.get("compensation", {})
        requirements.extend(
            self._extract_compensation_requirements(compensation, jurisdiction, version, base_citations)
        )

        # Extract from owner_rights section
        owner_rights = pack_data.get("owner_rights", {})
        requirements.extend(
            self._extract_owner_rights_requirements(owner_rights, jurisdiction, version, base_citations)
        )

        # Extract from deadline_chains
        for chain in pack_data.get("deadline_chains", []):
            requirements.extend(
                self._extract_deadline_chain_requirements(chain, jurisdiction, version)
            )

        # Extract from triggers
        for trigger in pack_data.get("triggers", []):
            requirements.extend(
                self._extract_trigger_requirements(trigger, jurisdiction, version)
            )

        return requirements

    def _extract_initiation_requirements(
        self,
        initiation: dict[str, Any],
        jurisdiction: str,
        version: str,
        base_citations: dict[str, Any],
    ) -> list[NormalizedRequirement]:
        """Extract requirements from initiation section."""
        reqs = []

        # Bill of Rights requirement
        if initiation.get("landowner_bill_of_rights"):
            reqs.append(NormalizedRequirement(
                requirement_id=f"{jurisdiction.lower()}.notice.bill_of_rights",
                state=jurisdiction.upper(),
                topic="notice",
                trigger_event="pre_final_offer",
                required_action="Provide Landowner Bill of Rights document",
                deadline_rule=f"{initiation.get('bill_of_rights_notice_days', 7)}_days_before_final_offer",
                deadline_days=initiation.get("bill_of_rights_notice_days", 7),
                doc_requirements=["landowner_bill_of_rights"],
                citations=[{
                    "citation": initiation.get("bill_of_rights_citation", base_citations.get("primary", "")),
                    "authority_level": "statute",
                }],
                authority_level="statute",
                effective_date=None,
                version=version,
                confidence=1.0,
                notes=None,
            ))

        # Initial offer wait period
        if initiation.get("initial_offer_days"):
            reqs.append(NormalizedRequirement(
                requirement_id=f"{jurisdiction.lower()}.offer.initial_wait",
                state=jurisdiction.upper(),
                topic="offer",
                trigger_event="initial_offer_served",
                required_action=f"Wait {initiation['initial_offer_days']} days before final offer",
                deadline_rule=f"{initiation['initial_offer_days']}_days_after_initial_offer",
                deadline_days=initiation["initial_offer_days"],
                doc_requirements=[],
                citations=[{"citation": base_citations.get("primary", ""), "authority_level": "statute"}],
                authority_level="statute",
                effective_date=None,
                version=version,
                confidence=1.0,
                notes=None,
            ))

        # Final offer consideration period
        if initiation.get("final_offer_days"):
            reqs.append(NormalizedRequirement(
                requirement_id=f"{jurisdiction.lower()}.offer.final_consideration",
                state=jurisdiction.upper(),
                topic="offer",
                trigger_event="final_offer_served",
                required_action=f"Allow {initiation['final_offer_days']} days for owner consideration",
                deadline_rule=f"{initiation['final_offer_days']}_days_after_final_offer",
                deadline_days=initiation["final_offer_days"],
                doc_requirements=[],
                citations=[{"citation": base_citations.get("primary", ""), "authority_level": "statute"}],
                authority_level="statute",
                effective_date=None,
                version=version,
                confidence=1.0,
                notes=None,
            ))

        # Resolution of Necessity
        if initiation.get("resolution_required"):
            reqs.append(NormalizedRequirement(
                requirement_id=f"{jurisdiction.lower()}.filing.resolution_of_necessity",
                state=jurisdiction.upper(),
                topic="filing",
                trigger_event="pre_condemnation",
                required_action="Obtain Resolution of Necessity",
                deadline_rule="before_filing_petition",
                deadline_days=None,
                doc_requirements=["resolution_of_necessity"],
                citations=[{"citation": base_citations.get("primary", ""), "authority_level": "statute"}],
                authority_level="statute",
                effective_date=None,
                version=version,
                confidence=1.0,
                notes="Required before filing condemnation petition",
            ))

        return reqs

    def _extract_compensation_requirements(
        self,
        compensation: dict[str, Any],
        jurisdiction: str,
        version: str,
        base_citations: dict[str, Any],
    ) -> list[NormalizedRequirement]:
        """Extract requirements from compensation section."""
        reqs = []

        # Attorney fees
        attorney_fees = compensation.get("attorney_fees", {})
        if attorney_fees.get("automatic") or attorney_fees.get("threshold_based"):
            reqs.append(NormalizedRequirement(
                requirement_id=f"{jurisdiction.lower()}.attorney_fees.recovery",
                state=jurisdiction.upper(),
                topic="attorney_fees",
                trigger_event="award_determination",
                required_action="Calculate attorney fee recovery eligibility",
                deadline_rule=None,
                deadline_days=None,
                doc_requirements=[],
                citations=[{
                    "citation": attorney_fees.get("citation", ""),
                    "authority_level": "statute",
                }],
                authority_level="statute",
                effective_date=None,
                version=version,
                confidence=1.0,
                notes=f"Automatic: {attorney_fees.get('automatic')}, Threshold: {attorney_fees.get('threshold_percent')}%",
            ))

        # Residence multiplier
        if compensation.get("residence_multiplier"):
            reqs.append(NormalizedRequirement(
                requirement_id=f"{jurisdiction.lower()}.compensation.residence_multiplier",
                state=jurisdiction.upper(),
                topic="compensation",
                trigger_event="valuation",
                required_action=f"Apply {compensation['residence_multiplier']}x multiplier for owner-occupied residence",
                deadline_rule=None,
                deadline_days=None,
                doc_requirements=[],
                citations=[{"citation": base_citations.get("primary", ""), "authority_level": "statute"}],
                authority_level="statute",
                effective_date=None,
                version=version,
                confidence=1.0,
                notes=None,
            ))

        return reqs

    def _extract_owner_rights_requirements(
        self,
        owner_rights: dict[str, Any],
        jurisdiction: str,
        version: str,
        base_citations: dict[str, Any],
    ) -> list[NormalizedRequirement]:
        """Extract requirements from owner_rights section."""
        reqs = []

        notice_periods = owner_rights.get("notice_periods", {})

        # Hearing notice
        if notice_periods.get("hearing_notice_days"):
            reqs.append(NormalizedRequirement(
                requirement_id=f"{jurisdiction.lower()}.notice.hearing",
                state=jurisdiction.upper(),
                topic="notice",
                trigger_event="hearing_scheduled",
                required_action=f"Provide {notice_periods['hearing_notice_days']} days notice of hearing",
                deadline_rule=f"{notice_periods['hearing_notice_days']}_days_before_hearing",
                deadline_days=notice_periods["hearing_notice_days"],
                doc_requirements=["hearing_notice"],
                citations=[{"citation": base_citations.get("primary", ""), "authority_level": "statute"}],
                authority_level="statute",
                effective_date=None,
                version=version,
                confidence=1.0,
                notes=None,
            ))

        # Objection window
        if notice_periods.get("objection_window_days"):
            reqs.append(NormalizedRequirement(
                requirement_id=f"{jurisdiction.lower()}.timeline.objection_window",
                state=jurisdiction.upper(),
                topic="timeline",
                trigger_event="commissioners_award",
                required_action=f"File objection within {notice_periods['objection_window_days']} days",
                deadline_rule=f"{notice_periods['objection_window_days']}_days_after_award",
                deadline_days=notice_periods["objection_window_days"],
                doc_requirements=["objection_filing"],
                citations=[{"citation": base_citations.get("primary", ""), "authority_level": "statute"}],
                authority_level="statute",
                effective_date=None,
                version=version,
                confidence=1.0,
                notes="Deadline to object to commissioners' award and request jury trial",
            ))

        return reqs

    def _extract_deadline_chain_requirements(
        self,
        chain: dict[str, Any],
        jurisdiction: str,
        version: str,
    ) -> list[NormalizedRequirement]:
        """Extract requirements from deadline chains."""
        reqs = []
        anchor_event = chain.get("anchor_event", "")

        for deadline in chain.get("deadlines", []):
            reqs.append(NormalizedRequirement(
                requirement_id=f"{jurisdiction.lower()}.timeline.{deadline['id']}",
                state=jurisdiction.upper(),
                topic="timeline",
                trigger_event=anchor_event,
                required_action=deadline.get("description", deadline["id"]),
                deadline_rule=f"{deadline['offset_days']}_days_{deadline.get('direction', 'after')}_{anchor_event}",
                deadline_days=deadline["offset_days"],
                doc_requirements=[],
                citations=[{
                    "citation": deadline.get("citation", ""),
                    "authority_level": "statute",
                }],
                authority_level="statute",
                effective_date=None,
                version=version,
                confidence=1.0,
                notes=deadline.get("notes"),
            ))

        return reqs

    def _extract_trigger_requirements(
        self,
        trigger: dict[str, Any],
        jurisdiction: str,
        version: str,
    ) -> list[NormalizedRequirement]:
        """Extract requirements from triggers."""
        reqs = []

        for deadline in trigger.get("deadlines", []):
            reqs.append(NormalizedRequirement(
                requirement_id=f"{jurisdiction.lower()}.trigger.{trigger['id']}.{deadline['id']}",
                state=jurisdiction.upper(),
                topic="timeline",
                trigger_event=trigger.get("match", ""),
                required_action=deadline.get("description", deadline["id"]),
                deadline_rule=f"{deadline['offset_days']}_days",
                deadline_days=deadline["offset_days"],
                doc_requirements=[],
                citations=[{
                    "citation": deadline.get("citation", ""),
                    "authority_level": "statute",
                }],
                authority_level="statute",
                effective_date=None,
                version=version,
                confidence=1.0,
                notes=trigger.get("description"),
            ))

        return reqs

    def validate_pack(
        self,
        pack_id: str,
        yaml_content: Optional[str] = None,
    ) -> ValidationResult:
        """Validate a requirement pack for schema and consistency.
        
        Args:
            pack_id: Pack identifier
            yaml_content: Optional YAML content (if not provided, reads from staging)
            
        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        # Load pack content
        if yaml_content is None:
            staging_path = self.storage_path / "staging" / f"{pack_id}.yaml"
            if not staging_path.exists():
                return ValidationResult(
                    valid=False,
                    errors=[f"Pack {pack_id} not found in staging"],
                )
            yaml_content = staging_path.read_text()

        # Parse YAML
        try:
            pack_data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            return ValidationResult(valid=False, errors=[f"YAML parse error: {e}"])

        # Required fields
        if not pack_data.get("version"):
            errors.append("Missing 'version' field")
        if not pack_data.get("jurisdiction"):
            errors.append("Missing 'jurisdiction' field")

        # Version format
        version = pack_data.get("version", "")
        if version and not self._is_valid_semver(version):
            errors.append(f"Invalid version format: {version} (expected semver)")

        # Jurisdiction format
        jurisdiction = pack_data.get("jurisdiction", "")
        if jurisdiction and (len(jurisdiction) != 2 or not jurisdiction.isalpha()):
            errors.append(f"Invalid jurisdiction format: {jurisdiction} (expected 2-letter state code)")

        # Validate triggers
        for i, trigger in enumerate(pack_data.get("triggers", [])):
            if not trigger.get("id"):
                errors.append(f"Trigger {i} missing 'id' field")
            if not trigger.get("match"):
                errors.append(f"Trigger {trigger.get('id', i)} missing 'match' expression")
            
            # Validate match expression syntax (basic check)
            match_expr = trigger.get("match", "")
            if match_expr and not self._is_valid_expression(match_expr):
                warnings.append(f"Trigger {trigger.get('id')}: match expression may be invalid")

        # Validate deadline chains
        for i, chain in enumerate(pack_data.get("deadline_chains", [])):
            if not chain.get("anchor_event"):
                errors.append(f"Deadline chain {i} missing 'anchor_event'")
            for j, deadline in enumerate(chain.get("deadlines", [])):
                if not deadline.get("id"):
                    errors.append(f"Deadline {j} in chain {i} missing 'id'")
                if deadline.get("offset_days") is None:
                    errors.append(f"Deadline {deadline.get('id', j)} missing 'offset_days'")
                if not deadline.get("citation"):
                    warnings.append(f"Deadline {deadline.get('id', j)} missing citation")

        # Check for required sections
        required_sections = ["initiation", "compensation", "owner_rights"]
        for section in required_sections:
            if section not in pack_data:
                warnings.append(f"Missing '{section}' section")

        # Collect topics covered
        topics_covered = set()
        if pack_data.get("initiation"):
            topics_covered.add("notice")
            topics_covered.add("offer")
        if pack_data.get("compensation"):
            topics_covered.add("compensation")
            topics_covered.add("attorney_fees")
        if pack_data.get("owner_rights"):
            topics_covered.add("trial")
            topics_covered.add("hearing")
        if pack_data.get("deadline_chains"):
            topics_covered.add("timeline")

        # Count requirements
        requirements = self._normalize_pack_to_requirements(pack_data, jurisdiction)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            requirements_count=len(requirements),
            topics_covered=list(topics_covered),
        )

    def _is_valid_semver(self, version: str) -> bool:
        """Check if version follows semver format."""
        parts = version.split(".")
        if len(parts) != 3:
            return False
        return all(part.isdigit() for part in parts)

    def _is_valid_expression(self, expr: str) -> bool:
        """Basic validation of match expression."""
        # Check for balanced parentheses
        paren_count = 0
        for char in expr:
            if char == "(":
                paren_count += 1
            elif char == ")":
                paren_count -= 1
            if paren_count < 0:
                return False
        return paren_count == 0

    def diff_packs(
        self,
        from_version_id: str,
        to_version_id: str,
    ) -> PackDiff:
        """Generate diff between two pack versions.
        
        Args:
            from_version_id: Source version pack ID
            to_version_id: Target version pack ID
            
        Returns:
            PackDiff with added, removed, and modified requirements
        """
        # Load both versions
        from_path = self.storage_path / "staging" / f"{from_version_id}.yaml"
        to_path = self.storage_path / "staging" / f"{to_version_id}.yaml"

        from_data = yaml.safe_load(from_path.read_text()) if from_path.exists() else {}
        to_data = yaml.safe_load(to_path.read_text()) if to_path.exists() else {}

        jurisdiction = to_data.get("jurisdiction", from_data.get("jurisdiction", ""))

        # Extract requirements
        from_reqs = {
            r.requirement_id: r.to_dict()
            for r in self._normalize_pack_to_requirements(from_data, jurisdiction)
        } if from_data else {}
        
        to_reqs = {
            r.requirement_id: r.to_dict()
            for r in self._normalize_pack_to_requirements(to_data, jurisdiction)
        } if to_data else {}

        # Find differences
        added = []
        removed = []
        modified = []

        # Added requirements
        for req_id in set(to_reqs.keys()) - set(from_reqs.keys()):
            added.append(to_reqs[req_id])

        # Removed requirements
        for req_id in set(from_reqs.keys()) - set(to_reqs.keys()):
            removed.append(from_reqs[req_id])

        # Modified requirements
        for req_id in set(from_reqs.keys()) & set(to_reqs.keys()):
            from_req = from_reqs[req_id]
            to_req = to_reqs[req_id]
            
            # Compare key fields
            if from_req != to_req:
                modified.append({
                    "requirement_id": req_id,
                    "from": from_req,
                    "to": to_req,
                    "changed_fields": [
                        k for k in from_req.keys()
                        if from_req.get(k) != to_req.get(k)
                    ],
                })

        # Generate summary
        summary_parts = []
        if added:
            summary_parts.append(f"{len(added)} added")
        if removed:
            summary_parts.append(f"{len(removed)} removed")
        if modified:
            summary_parts.append(f"{len(modified)} modified")
        summary = ", ".join(summary_parts) if summary_parts else "No changes"

        return PackDiff(
            from_version=from_data.get("version", "unknown"),
            to_version=to_data.get("version", "unknown"),
            added=added,
            removed=removed,
            modified=modified,
            summary=summary,
        )

    def publish_pack(
        self,
        pack_id: str,
        user_id: str,
        effective_date: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Publish a validated pack to active status.
        
        Args:
            pack_id: Pack identifier
            user_id: ID of user publishing
            effective_date: When the pack becomes effective
            
        Returns:
            Published pack information
        """
        staging_path = self.storage_path / "staging" / f"{pack_id}.yaml"
        if not staging_path.exists():
            raise ValueError(f"Pack {pack_id} not found in staging")

        # Validate first
        validation = self.validate_pack(pack_id)
        if not validation.valid:
            raise ValueError(f"Pack validation failed: {validation.errors}")

        yaml_content = staging_path.read_text()
        pack_data = yaml.safe_load(yaml_content)
        jurisdiction = pack_data.get("jurisdiction", "").lower()
        version = pack_data.get("version", "1.0.0")

        # Archive current active version if exists
        active_path = self.storage_path / f"{jurisdiction}.yaml"
        if active_path.exists():
            archive_name = f"{jurisdiction}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.yaml"
            archive_path = self.storage_path / "archive" / archive_name
            active_path.rename(archive_path)

        # Move from staging to active
        staging_path.rename(active_path)

        return {
            "pack_id": pack_id,
            "jurisdiction": jurisdiction.upper(),
            "version": version,
            "status": "active",
            "published_by": user_id,
            "published_at": datetime.utcnow().isoformat(),
            "effective_date": effective_date.isoformat() if effective_date else None,
            "active_path": str(active_path),
        }

    def get_active_pack(self, jurisdiction: str) -> Optional[dict[str, Any]]:
        """Get the currently active pack for a jurisdiction.
        
        Args:
            jurisdiction: Two-letter state code
            
        Returns:
            Pack data or None if not found
        """
        active_path = self.storage_path / f"{jurisdiction.lower()}.yaml"
        if not active_path.exists():
            return None

        yaml_content = active_path.read_text()
        pack_data = yaml.safe_load(yaml_content)
        
        return {
            "jurisdiction": jurisdiction.upper(),
            "version": pack_data.get("version"),
            "content": pack_data,
            "content_hash": sha256_hex(yaml_content.encode()),
            "path": str(active_path),
        }

    def list_jurisdictions(self) -> list[dict[str, Any]]:
        """List all jurisdictions with active packs.
        
        Returns:
            List of jurisdiction info
        """
        jurisdictions = []
        
        for path in self.storage_path.glob("*.yaml"):
            if path.stem in ["base", "schema"]:
                continue
            if len(path.stem) == 2 and path.stem.isalpha():
                pack_data = yaml.safe_load(path.read_text())
                jurisdictions.append({
                    "jurisdiction": path.stem.upper(),
                    "version": pack_data.get("version"),
                    "has_triggers": len(pack_data.get("triggers", [])) > 0,
                    "has_deadline_chains": len(pack_data.get("deadline_chains", [])) > 0,
                })

        return sorted(jurisdictions, key=lambda x: x["jurisdiction"])


# Stub for Regulatory Update Monitor job
async def check_regulatory_updates(jurisdiction: Optional[str] = None) -> list[dict[str, Any]]:
    """Check for regulatory updates (stub implementation).
    
    In production, this would:
    1. Query Westlaw/LexisNexis APIs
    2. Check state legislature RSS feeds
    3. Monitor court docket systems
    4. Use AI to analyze impact
    
    Args:
        jurisdiction: Optional state code to check (None = all states)
        
    Returns:
        List of detected updates
    """
    # Stub - returns empty list
    # TODO: Implement actual regulatory monitoring
    return []


async def propose_pack_update(
    jurisdiction: str,
    update: dict[str, Any],
) -> dict[str, Any]:
    """Propose a pack update based on regulatory change.
    
    Args:
        jurisdiction: State code
        update: Detected regulatory update
        
    Returns:
        Proposed pack changes
    """
    # Stub - returns empty proposal
    # TODO: Implement AI-assisted update proposal
    return {
        "jurisdiction": jurisdiction,
        "update_type": update.get("change_type"),
        "proposed_changes": [],
        "requires_review": True,
    }
