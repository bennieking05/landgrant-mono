from __future__ import annotations
from typing import Optional

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_principal, get_db
from app.db import models
from app.db.models import Persona, ParcelStage
from app.security.access_scope import filter_parcels_query
from app.security.jwt_auth import JWTPrincipal
from app.security.rbac import Action, authorize


router = APIRouter(prefix="/parcels", tags=["parcels"])


# Columns the enterprise grid (UX-4) may sort by. Keep this allowlist tight.
SORT_COLUMNS = {
    "id": models.Parcel.id,
    "stage": models.Parcel.stage,
    "risk_score": models.Parcel.risk_score,
    "next_deadline_at": models.Parcel.next_deadline_at,
    "updated_at": models.Parcel.updated_at,
    "county_fips": models.Parcel.county_fips,
}


@router.get("")
def list_parcels(
    project_id: Optional[str] = None,
    stage: Optional[str] = None,
    min_risk: Optional[int] = None,
    deadline_before: Optional[str] = None,
    q: Optional[str] = None,
    sort: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    persona: Persona = Depends(get_current_persona),
    principal: JWTPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    authorize(persona, "parcel", Action.READ)
    query = db.query(models.Parcel)
    query = filter_parcels_query(db, principal, query)
    if project_id:
        query = query.filter(models.Parcel.project_id == project_id)
    if stage:
        try:
            stage_enum = ParcelStage(stage)
            query = query.filter(models.Parcel.stage == stage_enum)
        except ValueError:
            # Invalid stage value, filter will return no results
            query = query.filter(False)
    if min_risk is not None:
        query = query.filter(models.Parcel.risk_score >= min_risk)
    if deadline_before:
        try:
            dt = datetime.fromisoformat(deadline_before.replace("Z", ""))
            query = query.filter(models.Parcel.next_deadline_at.isnot(None)).filter(
                models.Parcel.next_deadline_at <= dt
            )
        except Exception:
            pass

    # Free-text search by parcel id, county FIPS, or owner (party) name (UX-2 Cmd-K, UX-4 grid).
    if q and q.strip():
        like = f"%{q.strip()}%"
        owner_parcel_ids = (
            db.query(models.ParcelParty.parcel_id)
            .join(models.Party, models.Party.id == models.ParcelParty.party_id)
            .filter(models.Party.name.ilike(like))
        )
        query = query.filter(
            or_(
                models.Parcel.id.ilike(like),
                models.Parcel.county_fips.ilike(like),
                models.Parcel.id.in_(owner_parcel_ids),
            )
        )

    total = query.count()

    # Sorting: "field" (asc) or "-field" (desc); default to most-recently updated.
    order_clause = models.Parcel.updated_at.desc()
    if sort:
        key = sort[1:] if sort.startswith("-") else sort
        col = SORT_COLUMNS.get(key)
        if col is not None:
            order_clause = col.desc() if sort.startswith("-") else col.asc()

    items = (
        query.order_by(order_clause)
        .offset(max(offset, 0))
        .limit(min(max(limit, 1), 500))
        .all()
    )

    # Resolve a primary owner name per parcel for the page in a single query (no N+1).
    parcel_ids = [p.id for p in items]
    owners: dict[str, str] = {}
    if parcel_ids:
        rows = (
            db.query(models.ParcelParty.parcel_id, models.Party.name)
            .join(models.Party, models.Party.id == models.ParcelParty.party_id)
            .filter(models.ParcelParty.parcel_id.in_(parcel_ids))
            .all()
        )
        for pid, name in rows:
            owners.setdefault(pid, name)

    return {
        "total": total,
        "items": [
            {
                "id": p.id,
                "project_id": p.project_id,
                "county_fips": p.county_fips,
                "owner": owners.get(p.id),
                "stage": p.stage.value if p.stage else "intake",
                "risk_score": p.risk_score,
                "next_deadline_at": (
                    p.next_deadline_at.isoformat() + "Z" if p.next_deadline_at else None
                ),
                "updated_at": (
                    p.updated_at.isoformat() + "Z" if p.updated_at else None
                ),
                "geom": p.geom,
            }
            for p in items
        ],
    }
