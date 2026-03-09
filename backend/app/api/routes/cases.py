from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_persona
from app.db import models
from app.db.models import Persona
from app.security.rbac import authorize, Action

from pydantic import BaseModel

router = APIRouter(prefix="/cases", tags=["cases"])

# In-memory fallback for dev when DB is unavailable.
_parcels_fallback: dict[str, dict] = {}


class PartyPayload(BaseModel):
    name: str
    role: str
    email: str | None = None


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
    next_deadline_at: str | None = None


@router.post("", response_model=CaseResponse)
def create_case(payload: CaseCreate, persona: Persona = Depends(get_current_persona), db: Session = Depends(get_db)):
    authorize(persona, "parcel", Action.WRITE)

    parcel_ids: list[str] = []
    try:
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
        db.commit()
    except Exception:
        # DB unavailable -> store minimal parcel in memory so UI flows still work.
        for parcel_payload in payload.parcels:
            parcel_id = str(uuid4())
            _parcels_fallback[parcel_id] = {
                "id": parcel_id,
                "project_id": payload.project_id,
                "stage": parcel_payload.stage,
                "risk_score": parcel_payload.risk_score,
                "county_fips": parcel_payload.county_fips,
                "next_deadline_at": None,
            }
            parcel_ids.append(parcel_id)

    return CaseResponse(project_id=payload.project_id, parcel_ids=parcel_ids)


@router.get("/{parcel_id}")
def get_case(parcel_id: str, persona: Persona = Depends(get_current_persona), db: Session = Depends(get_db)):
    authorize(persona, "parcel", Action.READ)
    try:
        parcel = db.get(models.Parcel, parcel_id)
        if not parcel:
            return {"error": "not_found"}
        return {
            "id": parcel.id,
            "project_id": parcel.project_id,
            "stage": parcel.stage,
            "risk_score": parcel.risk_score,
            "next_deadline_at": parcel.next_deadline_at,
        }
    except Exception:
        fallback = _parcels_fallback.get(parcel_id)
        return fallback if fallback else {"error": "not_found"}
