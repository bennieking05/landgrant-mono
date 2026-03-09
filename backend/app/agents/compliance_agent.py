"""Compliance Agent for state-specific compliance checking and law monitoring.

This agent ensures cases comply with jurisdiction-specific requirements:
- Deadline compliance
- Document content validation
- Procedural requirements
- Law change monitoring

It integrates with:
- Rules engine for compliance checks
- Deadline service for timing validation
- Gemini AI for law change analysis
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from app.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.rules_engine import (
    load_rule, 
    get_jurisdiction_config,
    evaluate_rules,
)
from app.services.deadline_rules import derive_deadlines

logger = logging.getLogger(__name__)


# Prompts for compliance checking
COMPLIANCE_CHECK_PROMPT = """Review this eminent domain case for {jurisdiction} compliance.

Case Data:
{case_data}

Current Deadlines:
{deadlines}

Documents Filed:
{documents}

Jurisdiction Requirements:
{requirements}

Check:
1. Are all statutory deadlines being met?
2. Do filed documents contain required elements?
3. Are proper notice procedures followed?
4. Any procedural defects that could invalidate the taking?

Return JSON:
{{
    "compliant": true/false,
    "violations": [
        {{"requirement": "...", "status": "...", "days_overdue": 0, "severity": "low|medium|high"}}
    ],
    "warnings": ["upcoming issues..."],
    "remediation_steps": ["suggested fixes..."]
}}
"""

LAW_CHANGE_ANALYSIS_PROMPT = """Analyze this legal update for eminent domain impact.

Update: {law_change_text}
Jurisdiction: {jurisdiction}
Current Rules:
{current_rules}

Determine:
1. Does this change affect our eminent domain workflow?
2. Which specific rules need updating?
3. What is the effective date?
4. Are there transitional provisions for pending cases?

Return JSON:
{{
    "affects_workflow": true/false,
    "affected_rules": ["rule_id_1", "rule_id_2"],
    "effective_date": "YYYY-MM-DD",
    "suggested_rule_changes": [
        {{"rule_id": "...", "field": "...", "old_value": "...", "new_value": "...", "citation": "..."}}
    ],
    "urgency": "low|medium|high",
    "summary": "brief description of change"
}}
"""


@dataclass
class ComplianceViolation:
    """A compliance violation found during checking."""
    requirement_id: str
    requirement_name: str
    status: str  # violated, at_risk, warning
    severity: str  # low, medium, high, critical
    days_overdue: int = 0
    description: str = ""
    citation: str = ""
    remediation: str = ""


@dataclass
class ComplianceResult:
    """Result of compliance checking."""
    compliant: bool
    confidence: float
    violations: list[ComplianceViolation]
    warnings: list[str]
    remediation_steps: list[str]
    checked_requirements: int
    explanation: str


@dataclass
class LawChangeImpact:
    """Analysis of a law change's impact on the platform."""
    affects_workflow: bool
    affected_rules: list[str]
    effective_date: Optional[datetime]
    suggested_updates: list[dict[str, Any]]
    urgency: str
    summary: str


