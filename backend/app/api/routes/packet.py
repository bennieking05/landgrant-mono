from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_db
from app.db import models
from app.db.models import CurativeStatus, OfferType, Persona
from app.security.rbac import Action, authorize

router = APIRouter(prefix="/packet", tags=["packet"])


@router.get("/checklist")
def packet_checklist(
    parcel_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    # The workbench treats this as part of packet generation flow; we gate it behind packet EXECUTE.
    authorize(persona, "packet", Action.EXECUTE)

    title_doc_count = (
        db.query(func.count(models.TitleDocument.id))
        .filter(models.TitleDocument.parcel_id == parcel_id)
        .scalar()
        or 0
    )
    title_instrument_count = (
        db.query(func.count(models.TitleInstrument.id))
        .filter(models.TitleInstrument.parcel_id == parcel_id)
        .scalar()
        or 0
    )

    appraisal = (
        db.query(models.Appraisal)
        .filter(models.Appraisal.parcel_id == parcel_id)
        .order_by(models.Appraisal.created_at.desc())
        .first()
    )

    uploads = (
        db.query(func.count(models.Document.id))
        .filter(
            models.Document.parcel_id == parcel_id,
            models.Document.doc_type == "upload",
        )
        .scalar()
        or 0
    )

    blocking_curative = (
        db.query(func.count(models.CurativeItem.id))
        .filter(
            models.CurativeItem.parcel_id == parcel_id,
            models.CurativeItem.is_blocking.is_(True),
            models.CurativeItem.status.notin_(
                [CurativeStatus.RESOLVED, CurativeStatus.WAIVED]
            ),
        )
        .scalar()
        or 0
    )

    settlement_offer = (
        db.query(models.Offer)
        .filter(
            models.Offer.parcel_id == parcel_id,
            models.Offer.offer_type == OfferType.SETTLEMENT,
        )
        .order_by(models.Offer.created_date.desc())
        .first()
    )
    settlement_amt: Decimal | None = (
        settlement_offer.amount if settlement_offer else None
    )
    appraised: Decimal | None = appraisal.appraised_value if appraisal else None
    filing_aligned = True
    if settlement_amt is not None and appraised is not None and appraised != 0:
        try:
            diff = abs(float(settlement_amt) - float(appraised)) / abs(float(appraised))
            filing_aligned = diff <= 0.25
        except (TypeError, ValueError):
            filing_aligned = False
    elif settlement_amt is not None and appraised is None:
        filing_aligned = False

    items = [
        {
            "label": "Title report or instrument on file",
            "done": title_doc_count > 0 or title_instrument_count > 0,
        },
        {
            "label": "Appraisal summary validated",
            "done": bool(appraisal and appraisal.summary),
        },
        {
            "label": "Appraisal marked current (not stale)",
            "done": bool(appraisal and not appraisal.staleness_flag),
        },
        {
            "label": "Required uploads present",
            "done": uploads > 0,
        },
        {
            "label": "Curative: no blocking open issues",
            "done": blocking_curative == 0,
        },
        {
            "label": "Settlement vs appraisal filing baseline (within 25%)",
            "done": filing_aligned,
        },
    ]

    return {
        "parcel_id": parcel_id,
        "items": items,
    }
