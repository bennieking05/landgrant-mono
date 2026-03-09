"""API routes for Document QA and Risk Scoring.

Provides endpoints for:
- Running QA checks on documents
- Getting risk scores
- Viewing QA reports
- Pre-send/pre-file validation
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel

from app.api.deps import get_current_persona
from app.db.models import Persona
from app.security.rbac import authorize, Action

router = APIRouter(prefix="/qa", tags=["qa"])


# Request/Response models
class QACheckRequest(BaseModel):
    """Request to run QA checks on a document."""
    document_content: str
    document_id: str
    jurisdiction: str
    document_type: str  # offer, petition, deed, etc.
    context: Optional[dict[str, Any]] = None  # names, dates, amounts


class QAReportResponse(BaseModel):
    """QA report response."""
    id: str
    document_id: str
    document_hash: str
    jurisdiction: Optional[str]
    risk_level: str  # green, yellow, red
    passed: bool
    checks_performed: int
    checks_passed: int
    checks_failed: int
    checks_warned: int
    requires_counsel_review: bool
    escalation_reason: Optional[str]
    checked_at: str


class RiskScoreResponse(BaseModel):
    """Risk score response."""
    score: int
    risk_level: str
    qa_passed: bool
    requires_counsel_review: bool
    issues_summary: dict[str, int]


class QACheckDetail(BaseModel):
    """Detail of a single QA check."""
    check_type: str
    name: str
    passed: bool
    risk_level: str
    expected_value: Optional[str]
    actual_value: Optional[str]
    location: Optional[str]
    error_message: Optional[str]
    fix_suggestion: Optional[str]


@router.post("/check", response_model=QAReportResponse)
async def run_qa_checks(
    request: QACheckRequest,
    persona: Persona = Depends(get_current_persona),
):
    """Run all QA checks on a document.
    
    Returns a comprehensive report with pass/fail status
    and risk level (red/yellow/green).
    """
    authorize(persona, "qa", Action.EXECUTE)
    
    from app.services.qa_checks import QACheckService
    
    service = QACheckService()
    report = service.check_document(
        document_content=request.document_content,
        document_id=request.document_id,
        jurisdiction=request.jurisdiction,
        document_type=request.document_type,
        context=request.context,
    )
    
    return QAReportResponse(
        id=report.id,
        document_id=report.document_id,
        document_hash=report.document_hash,
        jurisdiction=report.jurisdiction,
        risk_level=report.risk_level,
        passed=report.passed,
        checks_performed=report.checks_performed,
        checks_passed=report.checks_passed,
        checks_failed=report.checks_failed,
        checks_warned=report.checks_warned,
        requires_counsel_review=report.requires_counsel_review,
        escalation_reason=report.escalation_reason,
        checked_at=report.checked_at.isoformat(),
    )


@router.get("/reports/{report_id}")
async def get_qa_report(
    report_id: str,
    persona: Persona = Depends(get_current_persona),
):
    """Get full details of a QA report.
    
    Includes all individual check results.
    """
    authorize(persona, "qa", Action.READ)
    
    from app.services.qa_checks import QACheckService
    
    service = QACheckService()
    report = service.get_report(report_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="QA report not found")
    
    return report.to_dict()


@router.get("/reports/{report_id}/checks", response_model=list[QACheckDetail])
async def get_qa_check_details(
    report_id: str,
    risk_level: Optional[str] = None,
    passed: Optional[bool] = None,
    persona: Persona = Depends(get_current_persona),
):
    """Get individual check results from a QA report.
    
    Can filter by risk level or pass/fail status.
    """
    authorize(persona, "qa", Action.READ)
    
    from app.services.qa_checks import QACheckService
    
    service = QACheckService()
    report = service.get_report(report_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="QA report not found")
    
    results = report.all_results
    
    if risk_level:
        results = [r for r in results if r.risk_level == risk_level]
    if passed is not None:
        results = [r for r in results if r.passed == passed]
    
    return [
        QACheckDetail(
            check_type=r.check_type,
            name=r.name,
            passed=r.passed,
            risk_level=r.risk_level,
            expected_value=r.expected_value,
            actual_value=r.actual_value,
            location=r.location,
            error_message=r.error_message,
            fix_suggestion=r.fix_suggestion,
        )
        for r in results
    ]


@router.get("/reports")
async def list_qa_reports(
    persona: Persona = Depends(get_current_persona),
    document_id: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = Query(50, le=200),
):
    """List QA reports with optional filters."""
    authorize(persona, "qa", Action.READ)
    
    from app.services.qa_checks import QACheckService
    
    service = QACheckService()
    reports = service.list_reports(
        document_id=document_id,
        risk_level=risk_level,
        limit=limit,
    )
    
    return {
        "count": len(reports),
        "reports": [
            QAReportResponse(
                id=r.id,
                document_id=r.document_id,
                document_hash=r.document_hash,
                jurisdiction=r.jurisdiction,
                risk_level=r.risk_level,
                passed=r.passed,
                checks_performed=r.checks_performed,
                checks_passed=r.checks_passed,
                checks_failed=r.checks_failed,
                checks_warned=r.checks_warned,
                requires_counsel_review=r.requires_counsel_review,
                escalation_reason=r.escalation_reason,
                checked_at=r.checked_at.isoformat(),
            )
            for r in reports
        ],
    }


@router.post("/risk-score", response_model=RiskScoreResponse)
async def calculate_risk_score(
    qa_report_id: str,
    citation_check: Optional[dict[str, Any]] = None,
    persona: Persona = Depends(get_current_persona),
):
    """Calculate overall risk score for a document.
    
    Combines QA report with citation verification.
    """
    authorize(persona, "qa", Action.READ)
    
    from app.services.qa_checks import QACheckService, calculate_risk_score
    
    service = QACheckService()
    report = service.get_report(qa_report_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="QA report not found")
    
    result = calculate_risk_score(report, citation_check)
    
    return RiskScoreResponse(**result)


@router.post("/validate-for-send")
async def validate_for_send(
    document_id: str,
    document_content: str,
    jurisdiction: str,
    document_type: str,
    context: Optional[dict[str, Any]] = None,
    persona: Persona = Depends(get_current_persona),
):
    """Validate a document before sending.
    
    Comprehensive check that must pass before
    any document is sent to landowner.
    """
    authorize(persona, "qa", Action.EXECUTE)
    
    from app.services.qa_checks import QACheckService, calculate_risk_score
    from app.services.citations import CitationService, ClaimChecker
    
    # Run QA checks
    qa_service = QACheckService()
    qa_report = qa_service.check_document(
        document_content=document_content,
        document_id=document_id,
        jurisdiction=jurisdiction,
        document_type=document_type,
        context=context,
    )
    
    # Calculate risk score
    risk = calculate_risk_score(qa_report, None)
    
    # Determine if sendable
    can_send = qa_report.passed and risk["risk_level"] != "red"
    
    return {
        "can_send": can_send,
        "qa_report_id": qa_report.id,
        "risk_level": risk["risk_level"],
        "risk_score": risk["score"],
        "requires_counsel_review": risk["requires_counsel_review"],
        "blocking_issues": [
            i.to_dict() for i in qa_report.critical_issues
        ],
        "warnings": [
            w.to_dict() for w in qa_report.warnings
        ],
        "missing_clauses": qa_report.required_clauses_missing,
    }


@router.get("/required-clauses/{jurisdiction}")
async def get_required_clauses(
    jurisdiction: str,
    document_type: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
):
    """Get required clauses for a jurisdiction.
    
    Lists all clauses that must be present in documents
    for the specified state.
    """
    authorize(persona, "qa", Action.READ)
    
    from app.services.qa_checks import STATE_REQUIRED_CLAUSES
    
    clauses = STATE_REQUIRED_CLAUSES.get(jurisdiction.upper(), [])
    
    return {
        "jurisdiction": jurisdiction.upper(),
        "clauses_count": len(clauses),
        "clauses": clauses,
    }
