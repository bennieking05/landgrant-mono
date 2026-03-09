from fastapi import APIRouter, Header

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/dockets")
def docket_webhook(payload: dict, x_lob_signature: str | None = Header(default=None)):
    # In production verify signature + enqueue Pub/Sub event.
    return {
        "received": True,
        "signature_present": bool(x_lob_signature),
        "payload": payload,
    }