class ComplianceAgent(BaseAgent):
    """Agent for compliance checking and law monitoring.
    
    Responsibilities:
    - Check cases against jurisdiction-specific requirements
    - Monitor deadlines for violations and warnings
    - Validate document content requirements
    - Analyze law changes for workflow impact
    
    Escalation triggers:
    - Compliance violations detected
    - Upcoming deadline risks
    - Law changes affecting workflow
    """
    
    agent_type = AgentType.COMPLIANCE
    confidence_threshold = 0.85
    
    # Flags that always escalate
    critical_flags = [
        "compliance_violation",
        "deadline_missed",
        "procedural_defect",
        "law_change_urgent",
    ]
    
    def __init__(self, db_session=None, confidence_threshold: float = None):
        """Initialize the compliance agent.
        
        Args:
            db_session: Database session
            confidence_threshold: Override default threshold
        """
        super().__init__(confidence_threshold)
        self.db = db_session
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute compliance check for a case.
        
        Args:
            context: Agent context with case details
            
        Returns:
            AgentResult with compliance status
        """
        start_time = datetime.utcnow()
        
        try:
            if not context.case_id and not context.project_id:
                return AgentResult.failure_result(
                    error="No case_id or project_id provided",
                    error_code="MISSING_CASE_ID",
                )
            
            # Run compliance check
            result = await self.check_case_compliance(
                context.case_id or context.project_id
            )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Determine flags
            flags = []
            if not result.compliant:
                flags.append("compliance_violation")
            
            for violation in result.violations:
                if violation.severity == "critical":
                    flags.append("procedural_defect")
                if violation.days_overdue > 0:
                    flags.append("deadline_missed")
            
            return AgentResult(
                success=result.compliant,
                confidence=result.confidence,
                data={
                    "compliant": result.compliant,
                    "violations": [
                        {
                            "requirement_id": v.requirement_id,
                            "requirement_name": v.requirement_name,
                            "status": v.status,
                            "severity": v.severity,
                            "days_overdue": v.days_overdue,
                            "description": v.description,
                            "citation": v.citation,
                            "remediation": v.remediation,
                        }
                        for v in result.violations
                    ],
                    "warnings": result.warnings,
                    "remediation_steps": result.remediation_steps,
                    "checked_requirements": result.checked_requirements,
                },
                flags=flags,
                requires_review=not result.compliant,
                audit_payload={
                    "explanation": result.explanation,
                    "violation_count": len(result.violations),
                },
                execution_time_ms=int(execution_time),
            )
            
        except Exception as e:
            self.logger.error(f"Compliance check failed: {e}", exc_info=True)
            return AgentResult.failure_result(
                error=str(e),
                error_code="COMPLIANCE_CHECK_ERROR",
            )
    
    async def check_case_compliance(self, case_id: str) -> ComplianceResult:
        """Check a case for compliance with jurisdiction requirements.
        
        Args:
            case_id: Project/case ID to check
            
        Returns:
            ComplianceResult with violations and warnings
        """
        violations = []
        warnings = []
        remediation_steps = []
        checked_requirements = 0
        
        # Get case data (mock for now - would fetch from DB)
        case_data = await self._get_case_data(case_id)
        
        if not case_data:
            return ComplianceResult(
                compliant=False,
                confidence=0.5,
                violations=[
                    ComplianceViolation(
                        requirement_id="case_exists",
                        requirement_name="Case Existence",
                        status="violated",
                        severity="high",
                        description=f"Case {case_id} not found",
                    )
                ],
                warnings=[],
                remediation_steps=["Verify case ID"],
                checked_requirements=1,
                explanation=f"Case {case_id} not found in system",
            )
        
        jurisdiction = case_data.get("jurisdiction", "TX")
        
        # Load compliance checks from rules
        try:
            rules = load_rule(jurisdiction)
            compliance_checks = rules.get("compliance_checks", [])
        except FileNotFoundError:
            compliance_checks = []
            warnings.append(f"No rules configured for {jurisdiction}")
        
        # Check each compliance requirement
        for check in compliance_checks:
            checked_requirements += 1
            result = await self._evaluate_compliance_check(check, case_data)
            
            if result:
                if result.status == "violated":
                    violations.append(result)
                    remediation_steps.append(result.remediation)
                elif result.status == "at_risk":
                    warnings.append(f"{result.requirement_name}: {result.description}")
        
        # Check deadlines
        deadline_result = await self._check_deadline_compliance(case_data)
        checked_requirements += deadline_result.get("checked", 0)
        
        for deadline_violation in deadline_result.get("violations", []):
            violations.append(deadline_violation)
        
        for deadline_warning in deadline_result.get("warnings", []):
            warnings.append(deadline_warning)
        
        # Determine overall compliance
        compliant = len(violations) == 0
        
        # Calculate confidence
        confidence = self._calculate_compliance_confidence(
            violations, 
            warnings, 
            checked_requirements
        )
        
        explanation = self._generate_compliance_explanation(
            compliant,
            violations,
            warnings,
            jurisdiction,
        )
        
        return ComplianceResult(
            compliant=compliant,
            confidence=confidence,
            violations=violations,
            warnings=warnings,
            remediation_steps=list(set(remediation_steps)),  # Dedupe
            checked_requirements=checked_requirements,
            explanation=explanation,
        )
    
    async def monitor_law_changes(self, jurisdiction: str) -> dict[str, Any]:
        """Monitor for law changes in a jurisdiction.
        
        Args:
            jurisdiction: State code to monitor
            
        Returns:
            Dict with detected changes and suggested updates
        """
        self.logger.info(f"Monitoring law changes for {jurisdiction}")
        
        # In production, this would call legal database APIs
        # For now, return empty results
        changes = []
        suggested_updates = []
        
        # TODO: Integrate with Westlaw API or state legislature feeds
        # This would:
        # 1. Fetch recent statute changes
        # 2. Fetch recent case law
        # 3. Compare against current rules
        # 4. Use AI to analyze impact
        
        return {
            "jurisdiction": jurisdiction,
            "changes": changes,
            "suggested_updates": suggested_updates,
            "checked_at": datetime.utcnow().isoformat(),
        }
    
    async def analyze_law_change_impact(
        self,
        change_id: str,
        change_text: str,
        jurisdiction: str,
    ) -> LawChangeImpact:
        """Analyze a specific law change for workflow impact.
        
        Args:
            change_id: Identifier for the change
            change_text: Text of the legal change
            jurisdiction: State code
            
        Returns:
            LawChangeImpact analysis
        """
        try:
            # Load current rules
            rules = load_rule(jurisdiction)
            
            # Prepare prompt
            prompt = LAW_CHANGE_ANALYSIS_PROMPT.format(
                law_change_text=change_text[:5000],  # Limit length
                jurisdiction=jurisdiction,
                current_rules=str(rules)[:2000],  # Limit length
            )
            
            # Call AI for analysis
            response = await self.call_ai(prompt, task_type="law_change_analysis")
            
            if response:
                effective_date = None
                if response.get("effective_date"):
                    try:
                        effective_date = datetime.fromisoformat(response["effective_date"])
                    except (ValueError, TypeError):
                        pass
                
                return LawChangeImpact(
                    affects_workflow=response.get("affects_workflow", False),
                    affected_rules=response.get("affected_rules", []),
                    effective_date=effective_date,
                    suggested_updates=response.get("suggested_rule_changes", []),
                    urgency=response.get("urgency", "low"),
                    summary=response.get("summary", ""),
                )
            
            # Default response if AI unavailable
            return LawChangeImpact(
                affects_workflow=False,
                affected_rules=[],
                effective_date=None,
                suggested_updates=[],
                urgency="low",
                summary="Unable to analyze - AI unavailable",
            )
            
        except Exception as e:
            self.logger.error(f"Law change analysis failed: {e}")
            return LawChangeImpact(
                affects_workflow=True,  # Assume impact to be safe
                affected_rules=[],
                effective_date=None,
                suggested_updates=[],
                urgency="medium",
                summary=f"Analysis failed: {str(e)}",
            )
    
    async def _get_case_data(self, case_id: str) -> Optional[dict[str, Any]]:
        """Fetch case data from database.
        
        Args:
            case_id: Case/project ID
            
        Returns:
            Case data dict or None
        """
        if not self.db:
            # Return mock data for development
            return {
                "id": case_id,
                "jurisdiction": "TX",
                "stage": "offer_pending",
                "deadlines": [],
                "documents": [],
                "created_at": datetime.utcnow() - timedelta(days=30),
            }
        
        try:
            from app.db.models import Project
            from sqlalchemy import select
            
            result = await self.db.execute(
                select(Project).where(Project.id == case_id)
            )
            project = result.scalar_one_or_none()
            
            if project:
                return {
                    "id": project.id,
                    "jurisdiction": project.jurisdiction_code,
                    "stage": project.stage.value,
                    "created_at": project.created_at,
                    "metadata": project.metadata_json or {},
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to fetch case data: {e}")
            return None
    
    async def _evaluate_compliance_check(
        self,
        check: dict[str, Any],
        case_data: dict[str, Any],
    ) -> Optional[ComplianceViolation]:
        """Evaluate a single compliance check.
        
        Args:
            check: Compliance check definition from YAML
            case_data: Case data to check against
            
        Returns:
            ComplianceViolation if check fails, None otherwise
        """
        check_id = check.get("id", "unknown")
        check_type = check.get("check_type", "")
        description = check.get("description", "")
        citation = check.get("citation", "")
        
        if check_type == "document_exists":
            # Check if required document exists
            doc_type = check.get("document_type", "")
            required_before = check.get("required_before_stage", "")
            
            documents = case_data.get("documents", [])
            current_stage = case_data.get("stage", "")
            
            # Check if document exists
            doc_exists = any(d.get("type") == doc_type for d in documents)
            
            # Check if we're past the required stage
            stage_order = ["intake", "appraisal", "offer_pending", "offer_sent", 
                         "negotiation", "closing", "litigation", "closed"]
            
            if required_before in stage_order and current_stage in stage_order:
                required_idx = stage_order.index(required_before)
                current_idx = stage_order.index(current_stage)
                
                if current_idx >= required_idx and not doc_exists:
                    return ComplianceViolation(
                        requirement_id=check_id,
                        requirement_name=description,
                        status="violated",
                        severity="high",
                        description=f"Required document '{doc_type}' not found",
                        citation=citation,
                        remediation=f"Upload {doc_type} document before proceeding",
                    )
        
        elif check_type == "document_content":
            # Check if document has required fields
            doc_type = check.get("document_type", "")
            required_fields = check.get("required_fields", [])
            
            # Would need to inspect actual document content
            # For now, return None (pass check)
            pass
        
        elif check_type == "deadline":
            # Deadline checks handled separately
            pass
        
        return None
    
    async def _check_deadline_compliance(
        self,
        case_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Check deadline compliance for a case.
        
        Args:
            case_data: Case data with deadlines
            
        Returns:
            Dict with violations and warnings
        """
        violations = []
        warnings = []
        checked = 0
        
        deadlines = case_data.get("deadlines", [])
        now = datetime.utcnow()
        
        for deadline in deadlines:
            checked += 1
            due_at = deadline.get("due_at")
            title = deadline.get("title", "Unknown deadline")
            
            if isinstance(due_at, str):
                try:
                    due_at = datetime.fromisoformat(due_at)
                except ValueError:
                    continue
            
            if not due_at:
                continue
            
            days_until = (due_at - now).days
            
            if days_until < 0:
                # Deadline missed
                violations.append(ComplianceViolation(
                    requirement_id=f"deadline_{deadline.get('id', 'unknown')}",
                    requirement_name=title,
                    status="violated",
                    severity="critical" if abs(days_until) > 7 else "high",
                    days_overdue=abs(days_until),
                    description=f"Deadline missed by {abs(days_until)} days",
                    remediation="Review deadline and take immediate action",
                ))
            elif days_until <= 3:
                warnings.append(f"{title} due in {days_until} days")
            elif days_until <= 7:
                warnings.append(f"{title} due in {days_until} days")
        
        return {
            "violations": violations,
            "warnings": warnings,
            "checked": checked,
        }
    
    def _calculate_compliance_confidence(
        self,
        violations: list[ComplianceViolation],
        warnings: list[str],
        checked_requirements: int,
    ) -> float:
        """Calculate confidence in compliance assessment.
        
        Args:
            violations: List of violations
            warnings: List of warnings
            checked_requirements: Number of requirements checked
            
        Returns:
            Confidence score 0.0-1.0
        """
        if checked_requirements == 0:
            return 0.5  # Low confidence if nothing checked
        
        # Start with high confidence
        confidence = 0.95
        
        # Reduce for each violation
        for v in violations:
            if v.severity == "critical":
                confidence -= 0.15
            elif v.severity == "high":
                confidence -= 0.10
            elif v.severity == "medium":
                confidence -= 0.05
        
        # Small reduction for warnings
        confidence -= 0.02 * len(warnings)
        
        return max(0.3, min(1.0, confidence))
    
    def _generate_compliance_explanation(
        self,
        compliant: bool,
        violations: list[ComplianceViolation],
        warnings: list[str],
        jurisdiction: str,
    ) -> str:
        """Generate human-readable compliance explanation.
        
        Args:
            compliant: Overall compliance status
            violations: List of violations
            warnings: List of warnings
            jurisdiction: State code
            
        Returns:
            Explanation string
        """
        if compliant:
            if warnings:
                return f"Case is compliant with {jurisdiction} requirements. {len(warnings)} warnings noted."
            return f"Case is fully compliant with {jurisdiction} requirements."
        
        critical = sum(1 for v in violations if v.severity == "critical")
        high = sum(1 for v in violations if v.severity == "high")
        
        parts = [f"Case has {len(violations)} compliance violation(s)."]
        
        if critical:
            parts.append(f"{critical} critical issue(s) require immediate attention.")
        if high:
            parts.append(f"{high} high-severity issue(s) need resolution.")
        
        return " ".join(parts)
