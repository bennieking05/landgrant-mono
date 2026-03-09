"""Document QA and Risk Scoring Service.

Provides pre-send/pre-filing quality checks:
- Required clause verification
- Name/date consistency
- Legal description validation
- Deadline accuracy
- Citation validity
- Risk scoring (red/yellow/green)

No document should be sent or filed without passing QA.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from app.services.hashing import sha256_hex


@dataclass
class QACheckConfig:
    """Configuration for a QA check."""
    check_type: str
    name: str
    description: str
    required: bool = True
    escalate_on_fail: bool = False
    severity: str = "error"  # error, warning, info


@dataclass
class QACheckResult:
    """Result of a single QA check."""
    check_type: str
    name: str
    passed: bool
    risk_level: str  # green, yellow, red
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    location: Optional[str] = None
    error_message: Optional[str] = None
    fix_suggestion: Optional[str] = None
    citation_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "check_type": self.check_type,
            "name": self.name,
            "passed": self.passed,
            "risk_level": self.risk_level,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "location": self.location,
            "error_message": self.error_message,
            "fix_suggestion": self.fix_suggestion,
            "citation_id": self.citation_id,
        }


@dataclass
class QAReport:
    """Complete QA report for a document."""
    id: str
    document_id: str
    document_hash: str
    jurisdiction: Optional[str]
    
    # Overall result
    risk_level: str  # green, yellow, red
    passed: bool
    
    # Check counts
    checks_performed: int
    checks_passed: int
    checks_failed: int
    checks_warned: int
    
    # Issues
    critical_issues: list[QACheckResult]
    warnings: list[QACheckResult]
    suggestions: list[QACheckResult]
    
    # Clauses
    required_clauses_present: list[str]
    required_clauses_missing: list[str]
    
    # Citations
    citations_validated: int
    citations_invalid: int
    citation_issues: list[dict[str, Any]]
    
    # Escalation
    requires_counsel_review: bool
    escalation_reason: Optional[str]
    
    # Timing
    checked_at: datetime
    
    # All results
    all_results: list[QACheckResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "document_hash": self.document_hash,
            "jurisdiction": self.jurisdiction,
            "risk_level": self.risk_level,
            "passed": self.passed,
            "checks_performed": self.checks_performed,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "checks_warned": self.checks_warned,
            "critical_issues": [i.to_dict() for i in self.critical_issues],
            "warnings": [w.to_dict() for w in self.warnings],
            "suggestions": [s.to_dict() for s in self.suggestions],
            "required_clauses_present": self.required_clauses_present,
            "required_clauses_missing": self.required_clauses_missing,
            "citations_validated": self.citations_validated,
            "citations_invalid": self.citations_invalid,
            "citation_issues": self.citation_issues,
            "requires_counsel_review": self.requires_counsel_review,
            "escalation_reason": self.escalation_reason,
            "checked_at": self.checked_at.isoformat(),
        }


# State-specific required clauses
STATE_REQUIRED_CLAUSES = {
    "TX": [
        {"id": "bill_of_rights_reference", "pattern": r"Landowner.*Bill.*Rights", "description": "Reference to Landowner Bill of Rights"},
        {"id": "property_code_citation", "pattern": r"Tex.*Prop.*Code.*§\s*21", "description": "Texas Property Code Chapter 21 citation"},
        {"id": "just_compensation", "pattern": r"(adequate|just)\s+compensation", "description": "Compensation language"},
    ],
    "FL": [
        {"id": "full_compensation", "pattern": r"full\s+compensation", "description": "Florida's 'full compensation' standard"},
        {"id": "fee_disclosure", "pattern": r"attorney.*fee", "description": "Attorney fee disclosure"},
    ],
    "CA": [
        {"id": "resolution_necessity", "pattern": r"resolution.*necessity", "description": "Resolution of Necessity reference"},
        {"id": "goodwill_notice", "pattern": r"business.*goodwill", "description": "Business goodwill compensation notice"},
    ],
    "MI": [
        {"id": "multiplier_disclosure", "pattern": r"125.*percent|1\.25", "description": "125% residence multiplier disclosure"},
        {"id": "fee_reimbursement", "pattern": r"(attorney|appraiser).*fee.*reimburs", "description": "Fee reimbursement notice"},
    ],
    "MO": [
        {"id": "heritage_multiplier", "pattern": r"(150|125).*percent|heritage|homestead", "description": "Heritage/homestead multiplier"},
    ],
}

# Forbidden language patterns
FORBIDDEN_LANGUAGE = [
    {"pattern": r"waive.*all.*rights", "reason": "Cannot require waiver of all rights", "severity": "red"},
    {"pattern": r"final.*offer.*no.*negotiation", "reason": "Must allow good faith negotiation", "severity": "yellow"},
    {"pattern": r"confidential.*settlement", "reason": "Confidentiality clauses may be restricted", "severity": "yellow"},
    {"pattern": r"take.*it.*or.*leave.*it", "reason": "Coercive language", "severity": "red"},
]


class QACheckService:
    """Service for document QA checks."""

    def __init__(self):
        """Initialize the service."""
        self._reports: dict[str, QAReport] = {}

    def check_document(
        self,
        document_content: str,
        document_id: str,
        jurisdiction: str,
        document_type: str,
        context: Optional[dict[str, Any]] = None,
    ) -> QAReport:
        """Run all QA checks on a document.
        
        Args:
            document_content: Document text content
            document_id: Document identifier
            jurisdiction: State code
            document_type: Type of document (offer, petition, deed, etc.)
            context: Additional context (names, dates, amounts, etc.)
            
        Returns:
            Complete QA report
        """
        context = context or {}
        report_id = f"qa_{uuid.uuid4().hex[:12]}"
        document_hash = sha256_hex(document_content.encode())
        
        results: list[QACheckResult] = []
        
        # Run required clause checks
        clause_results = self._check_required_clauses(
            document_content, jurisdiction, document_type
        )
        results.extend(clause_results)
        
        # Run forbidden language checks
        forbidden_results = self._check_forbidden_language(document_content)
        results.extend(forbidden_results)
        
        # Run name consistency checks
        if context.get("parties"):
            name_results = self._check_name_consistency(
                document_content, context["parties"]
            )
            results.extend(name_results)
        
        # Run date consistency checks
        if context.get("dates"):
            date_results = self._check_date_consistency(
                document_content, context["dates"]
            )
            results.extend(date_results)
        
        # Run legal description checks
        if context.get("legal_description"):
            legal_results = self._check_legal_description(
                document_content, context["legal_description"]
            )
            results.extend(legal_results)
        
        # Run amount accuracy checks
        if context.get("amounts"):
            amount_results = self._check_amounts(
                document_content, context["amounts"]
            )
            results.extend(amount_results)
        
        # Run deadline checks
        if context.get("deadlines"):
            deadline_results = self._check_deadlines(
                document_content, context["deadlines"]
            )
            results.extend(deadline_results)
        
        # Categorize results
        critical_issues = [r for r in results if not r.passed and r.risk_level == "red"]
        warnings = [r for r in results if not r.passed and r.risk_level == "yellow"]
        suggestions = [r for r in results if not r.passed and r.risk_level == "green"]
        
        # Calculate counts
        checks_passed = sum(1 for r in results if r.passed)
        checks_failed = sum(1 for r in results if not r.passed and r.risk_level == "red")
        checks_warned = sum(1 for r in results if not r.passed and r.risk_level == "yellow")
        
        # Determine overall risk level
        if critical_issues:
            risk_level = "red"
        elif warnings:
            risk_level = "yellow"
        else:
            risk_level = "green"
        
        # Check for required clauses
        clause_checks = [r for r in results if r.check_type == "required_clause"]
        required_clauses_present = [r.name for r in clause_checks if r.passed]
        required_clauses_missing = [r.name for r in clause_checks if not r.passed]
        
        # Determine if counsel review is needed
        requires_counsel_review = (
            risk_level == "red" or
            len(required_clauses_missing) > 0 or
            any(r.check_type == "forbidden_language" and not r.passed for r in results)
        )
        
        escalation_reason = None
        if requires_counsel_review:
            reasons = []
            if critical_issues:
                reasons.append(f"{len(critical_issues)} critical issues")
            if required_clauses_missing:
                reasons.append(f"Missing clauses: {', '.join(required_clauses_missing)}")
            escalation_reason = "; ".join(reasons)
        
        report = QAReport(
            id=report_id,
            document_id=document_id,
            document_hash=document_hash,
            jurisdiction=jurisdiction,
            risk_level=risk_level,
            passed=risk_level == "green",
            checks_performed=len(results),
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            checks_warned=checks_warned,
            critical_issues=critical_issues,
            warnings=warnings,
            suggestions=suggestions,
            required_clauses_present=required_clauses_present,
            required_clauses_missing=required_clauses_missing,
            citations_validated=0,
            citations_invalid=0,
            citation_issues=[],
            requires_counsel_review=requires_counsel_review,
            escalation_reason=escalation_reason,
            checked_at=datetime.utcnow(),
            all_results=results,
        )
        
        self._reports[report_id] = report
        return report

    def _check_required_clauses(
        self,
        content: str,
        jurisdiction: str,
        document_type: str,
    ) -> list[QACheckResult]:
        """Check for required clauses by jurisdiction."""
        results = []
        
        # Get jurisdiction-specific clauses
        clauses = STATE_REQUIRED_CLAUSES.get(jurisdiction.upper(), [])
        
        for clause in clauses:
            pattern = clause["pattern"]
            match = re.search(pattern, content, re.IGNORECASE)
            
            results.append(QACheckResult(
                check_type="required_clause",
                name=clause["id"],
                passed=match is not None,
                risk_level="red" if match is None else "green",
                expected_value=clause["description"],
                actual_value="Found" if match else "Not found",
                location=f"Position {match.start()}" if match else None,
                error_message=f"Missing required clause: {clause['description']}" if not match else None,
                fix_suggestion=f"Add language referencing {clause['description']}" if not match else None,
            ))
        
        return results

    def _check_forbidden_language(self, content: str) -> list[QACheckResult]:
        """Check for forbidden language patterns."""
        results = []
        
        for forbidden in FORBIDDEN_LANGUAGE:
            pattern = forbidden["pattern"]
            match = re.search(pattern, content, re.IGNORECASE)
            
            if match:
                results.append(QACheckResult(
                    check_type="forbidden_language",
                    name=f"forbidden_{forbidden['pattern'][:20]}",
                    passed=False,
                    risk_level=forbidden["severity"],
                    expected_value="Should not contain",
                    actual_value=match.group(0),
                    location=f"Position {match.start()}",
                    error_message=forbidden["reason"],
                    fix_suggestion="Remove or rephrase this language",
                ))
        
        return results

    def _check_name_consistency(
        self,
        content: str,
        parties: list[dict[str, Any]],
    ) -> list[QACheckResult]:
        """Check name consistency throughout document."""
        results = []
        
        for party in parties:
            name = party.get("name", "")
            role = party.get("role", "party")
            
            if not name:
                continue
            
            # Check if name appears in document
            occurrences = len(re.findall(re.escape(name), content, re.IGNORECASE))
            
            results.append(QACheckResult(
                check_type="name_consistency",
                name=f"name_{role}",
                passed=occurrences > 0,
                risk_level="yellow" if occurrences == 0 else "green",
                expected_value=name,
                actual_value=f"Found {occurrences} times",
                error_message=f"Name '{name}' not found in document" if occurrences == 0 else None,
                fix_suggestion="Verify party name is correctly included" if occurrences == 0 else None,
            ))
        
        return results

    def _check_date_consistency(
        self,
        content: str,
        dates: dict[str, str],
    ) -> list[QACheckResult]:
        """Check date consistency in document."""
        results = []
        
        for date_name, date_value in dates.items():
            if not date_value:
                continue
            
            found = date_value in content
            
            results.append(QACheckResult(
                check_type="date_consistency",
                name=f"date_{date_name}",
                passed=found,
                risk_level="yellow" if not found else "green",
                expected_value=date_value,
                actual_value="Found" if found else "Not found",
                error_message=f"Date {date_name} ({date_value}) not found" if not found else None,
                fix_suggestion="Verify date is correctly formatted" if not found else None,
            ))
        
        return results

    def _check_legal_description(
        self,
        content: str,
        legal_description: str,
    ) -> list[QACheckResult]:
        """Check legal description accuracy."""
        results = []
        
        # Check if legal description is present
        found = legal_description.lower()[:50] in content.lower()
        
        results.append(QACheckResult(
            check_type="legal_description",
            name="legal_description_present",
            passed=found,
            risk_level="red" if not found else "green",
            expected_value=legal_description[:100] + "...",
            actual_value="Found" if found else "Not found",
            error_message="Legal description does not match source documents" if not found else None,
            fix_suggestion="Verify legal description matches deed/title" if not found else None,
        ))
        
        return results

    def _check_amounts(
        self,
        content: str,
        amounts: dict[str, float],
    ) -> list[QACheckResult]:
        """Check monetary amounts in document."""
        results = []
        
        for amount_name, amount_value in amounts.items():
            # Format amount for searching
            formatted = f"${amount_value:,.2f}"
            found = formatted in content
            
            # Also try without cents
            if not found:
                formatted_int = f"${int(amount_value):,}"
                found = formatted_int in content
            
            results.append(QACheckResult(
                check_type="amount_accuracy",
                name=f"amount_{amount_name}",
                passed=found,
                risk_level="red" if not found else "green",
                expected_value=formatted,
                actual_value="Found" if found else "Not found",
                error_message=f"Amount {amount_name} ({formatted}) not found" if not found else None,
                fix_suggestion="Verify amount matches appraisal/calculation" if not found else None,
            ))
        
        return results

    def _check_deadlines(
        self,
        content: str,
        deadlines: dict[str, str],
    ) -> list[QACheckResult]:
        """Check deadline accuracy in document."""
        results = []
        
        for deadline_name, deadline_value in deadlines.items():
            found = deadline_value in content
            
            results.append(QACheckResult(
                check_type="deadline_accuracy",
                name=f"deadline_{deadline_name}",
                passed=found,
                risk_level="yellow" if not found else "green",
                expected_value=deadline_value,
                actual_value="Found" if found else "Not found",
                error_message=f"Deadline {deadline_name} ({deadline_value}) not found" if not found else None,
                fix_suggestion="Verify deadline matches statutory requirements" if not found else None,
            ))
        
        return results

    def get_report(self, report_id: str) -> Optional[QAReport]:
        """Get a QA report by ID.
        
        Args:
            report_id: Report identifier
            
        Returns:
            Report or None
        """
        return self._reports.get(report_id)

    def list_reports(
        self,
        document_id: Optional[str] = None,
        risk_level: Optional[str] = None,
        limit: int = 100,
    ) -> list[QAReport]:
        """List QA reports with filters.
        
        Args:
            document_id: Filter by document
            risk_level: Filter by risk level
            limit: Maximum reports to return
            
        Returns:
            Matching reports
        """
        reports = list(self._reports.values())
        
        if document_id:
            reports = [r for r in reports if r.document_id == document_id]
        if risk_level:
            reports = [r for r in reports if r.risk_level == risk_level]
        
        reports.sort(key=lambda r: r.checked_at, reverse=True)
        return reports[:limit]


def calculate_risk_score(
    qa_report: QAReport,
    citation_check: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Calculate overall risk score for a document.
    
    Combines QA report with citation verification for
    final risk assessment.
    
    Args:
        qa_report: QA report
        citation_check: Optional citation verification result
        
    Returns:
        Risk score with details
    """
    # Base score from QA
    base_score = 100
    
    # Deduct for issues
    base_score -= len(qa_report.critical_issues) * 25
    base_score -= len(qa_report.warnings) * 10
    base_score -= len(qa_report.required_clauses_missing) * 15
    
    # Deduct for citation issues
    if citation_check:
        if not citation_check.get("all_valid", True):
            base_score -= 20
        missing = len(citation_check.get("missing_citations", []))
        base_score -= missing * 10
    
    # Ensure score is in bounds
    base_score = max(0, min(100, base_score))
    
    # Determine risk level
    if base_score >= 80:
        risk_level = "green"
    elif base_score >= 50:
        risk_level = "yellow"
    else:
        risk_level = "red"
    
    return {
        "score": base_score,
        "risk_level": risk_level,
        "qa_passed": qa_report.passed,
        "requires_counsel_review": base_score < 80 or qa_report.requires_counsel_review,
        "issues_summary": {
            "critical": len(qa_report.critical_issues),
            "warnings": len(qa_report.warnings),
            "missing_clauses": len(qa_report.required_clauses_missing),
            "citation_issues": citation_check.get("citations_invalid", 0) if citation_check else 0,
        },
    }
