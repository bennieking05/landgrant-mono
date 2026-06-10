from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_persona
from app.db.models import Persona
from app.security.rbac import Action, authorize

router = APIRouter(prefix="/health", tags=["health"])


class InviteProbeResponse(BaseModel):
    status: str
    checks: list[str]


class EsignProbeResponse(BaseModel):
    status: str
    vendor: str


def _authorize_ops_health(persona: Persona) -> None:
    if persona in (Persona.ADMIN, Persona.PLATFORM_ADMIN):
        authorize(persona, "admin_platform", Action.READ)
        return
    authorize(persona, "ops", Action.READ)


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/invite", response_model=InviteProbeResponse)
def invite_probe(
    persona: Persona = Depends(get_current_persona),
) -> InviteProbeResponse:
    _authorize_ops_health(persona)
    return InviteProbeResponse(
        status="invite-flow", checks=["magic_link", "email_queue"]
    )


@router.get("/esign", response_model=EsignProbeResponse)
def esign_probe(
    persona: Persona = Depends(get_current_persona),
) -> EsignProbeResponse:
    _authorize_ops_health(persona)
    return EsignProbeResponse(status="esign", vendor="adobe")
