"""Regulatory update monitor.

Phase 2.2: wire the ComplianceAgent's ``monitor_law_changes`` hook to
pluggable feed fetchers and persist anything new to the
``regulatory_updates`` and ``law_changes`` tables so the review dashboard
has real rows to triage.

Individual feed adapters (statutory, case law, regulatory) implement the
:class:`RegulatoryFeed` protocol.  The default in-repo adapter returns no
results; ops can register commercial adapters at startup via
:func:`register_feed`.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Protocol

logger = logging.getLogger(__name__)


@dataclass
class FeedItem:
    """A single candidate regulatory update from an external feed."""

    source: str
    source_type: str  # legislature | court | agency
    jurisdiction: str
    change_type: str  # new_statute | amendment | repeal | court_ruling
    title: str
    summary: str
    citation: Optional[str] = None
    full_text: Optional[str] = None
    effective_date: Optional[datetime] = None
    url: Optional[str] = None


class RegulatoryFeed(Protocol):
    async def fetch(self, jurisdiction: str) -> list[FeedItem]: ...


_feeds: dict[str, RegulatoryFeed] = {}


def register_feed(name: str, feed: RegulatoryFeed) -> None:
    """Register a feed adapter.  Overwrites any existing entry."""

    _feeds[name] = feed


def registered_feeds() -> list[str]:
    return sorted(_feeds.keys())


async def fetch_all(jurisdiction: str) -> list[FeedItem]:
    results: list[FeedItem] = []
    for name, feed in _feeds.items():
        try:
            results.extend(await feed.fetch(jurisdiction))
        except Exception as exc:
            logger.warning("regulatory feed %s failed: %s", name, exc)
    return results


def _dedupe_key(item: FeedItem) -> str:
    return f"{item.jurisdiction}|{item.source}|{item.citation or item.title}"


def persist_items(
    db: Any,
    items: list[FeedItem],
) -> dict[str, Any]:
    """Upsert a batch of feed items into ``regulatory_updates``.

    Returns counts so callers (Celery task or CLI) can report progress.
    Items are de-duplicated by ``(jurisdiction, source, citation|title)``
    against the ``pending`` set.
    """

    from app.db import models

    created = 0
    skipped = 0

    existing_keys = set()
    try:
        rows = (
            db.query(models.RegulatoryUpdate)
            .filter(models.RegulatoryUpdate.status == "pending")
            .all()
        )
        for r in rows:
            existing_keys.add(
                f"{r.jurisdiction}|{r.source_name}|{r.citation or r.title}"
            )
    except Exception as exc:
        logger.warning("regulatory_updates dedupe query failed: %s", exc)

    for item in items:
        if _dedupe_key(item) in existing_keys:
            skipped += 1
            continue

        row = models.RegulatoryUpdate(
            id=f"regu_{uuid.uuid4().hex[:12]}",
            jurisdiction=item.jurisdiction,
            source_type=item.source_type,
            source_name=item.source,
            source_url=item.url,
            change_type=item.change_type,
            effective_date=item.effective_date,
            title=item.title,
            summary=item.summary,
            full_text=item.full_text,
            citation=item.citation,
            status="pending",
            detected_at=datetime.utcnow(),
        )
        db.add(row)
        created += 1

        # Also mirror into legacy ``law_changes`` for ComplianceAgent.
        try:
            lc = models.LawChange(
                id=f"lc_{uuid.uuid4().hex[:12]}",
                jurisdiction=item.jurisdiction,
                source=item.source,
                change_type=item.change_type,
                citation=item.citation,
                summary=item.summary,
                full_text=item.full_text,
                effective_date=item.effective_date,
                detected_at=datetime.utcnow(),
            )
            db.add(lc)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("law_changes mirror failed: %s", exc)

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("regulatory persist commit failed: %s", exc)
        return {"created": 0, "skipped": skipped, "error": str(exc)}

    return {"created": created, "skipped": skipped}


async def run_monitor(
    db: Any,
    jurisdictions: list[str],
) -> dict[str, Any]:
    """Fetch + persist for a list of jurisdictions.

    Designed to be invoked by a Celery beat schedule; safe to call from
    synchronous contexts via ``asyncio.run``.
    """

    summary: dict[str, Any] = {"jurisdictions": {}, "total_created": 0}
    for jur in jurisdictions:
        items = await fetch_all(jur)
        result = persist_items(db, items) if db is not None else {
            "created": 0,
            "skipped": len(items),
            "note": "db session not provided",
        }
        summary["jurisdictions"][jur] = {
            "items_fetched": len(items),
            **result,
        }
        summary["total_created"] += int(result.get("created", 0))
    return summary
