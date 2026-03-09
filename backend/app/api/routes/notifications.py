from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_user, get_db
from app.db.models import Persona
from app.security.rbac import Action, authorize
from app.services.notifications import preview_or_send


router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationPreviewRequest(BaseModel):
    template_id: str = Field(..., examples=["portal_invite", "decision_confirmation"])
    channel: str = Field(..., examples=["email", "sms"])
    to: str
    project_id: str
    parcel_id: str
    variables: dict = Field(default_factory=dict)


@router.post("/preview")
def preview_notification(
    payload: NotificationPreviewRequest,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # Treat as a comms write action (agent/counsel) or portal write (landowner). For now: allow agents/counsel only.
    authorize(persona, "communication", Action.WRITE)
    preview = preview_or_send(
        db,
        persona=persona,
        template_id=payload.template_id,
        channel=payload.channel,  # type: ignore[arg-type]
        to=payload.to,
        variables=payload.variables,
        project_id=payload.project_id,
        parcel_id=payload.parcel_id,
        user_id=getattr(user, "id", None),
    )
    return preview.__dict__



