from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_principal, get_db
from app.db import models
from app.db.models import OfferStatus, Persona, ParcelStage
from app.security.access_scope import filter_parcels_query, require_parcel_scope
from app.security.jwt_auth import JWTPrincipal
from app.security.rbac import Action, authorize
from app.services.hashing import sha256_hex

router = APIRouter(prefix="/parcels", tags=["parcels"])


# Columns the enterprise grid (UX-4) may sort by. Keep this allowlist tight.
SORT_COLUMNS = {
    "id": models.Parcel.id,
    "stage": models.Parcel.stage,
    "risk_score": models.Parcel.risk_score,
    "next_deadline_at": models.Parcel.next_deadline_at,
    "updated_at": models.Parcel.updated_at,
    "county_fips": models.Parcel.county_fips,
}


def _filtered_parcels_query(
    db: Session,
    principal: JWTPrincipal,
    *,
    project_id: Optional[str] = None,
    stage: Optional[str] = None,
    min_risk: Optional[int] = None,
    deadline_before: Optional[str] = None,
    q: Optional[str] = None,
    county: Optional[str] = None,
    assigned_to: Optional[str] = None,
    offer_status: Optional[str] = None,
) -> Any:
    query = db.query(models.Parcel)
    query = filter_parcels_query(db, principal, query)
    if project_id:
        query = query.filter(models.Parcel.project_id == project_id)
    if stage:
        try:
            stage_enum = ParcelStage(stage)
            query = query.filter(models.Parcel.stage == stage_enum)
        except ValueError:
            query = query.filter(False)
    if min_risk is not None:
        query = query.filter(models.Parcel.risk_score >= min_risk)
    if deadline_before:
        try:
            dt = datetime.fromisoformat(deadline_before.replace("Z", ""))
            query = query.filter(models.Parcel.next_deadline_at.isnot(None)).filter(
                models.Parcel.next_deadline_at <= dt
            )
        except Exception:
            pass
    if county and county.strip():
        like = f"%{county.strip()}%"
        query = query.filter(models.Parcel.county.ilike(like))
    if assigned_to:
        pids = [
            r[0]
            for r in (
                db.query(models.Task.parcel_id)
                .filter(
                    models.Task.assigned_to == assigned_to,
                    models.Task.status == "open",
                    models.Task.parcel_id.isnot(None),
                )
                .distinct()
                .all()
            )
        ]
        if not pids:
            query = query.filter(False)
        else:
            query = query.filter(models.Parcel.id.in_(pids))
    if offer_status:
        try:
            ost = OfferStatus(offer_status)
        except ValueError:
            query = query.filter(False)
        else:
            pids = [
                r[0]
                for r in (
                    db.query(models.Offer.parcel_id)
                    .filter(models.Offer.status == ost)
                    .distinct()
                    .all()
                )
            ]
            if not pids:
                query = query.filter(False)
            else:
                query = query.filter(models.Parcel.id.in_(pids))
    if q and q.strip():
        like = f"%{q.strip()}%"
        owner_parcel_ids = (
            db.query(models.ParcelParty.parcel_id)
            .join(models.Party, models.Party.id == models.ParcelParty.party_id)
            .filter(models.Party.name.ilike(like))
        )
        query = query.filter(
            or_(
                models.Parcel.id.ilike(like),
                models.Parcel.county_fips.ilike(like),
                models.Parcel.id.in_(owner_parcel_ids),
            )
        )
    return query


