"""Persona-aware dashboard KPIs with honest empty / insufficient-sample semantics (UX-3)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_principal, get_db
from app.db import models
from app.db.models import ApprovalStatus, OfferStatus, ParcelStage, Persona
from app.security.access_scope import filter_parcels_query
from app.security.jwt_auth import JWTPrincipal
from app.security.rbac import Action, authorize

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

MIN_SAMPLE_NARRATIVE = 5


def _firm_project_filter(principal: JWTPrincipal):
    if not principal.firm_id:
        return None
    return select(models.Project.id).where(models.Project.firm_id == principal.firm_id)


def _scoped_parcels(
    db: Session, principal: JWTPrincipal, project_id: Optional[str] = None
):
    q = filter_parcels_query(db, principal, db.query(models.Parcel))
    fp = _firm_project_filter(principal)
    if fp is not None:
        q = q.filter(models.Parcel.project_id.in_(fp))
    if project_id:
        q = q.filter(models.Parcel.project_id == project_id)
    return q


@router.get("/home")
def dashboard_home(
    project_id: Optional[str] = Query(
        None, description="Scope KPIs to a single project"
    ),
    persona: Persona = Depends(get_current_persona),
    principal: JWTPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Aggregated KPIs for the signed-in persona; never fabricates rates from thin air."""
    authorize(persona, "parcel", Action.READ)

    empty = {
        "persona": persona.value,
        "project_id": project_id,
        "sample_size": 0,
        "sample_sufficient": False,
        "parcels_by_stage": {},
        "pending_offers_count": 0,
        "overdue_tasks_count": 0,
        "deadlines_next_14_count": 0,
        "pending_approvals_count": None,
        "escalations_open_count": None,
        "litigation_rate": None,
        "litigation_rate_insufficient_data": True,
        "cycle_time_median_days": None,
        "cycle_time_insufficient_data": True,
        "budget_utilization_pct": None,
        "budget_utilization_insufficient_data": True,
    }

    if persona == Persona.LANDOWNER:
        return empty

    pq = _scoped_parcels(db, principal, project_id)
    total = pq.count()
    sample_sufficient = total >= MIN_SAMPLE_NARRATIVE

    by_stage: dict[str, int] = {}
    if total > 0:
        rows = (
            pq.with_entities(models.Parcel.stage, func.count(models.Parcel.id))
            .group_by(models.Parcel.stage)
            .all()
        )
        for st, cnt in rows:
            key = st.value if hasattr(st, "value") else str(st)
            by_stage[key] = int(cnt)

    if total == 0:
        out = {**empty}
        out["persona"] = persona.value
        out["project_id"] = project_id
        return out

    parcel_ids_subq = pq.with_entities(models.Parcel.id).subquery()

    pending_offers = (
        db.query(func.count(models.Offer.id))
        .filter(models.Offer.parcel_id.in_(select(parcel_ids_subq.c.id)))
        .filter(models.Offer.status == OfferStatus.SENT)
        .scalar()
        or 0
    )

    now = datetime.utcnow()
    horizon = now + timedelta(days=14)
    deadlines_14 = (
        db.query(func.count(models.Parcel.id))
        .filter(models.Parcel.id.in_(select(parcel_ids_subq.c.id)))
        .filter(models.Parcel.next_deadline_at.isnot(None))
        .filter(models.Parcel.next_deadline_at <= horizon)
        .filter(models.Parcel.next_deadline_at >= now)
        .scalar()
        or 0
    )

    overdue_tasks = (
        db.query(func.count(models.Task.id))
        .filter(models.Task.parcel_id.in_(select(parcel_ids_subq.c.id)))
        .filter(models.Task.status.in_(["open", "in_progress"]))
        .filter(models.Task.due_at.isnot(None))
        .filter(models.Task.due_at < now)
        .scalar()
        or 0
    )

    lit_count = int(by_stage.get(ParcelStage.LITIGATION.value, 0))
    litigation_rate: Optional[float] = None
    lit_insufficient = True
    if total >= MIN_SAMPLE_NARRATIVE:
        litigation_rate = round(lit_count / total, 4)
        lit_insufficient = False

    pending_approvals: Optional[int] = None
    if persona in (
        Persona.IN_HOUSE_COUNSEL,
        Persona.OUTSIDE_COUNSEL,
        Persona.PLATFORM_ADMIN,
    ):
        try:
            authorize(persona, "approvals", Action.READ)
            aq = db.query(func.count(models.Approval.id)).filter(
                models.Approval.status == ApprovalStatus.PENDING_REVIEW
            )
            fp = _firm_project_filter(principal)
            if fp is not None:
                aq = aq.filter(models.Approval.project_id.in_(fp))
            pending_approvals = int(aq.scalar() or 0)
        except Exception:
            pending_approvals = None

    escalations_open: Optional[int] = None
    if persona in (Persona.IN_HOUSE_COUNSEL, Persona.PLATFORM_ADMIN):
        try:
            authorize(persona, "ai_agent", Action.READ)
            escalations_open = int(
                db.query(func.count(models.EscalationRequest.id))
                .filter(models.EscalationRequest.status.in_(["open", "in_review"]))
                .scalar()
                or 0
            )
        except Exception:
            escalations_open = None

    return {
        "persona": persona.value,
        "project_id": project_id,
        "sample_size": total,
        "sample_sufficient": sample_sufficient,
        "parcels_by_stage": by_stage,
        "pending_offers_count": int(pending_offers),
        "overdue_tasks_count": int(overdue_tasks),
        "deadlines_next_14_count": int(deadlines_14),
        "pending_approvals_count": pending_approvals,
        "escalations_open_count": escalations_open,
        "litigation_rate": litigation_rate,
        "litigation_rate_insufficient_data": lit_insufficient,
        "cycle_time_median_days": None,
        "cycle_time_insufficient_data": True,
        "budget_utilization_pct": None,
        "budget_utilization_insufficient_data": True,
    }
