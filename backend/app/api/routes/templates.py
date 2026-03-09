import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_user, get_db
from app.db import models
from app.db.models import Persona
from app.security.rbac import authorize, Action
from app.services.hashing import sha256_hex

TEMPLATE_ROOT = Path(__file__).resolve().parents[4] / "templates" / "library"

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateMetadata(BaseModel):
    id: str
    version: str
    locale: str
    jurisdiction: str | None = None
    variables: dict
    privilege: str


@router.get("", response_model=list[TemplateMetadata])
def list_templates(persona: Persona = Depends(get_current_persona)):
    authorize(persona, "template", Action.READ)
    templates: list[TemplateMetadata] = []
    for meta_file in TEMPLATE_ROOT.rglob("meta.json"):
        data = TemplateMetadata.model_validate_json(meta_file.read_text())
        templates.append(data)
    return templates


class TemplateRenderRequest(BaseModel):
    template_id: str
    locale: str = "en-US"
    variables: dict
    # Optional: persist the rendered document
    persist: bool = False
    project_id: str | None = None
    parcel_id: str | None = None


class TemplateRenderResponse(BaseModel):
    rendered: str
    document_id: str | None = None
    deadline_anchors: dict[str, str] | None = None  # Extracted anchor dates for deadline derivation


def _extract_deadline_anchors(template_id: str, variables: dict) -> dict[str, str]:
    """
    Extract deadline anchor dates from template variables.

    Maps template variable names to standard anchor event names that can
    be used with the deadline derivation service.
    """
    # Load template metadata to check for tracked_dates and deadline_anchors
    meta_file = TEMPLATE_ROOT / template_id / "meta.json"
    anchors: dict[str, str] = {}

    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text())
            # Use explicit deadline_anchors mapping if defined
            anchor_mapping = meta.get("deadline_anchors", {})
            for event_name, var_name in anchor_mapping.items():
                if var_name in variables and variables[var_name]:
                    anchors[event_name] = str(variables[var_name])

            # Also extract from tracked_dates
            for tracked in meta.get("tracked_dates", []):
                field = tracked.get("field")
                event = tracked.get("event")
                if field and event and field in variables and variables[field]:
                    anchors[event] = str(variables[field])
        except (json.JSONDecodeError, KeyError):
            pass

    # Fallback: common variable name patterns
    common_mappings = {
        "service_date": "offer_served",
        "offer_date": "offer_served",
        "complaint_date": "complaint_filed",
        "filing_date": "complaint_filed",
        "notice_date": "notice_served",
        "report_date": "appraisers_report_mailed",
        "trial_date": "trial_date_set",
    }

    for var_name, event_name in common_mappings.items():
        if var_name in variables and variables[var_name] and event_name not in anchors:
            anchors[event_name] = str(variables[var_name])

    return anchors


@router.post("/render", response_model=TemplateRenderResponse)
def render_template(
    payload: TemplateRenderRequest,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    authorize(persona, "template", Action.EXECUTE)
    template_dir = TEMPLATE_ROOT / payload.template_id
    template_file = template_dir / "template.md"
    meta_file = template_dir / "meta.json"

    if not template_file.exists():
        raise HTTPException(status_code=404, detail="template_not_found")

    # Load template metadata
    template_meta: dict = {}
    jurisdiction: str | None = None
    if meta_file.exists():
        try:
            template_meta = json.loads(meta_file.read_text())
            jurisdiction = template_meta.get("jurisdiction")
        except json.JSONDecodeError:
            pass

    content = template_file.read_text()
    for var, value in payload.variables.items():
        content = content.replace(f"{{{{ {var} }}}}", str(value))

    # Extract deadline anchors
    deadline_anchors = _extract_deadline_anchors(payload.template_id, payload.variables)

    document_id: str | None = None

    # Persist document if requested
    if payload.persist and payload.project_id:
        document_id = str(uuid4())
        content_hash = sha256_hex({"content": content, "variables": payload.variables})

        # Build metadata including deadline anchors and tracked fields
        doc_metadata = {
            "template_id": payload.template_id,
            "template_version": template_meta.get("version", "1.0.0"),
            "locale": payload.locale,
            "jurisdiction": jurisdiction,
            "variables": payload.variables,
            "deadline_anchors": deadline_anchors,
            "project_id": payload.project_id,
            "parcel_id": payload.parcel_id,
        }

        doc = models.Document(
            id=document_id,
            doc_type=payload.template_id,
            template_id=payload.template_id,
            version=template_meta.get("version", "1.0.0"),
            sha256=content_hash,
            storage_path=f"rendered/{document_id}.md",  # Placeholder path
            privilege=template_meta.get("privilege", "non_privileged"),
            metadata_json=doc_metadata,
            created_by=getattr(user, "id", None),
        )
        db.add(doc)

        # Audit event
        db.add(
            models.AuditEvent(
                id=str(uuid4()),
                user_id=getattr(user, "id", None),
                actor_persona=persona,
                action="template.render",
                resource="document",
                payload={
                    "document_id": document_id,
                    "template_id": payload.template_id,
                    "project_id": payload.project_id,
                    "parcel_id": payload.parcel_id,
                    "deadline_anchors": deadline_anchors,
                },
                hash=sha256_hex({
                    "document_id": document_id,
                    "template_id": payload.template_id,
                    "content_hash": content_hash,
                }),
            )
        )
        db.commit()

    return TemplateRenderResponse(
        rendered=content,
        document_id=document_id,
        deadline_anchors=deadline_anchors if deadline_anchors else None,
    )