@router.get("/export.csv")
def export_parcels_csv(
    project_id: Optional[str] = None,
    stage: Optional[str] = None,
    min_risk: Optional[int] = None,
    deadline_before: Optional[str] = None,
    q: Optional[str] = None,
    county: Optional[str] = None,
    assigned_to: Optional[str] = None,
    offer_status: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
    principal: JWTPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> Response:
    """Server-generated CSV of the filtered parcel set; audit-logged (UX-4)."""
    authorize(persona, "parcel", Action.READ)
    query = _filtered_parcels_query(
        db,
        principal,
        project_id=project_id,
        stage=stage,
        min_risk=min_risk,
        deadline_before=deadline_before,
        q=q,
        county=county,
        assigned_to=assigned_to,
        offer_status=offer_status,
    )
    items = query.order_by(models.Parcel.updated_at.desc()).limit(500).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "project_id",
            "segment_id",
            "county",
            "parcel_state",
            "county_fips",
            "stage",
            "risk_score",
            "next_deadline_at",
            "updated_at",
        ]
    )
    for p in items:
        writer.writerow(
            [
                p.id,
                p.project_id,
                p.segment_id or "",
                p.county or "",
                p.parcel_state or "",
                p.county_fips,
                p.stage.value if p.stage else "intake",
                p.risk_score,
                p.next_deadline_at.isoformat() if p.next_deadline_at else "",
                p.updated_at.isoformat() if p.updated_at else "",
            ]
        )
    body = buf.getvalue()
    payload = {
        "row_count": len(items),
        "project_id": project_id,
        "stage": stage,
        "min_risk": min_risk,
        "deadline_before": deadline_before,
        "q": q,
        "county": county,
        "assigned_to": assigned_to,
        "offer_status": offer_status,
    }
    db.add(
        models.AuditEvent(
            id=str(uuid4()),
            firm_id=principal.firm_id,
            user_id=principal.user_id,
            actor_persona=persona,
            action="parcels.export_csv",
            resource="parcel",
            payload=payload,
            hash=sha256_hex(payload),
        )
    )
    db.commit()
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="parcels_export.csv"'},
    )


