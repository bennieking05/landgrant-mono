import json
import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request

from app.api.deps import verify_webhook_signature
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/integrations", tags=["integrations"])

# Require HMAC signature only outside local/test CI (same relaxed policy as WebSocket token checks).
_WEBHOOK_RELAXED_ENVS = frozenset({"dev", "test"})


@router.post("/dockets")
async def docket_webhook(
    request: Request,
    x_lob_signature: Optional[str] = Header(default=None, alias="X-Lob-Signature"),
):
    """Court docket / filing integration webhook (stub).

    Reads the raw body first so HMAC verification uses the same bytes the client signed.
    """
    body = await request.body()

    if settings.environment not in _WEBHOOK_RELAXED_ENVS:
        if not verify_webhook_signature(body, x_lob_signature, settings.session_secret):
            logger.warning("Docket webhook received with invalid signature")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    if body:
        try:
            json.loads(body)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="invalid_json") from exc

    return {
        "received": True,
        "signature_present": bool(x_lob_signature),
    }
