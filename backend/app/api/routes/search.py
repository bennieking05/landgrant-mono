"""Global search for staff workbench (UX-2): parcels, parties, cases, documents."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_principal, get_db
from app.db import models
from app.db.models import Persona
from app.security.access_scope import filter_parcels_query, granted_parcel_ids
from app.security.jwt_auth import JWTPrincipal
from app.security.rbac import Action, authorize

router = APIRouter(prefix="/search", tags=["search"])


class SearchResult(BaseModel):
    result_type: str
    id: str
    title: str
    subtitle: Optional[str] = None
    project_id: Optional[str] = None
    parcel_id: Optional[str] = None


def _parcel_base_query(db: Session, principal: JWTPrincipal):
    q = db.query(models.Parcel)
    return filter_parcels_query(db, principal, q)


def _firm_project_filter(db: Session, principal: JWTPrincipal):
    if not principal.firm_id:
        return None
    return (
        db.query(models.Project.id)
        .filter(models.Project.firm_id == principal.firm_id)
        .subquery()
    )


@router.get("")
def staff_global_search(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, le=50),
    persona: Persona = Depends(get_current_persona),
    principal: JWTPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Keyword search across parcels, litigation cases, parties, and documents (scoped)."""
    authorize(persona, "parcel", Action.READ)

    if persona == Persona.LANDOWNER:
        return {"query": q, "results": [], "count": 0}

    like = f"%{q.strip()}%"
    results: list[SearchResult] = []
    per_bucket = max(4, min(limit // 4, 16))
    firm_projects = _firm_project_filter(db, principal)

    # --- Parcels ---
    pq = _parcel_base_query(db, principal)
    if firm_projects is not None:
        pq = pq.filter(models.Parcel.project_id.in_(firm_projects))
    owner_parcel_ids = (
        db.query(models.ParcelParty.parcel_id)
        .join(models.Party, models.Party.id == models.ParcelParty.party_id)
        .filter(models.Party.name.ilike(like))
    )
    parcels = (
        pq.filter(
            or_(
                models.Parcel.id.ilike(like),
                models.Parcel.county_fips.ilike(like),
                models.Parcel.parcel_number.ilike(like),
                models.Parcel.id.in_(owner_parcel_ids),
            )
        )
        .limit(per_bucket)
        .all()
    )
    for parcel in parcels:
        project = (
            db.query(models.Project)
            .filter(models.Project.id == parcel.project_id)
            .first()
        )
        results.append(
            SearchResult(
                result_type="parcel",
                id=parcel.id,
                title=f"Parcel {parcel.id}",
                subtitle=f"Project: {project.name if project else parcel.project_id}",
                project_id=parcel.project_id,
                parcel_id=parcel.id,
            )
        )

    # --- Litigation (cause / court) ---
    lit_q = db.query(models.LitigationCase)
    if firm_projects is not None:
        lit_q = lit_q.filter(models.LitigationCase.project_id.in_(firm_projects))
    allowed = granted_parcel_ids(db, principal)
    if allowed is not None:
        if not allowed:
            lit_q = lit_q.filter(False)
        else:
            lit_q = lit_q.filter(
                or_(
                    models.LitigationCase.parcel_id.is_(None),
                    models.LitigationCase.parcel_id.in_(list(allowed)),
                )
            )
    lit_cases = (
        lit_q.filter(
            or_(
                models.LitigationCase.cause_number.ilike(like),
                models.LitigationCase.court.ilike(like),
                models.LitigationCase.case_number.ilike(like),
            )
        )
        .limit(per_bucket)
        .all()
    )
    for case in lit_cases:
        results.append(
            SearchResult(
                result_type="case",
                id=case.id,
                title=f"Case {case.cause_number or case.id}",
                subtitle=f"Court: {case.court}",
                project_id=case.project_id,
                parcel_id=case.parcel_id,
            )
        )

    # --- Parties (distinct IDs only — Party has JSON columns unsafe for SELECT DISTINCT *) ---
    party_id_q = (
        db.query(models.Party.id)
        .join(models.ParcelParty, models.ParcelParty.party_id == models.Party.id)
        .join(models.Parcel, models.Parcel.id == models.ParcelParty.parcel_id)
    )
    party_id_q = filter_parcels_query(db, principal, party_id_q)
    if firm_projects is not None:
        party_id_q = party_id_q.filter(models.Parcel.project_id.in_(firm_projects))
    party_ids = [
        row[0]
        for row in (
            party_id_q.filter(
                or_(
                    models.Party.name.ilike(like),
                    models.Party.email.ilike(like),
                )
            )
            .distinct()
            .limit(per_bucket)
            .all()
        )
    ]
    for party_id in party_ids:
        party = db.query(models.Party).filter(models.Party.id == party_id).first()
        if not party:
            continue
        parcel_party = (
            db.query(models.ParcelParty)
            .filter(models.ParcelParty.party_id == party.id)
            .first()
        )
        results.append(
            SearchResult(
                result_type="party",
                id=party.id,
                title=party.name,
                subtitle=f"Role: {party.role}",
                project_id=None,
                parcel_id=parcel_party.parcel_id if parcel_party else None,
            )
        )

    # --- Documents (name / file / type) ---
    doc_q = db.query(models.Document)
    if principal.firm_id:
        doc_q = doc_q.filter(models.Document.firm_id == principal.firm_id)
    if allowed is not None:
        if not allowed:
            doc_q = doc_q.filter(False)
        else:
            doc_q = doc_q.filter(
                or_(
                    models.Document.parcel_id.is_(None),
                    models.Document.parcel_id.in_(list(allowed)),
                )
            )
    elif firm_projects is not None:
        doc_q = doc_q.filter(
            or_(
                models.Document.project_id.is_(None),
                models.Document.project_id.in_(firm_projects),
            )
        )
    docs = (
        doc_q.filter(
            or_(
                models.Document.document_name.ilike(like),
                models.Document.file_name.ilike(like),
                models.Document.doc_type.ilike(like),
                models.Document.id.ilike(like),
            )
        )
        .limit(per_bucket)
        .all()
    )
    for doc in docs:
        label = doc.document_name or doc.file_name or doc.doc_type or doc.id
        results.append(
            SearchResult(
                result_type="document",
                id=doc.id,
                title=label,
                subtitle=doc.doc_type,
                project_id=doc.project_id,
                parcel_id=doc.parcel_id,
            )
        )

    # Trim to limit while preserving diversity (simple slice).
    trimmed = results[:limit]
    return {
        "query": q,
        "results": [r.model_dump() for r in trimmed],
        "count": len(trimmed),
    }
