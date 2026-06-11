"""Statutory sequencing checks for offers (TX / IN) — rules in code, citations in errors."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.db import models
from app.db.models import OfferType, OfferStatus


def _parcel_rule_state(parcel: models.Parcel, project: models.Project) -> str:
    return (
        (parcel.parcel_state or project.state or project.jurisdiction_code or "")
        .strip()
        .upper()
    )


def validate_new_offer(
    db: Session,
    *,
    parcel_id: str,
    project_id: str,
    offer_type: OfferType,
    statutory_override_reason: Optional[str],
) -> tuple[bool, list[str]]:
    """Return (ok, errors). When ``ok`` is False, caller may still proceed if override is logged."""

    errors: list[str] = []
    parcel = db.get(models.Parcel, parcel_id)
    project = db.get(models.Project, project_id)
    if not parcel or not project:
        return False, ["parcel_or_project_not_found"]

    state = _parcel_rule_state(parcel, project)
    override_ok = bool(statutory_override_reason and statutory_override_reason.strip())

    if offer_type != OfferType.FINAL:
        return True, []

    if state == "TX":
        lbor = (
            db.query(models.TxBillOfRightsDelivery)
            .filter(models.TxBillOfRightsDelivery.parcel_id == parcel_id)
            .order_by(models.TxBillOfRightsDelivery.delivery_date.desc())
            .first()
        )
        if lbor is None:
            errors.append(
                "Final offer unavailable: no Texas Landowner Bill of Rights delivery on file "
                "(Tex. Prop. Code ch. 21). Record a delivery in tx_bill_of_rights_deliveries "
                "or provide statutory_override_reason for a supervised override."
            )
        else:
            cutoff = date.today() - timedelta(days=7)
            if lbor.delivery_date > cutoff:
                errors.append(
                    "Final offer unavailable: Landowner Bill of Rights must be delivered at least "
                    "7 calendar days before the final offer (Tex. Prop. Code ch. 21)."
                )

        initial = (
            db.query(models.Offer)
            .filter(
                models.Offer.parcel_id == parcel_id,
                models.Offer.offer_type == OfferType.INITIAL,
                models.Offer.status.in_(
                    [OfferStatus.SENT, OfferStatus.ACCEPTED, OfferStatus.REJECTED]
                ),
            )
            .order_by(models.Offer.sent_date.asc())
            .first()
        )
        if initial is None or initial.sent_date is None:
            errors.append(
                "Final offer unavailable: an initial offer must be sent before a final offer (TX)."
            )
        else:
            sent = initial.sent_date
            if sent.tzinfo is not None:
                sent = sent.replace(tzinfo=None)
            if datetime.utcnow() - sent < timedelta(days=30):
                errors.append(
                    "Final offer unavailable: final offer cannot be made until at least 30 days "
                    "after the initial offer was served (Tex. Prop. Code §21.0113)."
                )

    elif state == "IN":
        initial = (
            db.query(models.Offer)
            .filter(
                models.Offer.parcel_id == parcel_id,
                models.Offer.offer_type == OfferType.INITIAL,
                models.Offer.status.in_(
                    [OfferStatus.SENT, OfferStatus.ACCEPTED, OfferStatus.REJECTED]
                ),
            )
            .order_by(models.Offer.sent_date.asc())
            .first()
        )
        if initial is None or initial.sent_date is None:
            errors.append(
                "Final offer unavailable: an initial offer must be sent before a final offer (IN)."
            )
        else:
            sent = initial.sent_date
            if sent.tzinfo is not None:
                sent = sent.replace(tzinfo=None)
            if datetime.utcnow() - sent < timedelta(days=30):
                errors.append(
                    "Final offer unavailable: at least 30 days must pass after the initial offer "
                    "before advancing the offer sequence (IC 32-24-1-5)."
                )

    if errors and override_ok:
        return True, errors
    if errors:
        return False, errors
    return True, []


def lifecycle_snapshot(db: Session, *, parcel_id: str, project_id: str) -> dict:
    """UI helper: blockers + simple timeline flags."""

    parcel = db.get(models.Parcel, parcel_id)
    project = db.get(models.Project, project_id)
    state = _parcel_rule_state(parcel, project) if parcel and project else ""
    ok, errs = validate_new_offer(
        db,
        parcel_id=parcel_id,
        project_id=project_id,
        offer_type=OfferType.FINAL,
        statutory_override_reason=None,
    )
    lbor_count = (
        db.query(models.TxBillOfRightsDelivery)
        .filter(models.TxBillOfRightsDelivery.parcel_id == parcel_id)
        .count()
        if state == "TX"
        else 0
    )
    offers = (
        db.query(models.Offer)
        .filter(models.Offer.parcel_id == parcel_id)
        .order_by(models.Offer.offer_number.asc())
        .all()
    )
    return {
        "parcel_id": parcel_id,
        "project_id": project_id,
        "rule_state": state,
        "final_offer_statutory_ok": ok and not errs,
        "final_offer_blockers": errs,
        "tx_lbor_deliveries": int(lbor_count),
        "offer_count": len(offers),
        "timeline": [
            {
                "step": "initial_offer",
                "label": "Initial offer (IOL)",
                "done": any(o.offer_type == OfferType.INITIAL for o in offers),
            },
            {
                "step": "lbor",
                "label": "Landowner Bill of Rights delivered (TX)",
                "done": lbor_count > 0,
                "applies": state == "TX",
            },
            {
                "step": "final_offer",
                "label": "Final offer (FOL)",
                "done": any(o.offer_type == OfferType.FINAL for o in offers),
            },
        ],
    }
