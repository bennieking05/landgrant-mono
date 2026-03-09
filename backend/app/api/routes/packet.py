from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_db
from app.db import models
from app.db.models import Persona
from app.security.rbac import Action, authorize

router = APIRouter(prefix="/packet", tags=["packet"])


@router.get("/checklist")
def packet_checklist(parcel_id: str, persona: Persona = Depends(get_current_persona), db: Session = Depends(get_db)):
    # The workbench treats this as part of packet generation flow; we gate it behind packet EXECUTE.
    authorize(persona, "packet", Action.EXECUTE)
    # Compute checklist from real DB entities.
    title_count = db.query(models.TitleInstrument).filter(models.TitleInstrument.parcel_id == parcel_id).count()
    appraisal = db.query(models.Appraisal).filter(models.Appraisal.parcel_id == parcel_id).first()
    uploads = db.query(models.Document).filter(models.Document.doc_type == "upload").count()

    return {
        "parcel_id": parcel_id,
        "items": [
            {"label": "Title chain attached", "done": title_count > 0},
            {"label": "Appraisal summary validated", "done": bool(appraisal and appraisal.summary)},
            {"label": "Required uploads present", "done": uploads > 0},
        ],
    }



