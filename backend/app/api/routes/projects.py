"""Project-scoped workspace APIs (hierarchy, navigation)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_principal, get_db
from app.db import models
from app.db.models import Persona
from app.security.access_scope import filter_parcels_query
from app.security.jwt_auth import JWTPrincipal
from app.security.rbac import Action, authorize

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/{project_id}/hierarchy")
def get_project_hierarchy(
    project_id: str,
    persona: Persona = Depends(get_current_persona),
    principal: JWTPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Return Project → Alignment → Segment → Parcel tree for workbench navigation."""

    authorize(persona, "parcel", Action.READ)
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    if principal.firm_id and project.firm_id and project.firm_id != principal.firm_id:
        raise HTTPException(status_code=403, detail="project_firm_mismatch")

    alignments = (
        db.query(models.Alignment)
        .filter(models.Alignment.project_id == project_id)
        .order_by(models.Alignment.id.asc())
        .all()
    )
    alignment_payload: list[dict] = []
    for a in alignments:
        segs = (
            db.query(models.Segment)
            .filter(models.Segment.alignment_id == a.id)
            .order_by(models.Segment.id.asc())
            .all()
        )
        seg_payload: list[dict] = []
        for s in segs:
            pq = db.query(models.Parcel).filter(models.Parcel.segment_id == s.id)
            pq = filter_parcels_query(db, principal, pq)
            parcels = pq.order_by(models.Parcel.id.asc()).all()
            seg_payload.append(
                {
                    "id": s.id,
                    "name": s.name,
                    "segment_number": s.segment_number,
                    "parcels": [
                        {
                            "id": p.id,
                            "stage": p.stage.value if p.stage else None,
                            "county_fips": p.county_fips,
                            "parcel_state": p.parcel_state,
                        }
                        for p in parcels
                    ],
                }
            )
        alignment_payload.append(
            {
                "id": a.id,
                "name": a.name,
                "alignment_type": a.alignment_type,
                "segments": seg_payload,
            }
        )

    uq = db.query(models.Parcel).filter(
        models.Parcel.project_id == project_id,
        models.Parcel.segment_id.is_(None),
    )
    uq = filter_parcels_query(db, principal, uq)
    unassigned = uq.order_by(models.Parcel.id.asc()).all()

    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "state": project.state or project.jurisdiction_code,
            "jurisdiction_code": project.jurisdiction_code,
        },
        "alignments": alignment_payload,
        "unassigned_parcels": [
            {
                "id": p.id,
                "stage": p.stage.value if p.stage else None,
                "county_fips": p.county_fips,
                "parcel_state": p.parcel_state,
            }
            for p in unassigned
        ],
    }
