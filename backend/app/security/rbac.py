from enum import Enum

from fastapi import HTTPException, status

from app.db.models import Persona


class Action(Enum):
    READ = "read"
    WRITE = "write"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    EXECUTE = "execute"


# DEV_KICKOFF matrix — see docs/security.md. ``platform_admin`` owns cross-tenant
# ``/admin`` and ``admin_platform``; ``firm_admin`` is tenant-scoped.
PERMISSION_MATRIX: dict[Persona, dict[str, set[Action]]] = {
    Persona.LANDOWNER: {
        "portal": {Action.READ, Action.WRITE},
        "communication": {Action.READ},
        "chat": {Action.READ, Action.WRITE},
        "offer": {Action.READ, Action.WRITE},
        "decision": {Action.EXECUTE},
        "esign": {Action.READ, Action.WRITE},
        "parcel": {Action.READ},
        "case": {Action.READ},
    },
    Persona.LAND_AGENT: {
        "parcel": {Action.READ, Action.WRITE, Action.UPDATE, Action.CREATE},
        "communication": {Action.READ, Action.WRITE},
        "packet": {Action.EXECUTE},
        "title": {Action.READ, Action.WRITE},
        "appraisal": {Action.READ, Action.WRITE},
        "ops": {Action.READ},
        "roe": {Action.READ, Action.WRITE},
        "offer": {Action.READ, Action.WRITE},
        "alignment": {Action.READ, Action.WRITE},
        "esign": {Action.READ, Action.WRITE},
        "portal": {Action.READ, Action.WRITE},
        "task": {Action.READ, Action.CREATE, Action.UPDATE},
        "rules": {Action.READ},
        "analytics": {Action.READ},
        "predictions": {Action.READ},
        "rag": {Action.READ},
        "copilot": {Action.READ, Action.WRITE},
        "case": {Action.READ, Action.WRITE},
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
        "esign": {Action.READ, Action.WRITE, Action.APPROVE},
        "portal": {Action.READ, Action.WRITE},
        "ai_agent": {Action.READ, Action.WRITE, Action.EXECUTE, Action.APPROVE},
        "parcel": {Action.READ, Action.APPROVE, Action.UPDATE},
        "task": {Action.READ, Action.CREATE, Action.UPDATE, Action.DELETE},
        "rules": {Action.READ, Action.WRITE},
        "qa": {Action.READ, Action.WRITE},
        "approvals": {Action.READ, Action.WRITE, Action.APPROVE},
        "analytics": {Action.READ},
        "predictions": {Action.READ},
        "rag": {Action.READ},
        "copilot": {Action.READ, Action.WRITE},
        "case": {Action.READ, Action.WRITE},
    },
    Persona.OUTSIDE_COUNSEL: {
        "case": {Action.READ, Action.WRITE, Action.CREATE},
        "deadline": {Action.READ, Action.WRITE},
        "status": {Action.EXECUTE},
        "litigation": {Action.READ, Action.WRITE},
        "budget": {Action.READ},
        "esign": {Action.READ},
        "task": {Action.READ},
        "rules": {Action.READ},
        "parcel": {Action.READ},
    },
    Persona.FIRM_ADMIN: {
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
        "admin_firm": {Action.READ},
        "audit": {Action.READ},
        "task": {Action.READ},
    },
    Persona.PLATFORM_ADMIN: {
        "rbac": {Action.READ, Action.WRITE},
        "audit": {Action.READ, Action.WRITE},
        "esign": {Action.READ, Action.WRITE},
        "admin_platform": {Action.READ},
        "parcel": {Action.READ},
        "communication": {Action.READ},
        "offer": {Action.READ},
        "litigation": {Action.READ},
        "roe": {Action.READ},
        "title": {Action.READ},
        "appraisal": {Action.READ},
        "alignment": {Action.READ},
        "portal": {Action.READ},
        "project": {Action.READ},
        "task": {Action.READ, Action.CREATE, Action.UPDATE, Action.DELETE},
        "rules": {Action.READ, Action.WRITE},
        "qa": {Action.READ, Action.WRITE},
        "approvals": {Action.READ, Action.WRITE, Action.APPROVE},
        "analytics": {Action.READ},
        "predictions": {Action.READ},
        "rag": {Action.READ, Action.WRITE},
        "copilot": {Action.READ, Action.WRITE},
    },
    # Legacy DB-only persona — JWTs normalize ``admin`` to ``platform_admin``.
    Persona.ADMIN: {
        "rbac": {Action.READ},
        "audit": {Action.READ},
        "parcel": {Action.READ},
    },
}


def authorize(persona: Persona, resource: str, action: Action) -> None:
    allowed = PERMISSION_MATRIX.get(persona, {})
    if action not in allowed.get(resource, set()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{persona.value} cannot {action.value} {resource}",
        )