@router.get("/{parcel_id}/timeline")
def parcel_timeline(
    parcel_id: str,
    persona: Persona = Depends(get_current_persona),
    principal: JWTPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Merged timeline for parcel detail (UX-6): offers, communications, rule results."""
    authorize(persona, "parcel", Action.READ)
    require_parcel_scope(db, principal, parcel_id)
    p = (
        filter_parcels_query(db, principal, db.query(models.Parcel))
        .filter(models.Parcel.id == parcel_id)
        .first()
    )
    if not p:
        return {"parcel_id": parcel_id, "events": []}

    events: list[dict[str, Any]] = []
    for o in (
        db.query(models.Offer)
        .filter(models.Offer.parcel_id == parcel_id)
        .order_by(models.Offer.created_date.desc())
        .limit(100)
        .all()
    ):
        events.append(
            {
                "id": f"offer-{o.id}",
                "kind": "offer",
                "title": f"Offer {o.offer_number or ''}".strip(),
                "detail": str(
                    o.status.value if hasattr(o.status, "value") else o.status
                ),
                "at": o.sent_date.isoformat() if o.sent_date else None,
                "actor": None,
                "source": f"/offers?parcel_id={parcel_id}",
            }
        )
    for c in (
        db.query(models.Communication)
        .filter(models.Communication.parcel_id == parcel_id)
        .order_by(models.Communication.created_at.desc())
        .limit(100)
        .all()
    ):
        events.append(
            {
                "id": f"comm-{c.id}",
                "kind": "communication",
                "title": f"{c.channel} communication",
                "detail": c.summary or c.delivery_status,
                "at": c.created_at.isoformat() if c.created_at else None,
                "actor": c.initiated_by,
                "source": f"/communications?parcel_id={parcel_id}",
            }
        )
    for r in (
        db.query(models.RuleResult)
        .filter(models.RuleResult.parcel_id == parcel_id)
        .order_by(models.RuleResult.fired_at.desc())
        .limit(100)
        .all()
    ):
        fired = True
        if isinstance(r.payload, dict):
            fired = bool(r.payload.get("fired", True))
        if not fired:
            continue
        events.append(
            {
                "id": f"rule-{r.id}",
                "kind": "rule",
                "title": f"Rule fired: {r.rule_id}",
                "detail": r.citation,
                "at": r.fired_at.isoformat() if r.fired_at else None,
                "actor": None,
                "source": f"/rules/results?parcel_id={parcel_id}",
            }
        )

    events.sort(
        key=lambda e: e["at"] or "",
        reverse=True,
    )
    return {"parcel_id": parcel_id, "events": events}


@router.get("")
def list_parcels(
    project_id: Optional[str] = None,
    stage: Optional[str] = None,
    min_risk: Optional[int] = None,
    deadline_before: Optional[str] = None,
    q: Optional[str] = None,
    county: Optional[str] = None,
    assigned_to: Optional[str] = None,
    offer_status: Optional[str] = None,
    sort: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    persona: Persona = Depends(get_current_persona),
    principal: JWTPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    authorize(persona, "parcel", Action.READ)
    query = _filtered_parcels_query(
        db,
        principal,
        project_id=project_id,
        stage=stage,
        min_risk=min_risk,
        deadline_before=deadline_before,
        q=q,
        county=county,
        assigned_to=assigned_to,
        offer_status=offer_status,
    )

    total = query.count()

    order_clause = models.Parcel.updated_at.desc()
    if sort:
        key = sort[1:] if sort.startswith("-") else sort
        col = SORT_COLUMNS.get(key)
        if col is not None:
            order_clause = col.desc() if sort.startswith("-") else col.asc()

    items = (
        query.order_by(order_clause)
        .offset(max(offset, 0))
        .limit(min(max(limit, 1), 500))
        .all()
    )

    parcel_ids = [p.id for p in items]
    owners: dict[str, str] = {}
    if parcel_ids:
        rows = (
            db.query(models.ParcelParty.parcel_id, models.Party.name)
            .join(models.Party, models.Party.id == models.ParcelParty.party_id)
            .filter(models.ParcelParty.parcel_id.in_(parcel_ids))
            .all()
        )
        for pid, name in rows:
            owners.setdefault(pid, name)

    project_names: dict[str, str] = {}
    proj_ids = {p.project_id for p in items}
    if proj_ids:
        for pr in db.query(models.Project).filter(models.Project.id.in_(proj_ids)).all():
            project_names[pr.id] = pr.name

    segment_labels: dict[str, str] = {}
    alignment_labels: dict[str, str] = {}
    seg_ids = [sid for sid in (p.segment_id for p in items) if sid]
    if seg_ids:
        segs = db.query(models.Segment).filter(models.Segment.id.in_(seg_ids)).all()
        aln_ids = {s.alignment_id for s in segs}
        aln_names: dict[str, str] = {}
        if aln_ids:
            for a in db.query(models.Alignment).filter(models.Alignment.id.in_(aln_ids)).all():
                aln_names[a.id] = a.name
        for s in segs:
            segment_labels[s.id] = (
                s.name
                if s.name
                else (
                    f"Segment {s.segment_number}"
                    if s.segment_number is not None
                    else s.id[:8]
                )
            )
            alignment_labels[s.id] = aln_names.get(s.alignment_id, "")

    latest_offer_status: dict[str, str] = {}
    if parcel_ids:
        offers = (
            db.query(models.Offer)
            .filter(models.Offer.parcel_id.in_(parcel_ids))
            .order_by(models.Offer.parcel_id, models.Offer.created_date.desc())
            .all()
        )
        for o in offers:
            if o.parcel_id in latest_offer_status:
                continue
            st = o.status
            latest_offer_status[o.parcel_id] = (
                st.value if hasattr(st, "value") else str(st)
            )

    assignee_user_by_parcel: dict[str, str] = {}
    if parcel_ids:
        tasks = (
            db.query(models.Task)
            .filter(
                models.Task.parcel_id.in_(parcel_ids),
                models.Task.status == "open",
                models.Task.assigned_to.isnot(None),
            )
            .order_by(models.Task.parcel_id, models.Task.due_at.asc())
            .all()
        )
        for t in tasks:
            if t.parcel_id and t.parcel_id not in assignee_user_by_parcel and t.assigned_to:
                assignee_user_by_parcel[t.parcel_id] = t.assigned_to

    user_names: dict[str, str] = {}
    uids = set(assignee_user_by_parcel.values())
    if uids:
        for u in db.query(models.User).filter(models.User.id.in_(uids)).all():
            user_names[u.id] = (u.full_name or u.email or u.id)

    return {
        "total": total,
        "items": [
            {
                "id": p.id,
                "project_id": p.project_id,
                "project_name": project_names.get(p.project_id),
                "segment_id": p.segment_id,
                "segment_label": (
                    segment_labels.get(p.segment_id) if p.segment_id else None
                ),
                "alignment_label": (
                    alignment_labels.get(p.segment_id) if p.segment_id else None
                ),
                "county": p.county,
                "parcel_state": p.parcel_state,
                "county_fips": p.county_fips,
                "owner": owners.get(p.id),
                "stage": p.stage.value if p.stage else "intake",
                "risk_score": p.risk_score,
                "offer_status": latest_offer_status.get(p.id),
                "assignee_name": (
                    user_names.get(assignee_user_by_parcel[p.id])
                    if p.id in assignee_user_by_parcel
                    else None
                ),
                "next_deadline_at": (
                    p.next_deadline_at.isoformat() + "Z" if p.next_deadline_at else None
                ),
                "updated_at": (
                    p.updated_at.isoformat() + "Z" if p.updated_at else None
                ),
                "geom": p.geom,
            }
            for p in items
        ],
    }
