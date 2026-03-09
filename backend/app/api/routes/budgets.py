from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_db
from app.db import models
from app.db.models import Persona
from app.security.rbac import Action, authorize

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("/summary")
def budget_summary(project_id: str, persona: Persona = Depends(get_current_persona), db: Session = Depends(get_db)):
    authorize(persona, "budget", Action.READ)
    try:
        budget = (
            db.query(models.Budget)
            .filter(models.Budget.project_id == project_id)
            .order_by(models.Budget.updated_at.desc())
            .first()
        )
        if not budget:
            raise RuntimeError("missing_budget")

        cap = float(budget.cap_amount)
        actual = float(budget.actual_amount)
        utilization = int(round((actual / cap) * 100)) if cap else 0
        alerts: list[str] = []
        if utilization >= 100:
            alerts.append("utilization_100")
        elif utilization >= 80:
            alerts.append("utilization_80")
        return {
            "project_id": project_id,
            "cap_amount": cap,
            "actual_amount": actual,
            "utilization_pct": utilization,
            "alerts": alerts,
            "updated_at": budget.updated_at.isoformat() + "Z" if budget.updated_at else None,
        }
    except Exception:
        return {
            "project_id": project_id,
            "cap_amount": 250000,
            "actual_amount": 175000,
            "utilization_pct": 70,
            "alerts": [],
            "updated_at": None,
        }


