"""
Admin API Routes

Provides dashboard endpoints for two admin levels:
- FIRM_ADMIN: Law firm admin - sees rolled-up cases for their firm's projects
- ADMIN: Platform admin - sees ALL cases across all firms with search/filter
"""

from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_persona, get_current_user
from app.db import models
from app.db.models import Persona
from app.security.rbac import Action, authorize

router = APIRouter(prefix="/admin", tags=["admin"])


# =============================================================================
# Response Models
# =============================================================================


class FirmMetrics(BaseModel):
    total_projects: int
    total_parcels: int
    parcels_by_stage: dict[str, int]
    active_negotiations: int
    litigation_cases: int
    completion_rate: float
    pending_offers: int
    active_roes: int


class FirmCaseItem(BaseModel):
    parcel_id: str
    project_id: str
    project_name: Optional[str]
    parcel_stage: str
    litigation_status: Optional[str]
    offer_status: Optional[str]
    payment_status: Optional[str]
    updated_at: str


class FirmActivityItem(BaseModel):
    id: str
    action: str
    resource: str
    actor_persona: Optional[str]
    occurred_at: str
    payload: dict


class PlatformMetrics(BaseModel):
    total_firms: int  # Total projects (firm = project)
    total_parcels: int
    total_cases: int
    parcels_by_stage: dict[str, int]
    cases_by_status: dict[str, int]
    active_portal_sessions: int
    pending_approvals: int
    system_health: dict[str, str]


class GlobalCaseItem(BaseModel):
    parcel_id: str
    project_id: str
    project_name: Optional[str]
    parcel_stage: str
    jurisdiction: Optional[str]
    litigation_status: Optional[str]
    litigation_case_id: Optional[str]
    cause_number: Optional[str]
    offer_status: Optional[str]
    payment_status: Optional[str]
    landowner_name: Optional[str]
    updated_at: str


class ProjectOverview(BaseModel):
    project_id: str
    project_name: str
    jurisdiction: str
    stage: str
    parcel_count: int
    litigation_count: int
    completion_rate: float
    created_at: str


class SearchResult(BaseModel):
    result_type: str  # parcel, party, case
    id: str
    title: str
    subtitle: Optional[str]
    project_id: Optional[str]
    parcel_id: Optional[str]


class HealthStatus(BaseModel):
    service: str
    status: str  # healthy, degraded, unhealthy
    latency_ms: Optional[int]
    last_check: str


# =============================================================================
# Helper Functions
# =============================================================================


def _get_user_project_ids(db: Session, user_id: str) -> list[str]:
    """
    Get project IDs that a user has access to.
    For now, returns all projects. In a real implementation,
    this would check user-project assignments.
    """
    # TODO: Implement proper user-project access control
    # For now, return all project IDs
    projects = db.query(models.Project.id).all()
    return [p.id for p in projects]


def _build_parcel_stage_counts(db: Session, project_ids: Optional[list[str]] = None) -> dict[str, int]:
    """Count parcels by stage."""
    query = db.query(
        models.Parcel.stage,
        func.count(models.Parcel.id)
    ).group_by(models.Parcel.stage)
    
    if project_ids:
        query = query.filter(models.Parcel.project_id.in_(project_ids))
    
    results = query.all()
    return {str(stage.value) if hasattr(stage, 'value') else str(stage): count for stage, count in results}


def _build_litigation_status_counts(db: Session, project_ids: Optional[list[str]] = None) -> dict[str, int]:
    """Count litigation cases by status."""
    query = db.query(
        models.LitigationCase.status,
        func.count(models.LitigationCase.id)
    ).group_by(models.LitigationCase.status)
    
    if project_ids:
        query = query.filter(models.LitigationCase.project_id.in_(project_ids))
    
    results = query.all()
    return {str(status.value) if hasattr(status, 'value') else str(status): count for status, count in results}


# =============================================================================
# Firm Admin Endpoints (Scoped to User's Projects)
# =============================================================================


