from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])


class InviteProbeResponse(BaseModel):
    status: str
    checks: list[str]


class EsignProbeResponse(BaseModel):
    status: str
    vendor: str


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/invite", response_model=InviteProbeResponse)
def invite_probe() -> InviteProbeResponse:
    return InviteProbeResponse(status="invite-flow", checks=["magic_link", "email_queue"])


@router.get("/esign", response_model=EsignProbeResponse)
def esign_probe() -> EsignProbeResponse:
    return EsignProbeResponse(status="esign", vendor="adobe")
