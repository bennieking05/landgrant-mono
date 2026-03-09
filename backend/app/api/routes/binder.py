from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_persona
from app.db.models import Persona
from app.security.rbac import Action, authorize

router = APIRouter(prefix="/binder", tags=["binder"])


@router.get("/status")
def binder_status(project_id: str, persona: Persona = Depends(get_current_persona)):
    authorize(persona, "binder", Action.READ)
    return {
        "project_id": project_id,
        "sections": [
            {"name": "Comms timeline", "status": "Complete"},
            {"name": "Rule results", "status": "Complete"},
            {"name": "Approvals", "status": "Pending"},
        ],
    }