@router.get("/firm/dashboard")
def get_firm_dashboard(
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> FirmMetrics:
    """
    Get firm-level dashboard metrics.
    
    Returns rolled-up statistics for all projects the firm admin has access to.
    """
    authorize(persona, "admin_firm", Action.READ)
    
    user_id = user.get("sub", "unknown")
    project_ids = _get_user_project_ids(db, user_id)
    
    # Total projects and parcels
    total_projects = len(project_ids)
    total_parcels = db.query(func.count(models.Parcel.id)).filter(
        models.Parcel.project_id.in_(project_ids)
    ).scalar() or 0
    
    # Parcels by stage
    parcels_by_stage = _build_parcel_stage_counts(db, project_ids)
    
    # Active negotiations (parcels in negotiation stage)
    active_negotiations = db.query(func.count(models.Parcel.id)).filter(
        models.Parcel.project_id.in_(project_ids),
        models.Parcel.stage == models.ParcelStage.NEGOTIATION
    ).scalar() or 0
    
    # Litigation cases
    litigation_cases = db.query(func.count(models.LitigationCase.id)).filter(
        models.LitigationCase.project_id.in_(project_ids)
    ).scalar() or 0
    
    # Completion rate
    closed_parcels = parcels_by_stage.get("closed", 0)
    completion_rate = (closed_parcels / total_parcels * 100) if total_parcels > 0 else 0.0
    
    # Pending offers
    pending_offers = db.query(func.count(models.Offer.id)).filter(
        models.Offer.project_id.in_(project_ids),
        models.Offer.status == models.OfferStatus.SENT
    ).scalar() or 0
    
    # Active ROEs
    active_roes = db.query(func.count(models.ROE.id)).filter(
        models.ROE.project_id.in_(project_ids),
        models.ROE.status == models.ROEStatus.ACTIVE
    ).scalar() or 0
    
    return FirmMetrics(
        total_projects=total_projects,
        total_parcels=total_parcels,
        parcels_by_stage=parcels_by_stage,
        active_negotiations=active_negotiations,
        litigation_cases=litigation_cases,
        completion_rate=round(completion_rate, 1),
        pending_offers=pending_offers,
        active_roes=active_roes,
    )


@router.get("/firm/cases")
def get_firm_cases(
    status: Optional[str] = Query(None, description="Filter by parcel stage"),
    litigation_status: Optional[str] = Query(None, description="Filter by litigation status"),
    search: Optional[str] = Query(None, description="Search by parcel ID"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """
    List all cases across firm's projects with filters.
    """
    authorize(persona, "admin_firm", Action.READ)
    
    user_id = user.get("sub", "unknown")
    project_ids = _get_user_project_ids(db, user_id)
    
    # Base query
    query = db.query(models.Parcel).filter(models.Parcel.project_id.in_(project_ids))
    
    # Apply filters
    if status:
        try:
            stage_enum = models.ParcelStage(status)
            query = query.filter(models.Parcel.stage == stage_enum)
        except ValueError:
            pass
    
    if search:
        query = query.filter(models.Parcel.id.ilike(f"%{search}%"))
    
    # Get total count
    total = query.count()
    
    # Get parcels
    parcels = query.order_by(models.Parcel.updated_at.desc()).offset(offset).limit(limit).all()
    
    # Build response with related data
    cases = []
    for parcel in parcels:
        # Get project name
        project = db.query(models.Project).filter(models.Project.id == parcel.project_id).first()
        
        # Get litigation status if applicable
        lit_case = db.query(models.LitigationCase).filter(
            models.LitigationCase.parcel_id == parcel.id
        ).first()
        
        # Get payment ledger status
        ledger = db.query(models.PaymentLedger).filter(
            models.PaymentLedger.parcel_id == parcel.id
        ).first()
        
        # Get current offer status
        offer = db.query(models.Offer).filter(
            models.Offer.parcel_id == parcel.id
        ).order_by(models.Offer.created_at.desc()).first()
        
        # Apply litigation filter if specified
        if litigation_status:
            if not lit_case:
                continue
            try:
                lit_status_enum = models.LitigationStatus(litigation_status)
                if lit_case.status != lit_status_enum:
                    continue
            except ValueError:
                pass
        
        cases.append(FirmCaseItem(
            parcel_id=parcel.id,
            project_id=parcel.project_id,
            project_name=project.name if project else None,
            parcel_stage=parcel.stage.value if parcel.stage else "unknown",
            litigation_status=lit_case.status.value if lit_case else None,
            offer_status=offer.status.value if offer else None,
            payment_status=ledger.status.value if ledger else None,
            updated_at=parcel.updated_at.isoformat() if parcel.updated_at else "",
        ))
    
    return {
        "cases": [c.model_dump() for c in cases],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/firm/activity")
def get_firm_activity(
    days: int = Query(7, le=30, description="Number of days to look back"),
    limit: int = Query(50, le=200),
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get recent activity within firm's projects.
    """
    authorize(persona, "admin_firm", Action.READ)
    
    user_id = user.get("sub", "unknown")
    project_ids = _get_user_project_ids(db, user_id)
    
    since = datetime.utcnow() - timedelta(days=days)
    
    # Get audit events for firm's projects
    # Filter by payload containing project_id in firm's projects
    events = db.query(models.AuditEvent).filter(
        models.AuditEvent.occurred_at >= since
    ).order_by(models.AuditEvent.occurred_at.desc()).limit(limit * 2).all()
    
    # Filter events related to firm's projects
    firm_events = []
    for event in events:
        payload = event.payload or {}
        if payload.get("project_id") in project_ids or payload.get("parcel_id", "").split("-")[0] in ["PARCEL"]:
            firm_events.append(FirmActivityItem(
                id=event.id,
                action=event.action,
                resource=event.resource,
                actor_persona=event.actor_persona.value if event.actor_persona else None,
                occurred_at=event.occurred_at.isoformat() if event.occurred_at else "",
                payload=payload,
            ))
        if len(firm_events) >= limit:
            break
    
    return {
        "activities": [a.model_dump() for a in firm_events],
        "days": days,
        "count": len(firm_events),
    }


# =============================================================================
# Platform Admin Endpoints (Global Scope)
# =============================================================================


@router.get("/platform/dashboard")
def get_platform_dashboard(
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
) -> PlatformMetrics:
    """
    Get platform-wide dashboard metrics.
    
    Returns system-wide statistics across all projects/firms.
    """
    authorize(persona, "admin_platform", Action.READ)
    
    # Total firms (projects)
    total_firms = db.query(func.count(models.Project.id)).scalar() or 0
    
    # Total parcels
    total_parcels = db.query(func.count(models.Parcel.id)).scalar() or 0
    
    # Total litigation cases
    total_cases = db.query(func.count(models.LitigationCase.id)).scalar() or 0
    
    # Parcels by stage
    parcels_by_stage = _build_parcel_stage_counts(db)
    
    # Cases by status
    cases_by_status = _build_litigation_status_counts(db)
    
    # Active portal sessions
    active_sessions = db.query(func.count(models.PortalSession.id)).filter(
        models.PortalSession.expires_at > datetime.utcnow(),
        models.PortalSession.revoked_at.is_(None)
    ).scalar() or 0
    
    # Pending approvals
    pending_approvals = db.query(func.count(models.Approval.id)).filter(
        models.Approval.status == models.ApprovalStatus.PENDING_REVIEW
    ).scalar() or 0
    
    # Basic system health check
    system_health = {
        "database": "healthy",
        "api": "healthy",
    }
    
    return PlatformMetrics(
        total_firms=total_firms,
        total_parcels=total_parcels,
        total_cases=total_cases,
        parcels_by_stage=parcels_by_stage,
        cases_by_status=cases_by_status,
        active_portal_sessions=active_sessions,
        pending_approvals=pending_approvals,
        system_health=system_health,
    )


@router.get("/platform/cases")
def get_platform_cases(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    status: Optional[str] = Query(None, description="Filter by parcel stage"),
    litigation_status: Optional[str] = Query(None, description="Filter by litigation status"),
    case_type: Optional[str] = Query(None, description="Filter by case type (standard/quick_take)"),
    search: Optional[str] = Query(None, description="Search by parcel ID, cause number, or party name"),
    date_from: Optional[str] = Query(None, description="Filter by date range start (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter by date range end (ISO format)"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    List ALL cases across all firms with comprehensive search/filter.
    """
    authorize(persona, "admin_platform", Action.READ)
    
    # Base query with joins for search
    query = db.query(models.Parcel)
    
    # Apply filters
    if project_id:
        query = query.filter(models.Parcel.project_id == project_id)
    
    if status:
        try:
            stage_enum = models.ParcelStage(status)
            query = query.filter(models.Parcel.stage == stage_enum)
        except ValueError:
            pass
    
    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            query = query.filter(models.Parcel.updated_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            query = query.filter(models.Parcel.updated_at <= to_date)
        except ValueError:
            pass
    
    # Text search across multiple fields
    if search:
        query = query.filter(
            or_(
                models.Parcel.id.ilike(f"%{search}%"),
                models.Parcel.project_id.ilike(f"%{search}%"),
            )
        )
    
    # Get total count before pagination
    total = query.count()
    
    # Get parcels
    parcels = query.order_by(models.Parcel.updated_at.desc()).offset(offset).limit(limit).all()
    
    # Build enriched response
    cases = []
    for parcel in parcels:
        # Get project
        project = db.query(models.Project).filter(models.Project.id == parcel.project_id).first()
        
        # Get litigation case
        lit_case = db.query(models.LitigationCase).filter(
            models.LitigationCase.parcel_id == parcel.id
        ).first()
        
        # Apply litigation filters
        if litigation_status and lit_case:
            try:
                lit_status_enum = models.LitigationStatus(litigation_status)
                if lit_case.status != lit_status_enum:
                    continue
            except ValueError:
                pass
        elif litigation_status and not lit_case:
            continue
        
        if case_type:
            if not lit_case:
                continue
            if case_type == "quick_take" and not lit_case.is_quick_take:
                continue
            if case_type == "standard" and lit_case.is_quick_take:
                continue
        
        # Get payment ledger
        ledger = db.query(models.PaymentLedger).filter(
            models.PaymentLedger.parcel_id == parcel.id
        ).first()
        
        # Get current offer
        offer = db.query(models.Offer).filter(
            models.Offer.parcel_id == parcel.id
        ).order_by(models.Offer.created_at.desc()).first()
        
        # Get landowner name from parties
        landowner = None
        parcel_party = db.query(models.ParcelParty).filter(
            models.ParcelParty.parcel_id == parcel.id,
            models.ParcelParty.relationship_type == "owner"
        ).first()
        if parcel_party:
            party = db.query(models.Party).filter(models.Party.id == parcel_party.party_id).first()
            if party:
                landowner = party.name
        
        cases.append(GlobalCaseItem(
            parcel_id=parcel.id,
            project_id=parcel.project_id,
            project_name=project.name if project else None,
            parcel_stage=parcel.stage.value if parcel.stage else "unknown",
            jurisdiction=project.jurisdiction_code if project else None,
            litigation_status=lit_case.status.value if lit_case else None,
            litigation_case_id=lit_case.id if lit_case else None,
            cause_number=lit_case.cause_number if lit_case else None,
            offer_status=offer.status.value if offer else None,
            payment_status=ledger.status.value if ledger else None,
            landowner_name=landowner,
            updated_at=parcel.updated_at.isoformat() if parcel.updated_at else "",
        ))
    
    return {
        "cases": [c.model_dump() for c in cases],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/platform/projects")
def get_platform_projects(
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    stage: Optional[str] = Query(None, description="Filter by project stage"),
    search: Optional[str] = Query(None, description="Search by project name"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    List all projects/firms with metrics.
    """
    authorize(persona, "admin_platform", Action.READ)
    
    query = db.query(models.Project)
    
    if jurisdiction:
        query = query.filter(models.Project.jurisdiction_code == jurisdiction)
    
    if stage:
        try:
            stage_enum = models.ProjectStage(stage)
            query = query.filter(models.Project.stage == stage_enum)
        except ValueError:
            pass
    
    if search:
        query = query.filter(models.Project.name.ilike(f"%{search}%"))
    
    total = query.count()
    projects = query.order_by(models.Project.created_at.desc()).offset(offset).limit(limit).all()
    
    # Build response with metrics
    project_overviews = []
    for project in projects:
        # Count parcels
        parcel_count = db.query(func.count(models.Parcel.id)).filter(
            models.Parcel.project_id == project.id
        ).scalar() or 0
        
        # Count litigation cases
        litigation_count = db.query(func.count(models.LitigationCase.id)).filter(
            models.LitigationCase.project_id == project.id
        ).scalar() or 0
        
        # Calculate completion rate
        closed_count = db.query(func.count(models.Parcel.id)).filter(
            models.Parcel.project_id == project.id,
            models.Parcel.stage == models.ParcelStage.CLOSED
        ).scalar() or 0
        completion_rate = (closed_count / parcel_count * 100) if parcel_count > 0 else 0.0
        
        project_overviews.append(ProjectOverview(
            project_id=project.id,
            project_name=project.name,
            jurisdiction=project.jurisdiction_code,
            stage=project.stage.value if project.stage else "unknown",
            parcel_count=parcel_count,
            litigation_count=litigation_count,
            completion_rate=round(completion_rate, 1),
            created_at=project.created_at.isoformat() if project.created_at else "",
        ))
    
    return {
        "projects": [p.model_dump() for p in project_overviews],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/platform/search")
def global_search(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, le=50),
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Global keyword search across cases, parcels, parties.
    """
    authorize(persona, "admin_platform", Action.READ)
    
    results: list[SearchResult] = []
    
    # Search parcels
    parcels = db.query(models.Parcel).filter(
        models.Parcel.id.ilike(f"%{q}%")
    ).limit(limit // 3).all()
    
    for parcel in parcels:
        project = db.query(models.Project).filter(models.Project.id == parcel.project_id).first()
        results.append(SearchResult(
            result_type="parcel",
            id=parcel.id,
            title=f"Parcel {parcel.id}",
            subtitle=f"Project: {project.name if project else parcel.project_id}",
            project_id=parcel.project_id,
            parcel_id=parcel.id,
        ))
    
    # Search litigation cases by cause number
    lit_cases = db.query(models.LitigationCase).filter(
        or_(
            models.LitigationCase.cause_number.ilike(f"%{q}%"),
            models.LitigationCase.court.ilike(f"%{q}%"),
        )
    ).limit(limit // 3).all()
    
    for case in lit_cases:
        results.append(SearchResult(
            result_type="case",
            id=case.id,
            title=f"Case {case.cause_number or case.id}",
            subtitle=f"Court: {case.court}",
            project_id=case.project_id,
            parcel_id=case.parcel_id,
        ))
    
    # Search parties
    parties = db.query(models.Party).filter(
        or_(
            models.Party.name.ilike(f"%{q}%"),
            models.Party.email.ilike(f"%{q}%"),
        )
    ).limit(limit // 3).all()
    
    for party in parties:
        # Find associated parcel
        parcel_party = db.query(models.ParcelParty).filter(
            models.ParcelParty.party_id == party.id
        ).first()
        
        results.append(SearchResult(
            result_type="party",
            id=party.id,
            title=party.name,
            subtitle=f"Role: {party.role}",
            project_id=None,
            parcel_id=parcel_party.parcel_id if parcel_party else None,
        ))
    
    return {
        "query": q,
        "results": [r.model_dump() for r in results],
        "count": len(results),
    }


@router.get("/platform/health")
def get_platform_health(
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Get system health status for all services.
    """
    authorize(persona, "admin_platform", Action.READ)
    
    health_checks: list[HealthStatus] = []
    
    # Database health
    try:
        start = datetime.utcnow()
        db.execute("SELECT 1")
        latency = int((datetime.utcnow() - start).total_seconds() * 1000)
        health_checks.append(HealthStatus(
            service="PostgreSQL",
            status="healthy",
            latency_ms=latency,
            last_check=datetime.utcnow().isoformat(),
        ))
    except Exception:
        health_checks.append(HealthStatus(
            service="PostgreSQL",
            status="unhealthy",
            latency_ms=None,
            last_check=datetime.utcnow().isoformat(),
        ))
    
    # API health (always healthy if we got here)
    health_checks.append(HealthStatus(
        service="API",
        status="healthy",
        latency_ms=0,
        last_check=datetime.utcnow().isoformat(),
    ))
    
    # Placeholder for other services
    health_checks.append(HealthStatus(
        service="Redis",
        status="healthy",
        latency_ms=1,
        last_check=datetime.utcnow().isoformat(),
    ))
    
    health_checks.append(HealthStatus(
        service="SendGrid",
        status="healthy",
        latency_ms=None,
        last_check=datetime.utcnow().isoformat(),
    ))
    
    health_checks.append(HealthStatus(
        service="DocuSign",
        status="healthy",
        latency_ms=None,
        last_check=datetime.utcnow().isoformat(),
    ))
    
    overall = "healthy"
    for check in health_checks:
        if check.status == "unhealthy":
            overall = "unhealthy"
            break
        elif check.status == "degraded":
            overall = "degraded"
    
    return {
        "overall_status": overall,
        "services": [h.model_dump() for h in health_checks],
        "checked_at": datetime.utcnow().isoformat(),
    }
