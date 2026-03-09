from enum import Enum
from typing import Iterable

from fastapi import HTTPException, status

from app.db.models import Persona


class Action(Enum):
    READ = "read"
    WRITE = "write"
    APPROVE = "approve"
    EXECUTE = "execute"


PERMISSION_MATRIX: dict[Persona, dict[str, set[Action]]] = {
    Persona.LANDOWNER: {
        "portal": {Action.READ, Action.WRITE},
        "decision": {Action.EXECUTE},
        "esign": {Action.READ},  # Can view signing status
    },
    Persona.LAND_AGENT: {
        "parcel": {Action.READ, Action.WRITE},
        "communication": {Action.READ, Action.WRITE},
        "packet": {Action.EXECUTE},
        "title": {Action.READ, Action.WRITE},
        "appraisal": {Action.READ, Action.WRITE},
        "ops": {Action.READ},
        "roe": {Action.READ, Action.WRITE},
        "offer": {Action.READ, Action.WRITE},
        "alignment": {Action.READ, Action.WRITE},
        "esign": {Action.READ, Action.WRITE},  # Can initiate signing
        "portal": {Action.READ, Action.WRITE},  # Can send portal invites to landowners
    },
    Persona.IN_HOUSE_COUNSEL: {
        "template": {Action.READ, Action.WRITE, Action.APPROVE, Action.EXECUTE},
        "binder": {Action.READ, Action.APPROVE},
        "budget": {Action.READ, Action.WRITE},
        "communication": {Action.READ, Action.WRITE},
        "deadline": {Action.READ, Action.WRITE},
        "ops": {Action.READ},
        "roe": {Action.READ},
        "offer": {Action.READ, Action.APPROVE},
        "litigation": {Action.READ, Action.WRITE},
        "alignment": {Action.READ},
        "esign": {Action.READ, Action.WRITE, Action.APPROVE},  # Full e-sign access
        "portal": {Action.READ, Action.WRITE},  # Can send portal invites
    },
    Persona.OUTSIDE_COUNSEL: {
        "case": {Action.READ, Action.WRITE},
        "deadline": {Action.READ, Action.WRITE},
        "status": {Action.EXECUTE},
        "litigation": {Action.READ, Action.WRITE},
        "esign": {Action.READ},  # Can view signing status
    },
    Persona.FIRM_ADMIN: {
        # Law firm admin - read access to cases within their firm's projects
        "parcel": {Action.READ},
        "communication": {Action.READ},
        "offer": {Action.READ},
        "litigation": {Action.READ},
        "roe": {Action.READ},
        "title": {Action.READ},
        "appraisal": {Action.READ},
        "alignment": {Action.READ},
        "portal": {Action.READ},
        "esign": {Action.READ},
        "admin_firm": {Action.READ},  # Firm admin dashboard access
        "audit": {Action.READ},  # Can view audit logs for their projects
    },
    Persona.ADMIN: {
        # Platform admin - global access across all firms/projects
        "rbac": {Action.READ, Action.WRITE},
        "audit": {Action.READ},
        "esign": {Action.READ, Action.WRITE},
        "admin_platform": {Action.READ},  # Platform admin dashboard access
        "parcel": {Action.READ},  # Global read access
        "communication": {Action.READ},
        "offer": {Action.READ},
        "litigation": {Action.READ},
        "roe": {Action.READ},
        "title": {Action.READ},
        "appraisal": {Action.READ},
        "alignment": {Action.READ},
        "portal": {Action.READ},
        "project": {Action.READ},  # Can see all projects
    },
}


def authorize(persona: Persona, resource: str, action: Action) -> None:
    allowed = PERMISSION_MATRIX.get(persona, {})
    if action not in allowed.get(resource, set()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{persona.value} cannot {action.value} {resource}",
        )
