"""Canonical jurisdiction list for UI (Contract Milestone 1 §2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_persona
from app.core.config import get_settings
from app.db.models import Persona
from app.security.rbac import Action, authorize

router = APIRouter(prefix="/jurisdictions", tags=["jurisdictions"])

_LABELS = {
    "TX": "Texas",
    "IN": "Indiana",
}


@router.get("")
def list_contract_jurisdictions(
    persona: Persona = Depends(get_current_persona),
):
    """Return only jurisdictions the product is contracted to support (TX, IN)."""

    authorize(persona, "parcel", Action.READ)
    settings = get_settings()
    return {
        "items": [
            {
                "code": code,
                "label": _LABELS.get(code, code),
                "active": True,
            }
            for code in settings.contract_jurisdiction_codes
        ]
    }
