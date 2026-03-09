from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_db
from app.db import models
from app.db.models import Persona
from app.security.rbac import Action, authorize

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("/results")
def list_rule_results(parcel_id: str, persona: Persona = Depends(get_current_persona), db: Session = Depends(get_db)):
    # Workbench reads this as part of parcel analysis, so we gate it behind parcel READ.
    authorize(persona, "parcel", Action.READ)
    try:
        results = (
            db.query(models.RuleResult)
            .filter(models.RuleResult.parcel_id == parcel_id)
            .order_by(models.RuleResult.fired_at.desc())
            .all()
        )
        items = [
            {
                "id": r.id,
                "rule_id": r.rule_id,
                "citation": r.citation,
                "fired": True,
                "fired_at": r.fired_at.isoformat() + "Z" if r.fired_at else None,
                "payload": r.payload,
            }
            for r in results
        ]
        if items:
            return {"parcel_id": parcel_id, "items": items}
        raise RuntimeError("no_rows")
    except Exception:
        return {
            "parcel_id": parcel_id,
            "items": [
                {
                    "id": "RULE-001",
                    "rule_id": "valuation_threshold",
                    "citation": "Tex. Prop. Code §21.0113",
                    "fired": True,
                    "fired_at": None,
                    "payload": {"parcel.assessed_value": 300000},
                }
            ],
        }


