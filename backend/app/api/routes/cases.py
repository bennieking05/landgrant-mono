import logging
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_persona, get_current_principal
from app.db import models
from app.db.models import Persona
from app.security.access_scope import require_parcel_scope
from app.security.jwt_auth import JWTPrincipal
from app.security.rbac import authorize, Action

from pydantic import BaseModel

router = APIRouter(prefix="/cases", tags=["cases"])
logger = logging.getLogger(__name__)


class PartyPayload(BaseModel):
    name: str
    role: str
    email: Optional[str] = None


class ParcelPayload(BaseModel):
    county_fips: str
    stage: str = "intake"
    risk_score: int = 0
    parties: List[PartyPayload] = []


class CaseCreate(BaseModel):
    project_id: str
    parcels: List[ParcelPayload]
    jurisdiction_code: str
    stage: str = "intake"


class CaseResponse(BaseModel):
    project_id: str
    parcel_ids: List[str]
    next_deadline_at: Optional[str] = None


@router.post("", response_model=CaseResponse)
def create_case(
    payload: CaseCreate,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    authorize(persona, "parcel", Action.WRITE)

    parcel_ids: list[str] = []
    try:
        project = db.get(models.Project, payload.project_id)
        if project is None:
            project = models.Project(
                id=payload.project_id,
                name=f"Project {payload.project_id}",
                jurisdiction_code=payload.jurisdiction_code,
                stage=payload.stage,
            )
            db.add(project)
            db.flush()

        for parcel_payload in payload.parcels:
            parcel_id = str(uuid4())
            parcel = models.Parcel(
                id=parcel_id,
                project_id=payload.project_id,
                county_fips=parcel_payload.county_fips,
                stage=parcel_payload.stage,
                risk_score=parcel_payload.risk_score,
            )
            db.add(parcel)
            parcel_ids.append(parcel_id)

            for party_payload in parcel_payload.parties:
                party = models.Party(
                    id=str(uuid4()),
                    name=party_payload.name,
                    role=party_payload.role,
                    email=party_payload.email,
                )
                db.add(party)
                db.add(
                    models.ParcelParty(
                        parcel_id=parcel_id,
                        party_id=party.id,
                        relationship_type=party_payload.role,
                    )
                )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to create parcel case for project %s", payload.project_id)
        raise HTTPException(status_code=500, detail="case_create_failed") from exc

    return CaseResponse(project_id=payload.project_id, parcel_ids=parcel_ids)


@router.get("/{parcel_id}")
def get_case(
    parcel_id: str,
    persona: Persona = Depends(get_current_persona),
    principal: JWTPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    authorize(persona, "case", Action.READ)
    require_parcel_scope(db, principal, parcel_id)
    try:
        parcel = db.get(models.Parcel, parcel_id)
        if not parcel:
            raise HTTPException(status_code=404, detail="not_found")
        return {
            "id": parcel.id,
            "project_id": parcel.project_id,
            "stage": parcel.stage,
            "risk_score": parcel.risk_score,
            "next_deadline_at": parcel.next_deadline_at,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="case_read_failed") from exc
