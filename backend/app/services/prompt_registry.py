"""Prompt registry backed by the ``prompt_templates`` table.

Phase 1.4 of the AI-first robustness plan: every LLM call should resolve its
prompt by ``(name, version)`` instead of formatting a module-level string.
This lets us:

* Log ``prompt_template_id`` / ``prompt_version`` on the corresponding
  :class:`~app.services.ai_telemetry.AIEventInput`, making replays exact.
* Roll back a bad prompt by flipping ``is_active`` without code deploys.
* Diff prompt versions in the Audit UI.

The registry is intentionally small and does not try to be a full CMS: the
canonical prompts ship as code constants in :mod:`app.services.ai_pipeline`
and are seeded into the DB via :func:`seed_default_prompts`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.db import models


@dataclass
class PromptRecord:
    id: str
    name: str
    version: str
    category: str
    system_prompt: Optional[str]
    user_prompt_template: str
    default_model: str
    default_temperature: float
    is_active: bool


def _row_to_record(row: models.PromptTemplate) -> PromptRecord:
    return PromptRecord(
        id=row.id,
        name=row.name,
        version=row.version,
        category=row.category,
        system_prompt=row.system_prompt,
        user_prompt_template=row.user_prompt_template,
        default_model=row.default_model or "gemini-1.5-flash-001",
        default_temperature=float(row.default_temperature or 0.2),
        is_active=bool(row.is_active),
    )


def get_active_prompt(db: Session, name: str) -> Optional[PromptRecord]:
    """Return the active prompt for ``name`` or ``None``.

    When multiple rows for the same ``name`` exist, the most recent active
    one (highest ``updated_at``) wins.  Callers that need a specific version
    should use :func:`get_prompt_version` instead.
    """

    row = (
        db.query(models.PromptTemplate)
        .filter(models.PromptTemplate.name == name)
        .filter(models.PromptTemplate.is_active.is_(True))
        .order_by(models.PromptTemplate.updated_at.desc())
        .first()
    )
    return _row_to_record(row) if row else None


def get_prompt_version(
    db: Session, name: str, version: str
) -> Optional[PromptRecord]:
    row = (
        db.query(models.PromptTemplate)
        .filter(models.PromptTemplate.name == name)
        .filter(models.PromptTemplate.version == version)
        .first()
    )
    return _row_to_record(row) if row else None


@dataclass
class _DefaultPrompt:
    name: str
    version: str
    category: str
    user_prompt_template: str
    system_prompt: Optional[str] = None
    default_model: str = "gemini-1.5-flash-001"
    default_temperature: float = 0.2


def seed_default_prompts(
    db: Session, prompts: Optional[Iterable[_DefaultPrompt]] = None
) -> list[PromptRecord]:
    """Insert / upsert the baseline prompts shipped with the repo.

    Idempotent: an existing row with the same ``(name, version)`` is left
    alone so that manual edits in production are preserved.  New versions are
    created as new rows so that rollback means flipping ``is_active``.
    """

    from app.services import ai_pipeline

    if prompts is None:
        prompts = [
            _DefaultPrompt(
                name="legal_analysis",
                version="2026.04.01",
                category="analysis",
                user_prompt_template=ai_pipeline.LEGAL_ANALYSIS_PROMPT,
                system_prompt=None,
            ),
            _DefaultPrompt(
                name="document_review",
                version="2026.04.01",
                category="document",
                user_prompt_template=ai_pipeline.DOCUMENT_REVIEW_PROMPT,
                system_prompt=None,
            ),
            _DefaultPrompt(
                name="risk_assessment",
                version="2026.04.01",
                category="risk",
                user_prompt_template=ai_pipeline.RISK_ASSESSMENT_PROMPT,
                system_prompt=None,
            ),
        ]

    records: list[PromptRecord] = []
    for p in prompts:
        existing = (
            db.query(models.PromptTemplate)
            .filter(
                models.PromptTemplate.name == p.name,
                models.PromptTemplate.version == p.version,
            )
            .first()
        )
        if existing:
            records.append(_row_to_record(existing))
            continue

        row = models.PromptTemplate(
            id=f"pt_{uuid.uuid4().hex[:12]}",
            name=p.name,
            version=p.version,
            category=p.category,
            user_prompt_template=p.user_prompt_template,
            system_prompt=p.system_prompt,
            default_model=p.default_model,
            default_temperature=p.default_temperature,
            is_active=True,
        )
        db.add(row)
        records.append(_row_to_record(row))

    db.commit()
    return records


def resolve_for_task(db: Session, task_type: str) -> Optional[PromptRecord]:
    """Map a pipeline ``task_type`` to the active prompt.

    Keeps :mod:`ai_pipeline` decoupled from the exact DB schema: it asks the
    registry for an active prompt and falls back to the string constants if
    the DB is empty (first-boot before seeding).
    """

    mapping = {
        "draft_analysis": "legal_analysis",
        "document_review": "document_review",
        "risk_assessment": "risk_assessment",
    }
    name = mapping.get(task_type)
    if not name:
        return None
    return get_active_prompt(db, name)
