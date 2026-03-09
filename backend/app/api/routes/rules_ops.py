"""API routes for Requirements Operations.

Provides endpoints for:
- State pack import and validation
- Version management and diffing
- Publishing and rollback
- Regulatory update monitoring
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel

from app.api.deps import get_current_persona
from app.db.models import Persona
from app.security.rbac import authorize, Action

router = APIRouter(prefix="/rules", tags=["rules-ops"])


# Request/Response models
class ImportPackRequest(BaseModel):
    """Request to import a state pack."""
    jurisdiction: str
    yaml_content: str
    citations: Optional[list[dict[str, Any]]] = None
    metadata: Optional[dict[str, Any]] = None


class ImportPackResponse(BaseModel):
    """Response from pack import."""
    pack_id: str
    jurisdiction: str
    version: str
    status: str
    requirements_count: int
    staging_path: str


class ValidationResult(BaseModel):
    """Pack validation result."""
    valid: bool
    errors: list[str]
    warnings: list[str]
    requirements_count: int
    topics_covered: list[str]


class PackDiffResponse(BaseModel):
    """Diff between two pack versions."""
    from_version: str
    to_version: str
    added_count: int
    removed_count: int
    modified_count: int
    summary: str
    details: dict[str, Any]


class PublishRequest(BaseModel):
    """Request to publish a pack."""
    pack_id: str
    effective_date: Optional[datetime] = None


@router.post("/import_state_pack", response_model=ImportPackResponse)
async def import_state_pack(
    request: ImportPackRequest,
    persona: Persona = Depends(get_current_persona),
):
    """Import a state requirement pack from YAML.
    
    The pack is staged for validation before publishing.
    Only counsel can import packs.
    """
    authorize(persona, "rules", Action.WRITE)
    
    try:
        from app.services.requirements_ops import RequirementsOpsService
        
        service = RequirementsOpsService()
        result = service.import_state_pack(
            jurisdiction=request.jurisdiction,
            yaml_content=request.yaml_content,
            citations=request.citations,
            metadata=request.metadata,
        )
        
        pack = result["pack"]
        return ImportPackResponse(
            pack_id=pack["id"],
            jurisdiction=pack["jurisdiction"],
            version=pack["version"],
            status=pack["status"],
            requirements_count=pack["requirements_count"],
            staging_path=result["staging_path"],
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/validate_pack", response_model=ValidationResult)
async def validate_pack(
    pack_id: str,
    persona: Persona = Depends(get_current_persona),
):
    """Validate a staged pack for schema and consistency.
    
    Returns errors and warnings that must be addressed
    before publishing.
    """
    authorize(persona, "rules", Action.READ)
    
    try:
        from app.services.requirements_ops import RequirementsOpsService
        
        service = RequirementsOpsService()
        result = service.validate_pack(pack_id)
        
        return ValidationResult(
            valid=result.valid,
            errors=result.errors,
            warnings=result.warnings,
            requirements_count=result.requirements_count,
            topics_covered=result.topics_covered,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/state/{state}/diff", response_model=PackDiffResponse)
async def diff_packs(
    state: str,
    from_version: str = Query(..., alias="from"),
    to_version: str = Query(..., alias="to"),
    persona: Persona = Depends(get_current_persona),
):
    """Show differences between two pack versions.
    
    Useful for reviewing changes before publishing
    or understanding what changed between versions.
    """
    authorize(persona, "rules", Action.READ)
    
    try:
        from app.services.requirements_ops import RequirementsOpsService
        
        service = RequirementsOpsService()
        diff = service.diff_packs(from_version, to_version)
        
        return PackDiffResponse(
            from_version=diff.from_version,
            to_version=diff.to_version,
            added_count=len(diff.added),
            removed_count=len(diff.removed),
            modified_count=len(diff.modified),
            summary=diff.summary,
            details={
                "added": diff.added,
                "removed": diff.removed,
                "modified": diff.modified,
            },
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/publish")
async def publish_pack(
    request: PublishRequest,
    persona: Persona = Depends(get_current_persona),
):
    """Publish a validated pack to active status.
    
    The previous active version is archived.
    Only counsel can publish packs.
    """
    authorize(persona, "rules", Action.APPROVE)
    
    try:
        from app.services.requirements_ops import RequirementsOpsService
        
        service = RequirementsOpsService()
        result = service.publish_pack(
            pack_id=request.pack_id,
            user_id=str(persona),
            effective_date=request.effective_date,
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/state/{state}")
async def get_active_pack(
    state: str,
    persona: Persona = Depends(get_current_persona),
):
    """Get the currently active pack for a state."""
    authorize(persona, "rules", Action.READ)
    
    from app.services.requirements_ops import RequirementsOpsService
    
    service = RequirementsOpsService()
    pack = service.get_active_pack(state)
    
    if not pack:
        raise HTTPException(
            status_code=404,
            detail=f"No active pack found for state: {state}"
        )
    
    return pack


@router.get("/jurisdictions")
async def list_jurisdictions(
    persona: Persona = Depends(get_current_persona),
):
    """List all jurisdictions with active packs."""
    authorize(persona, "rules", Action.READ)
    
    from app.services.requirements_ops import RequirementsOpsService
    
    service = RequirementsOpsService()
    return service.list_jurisdictions()


@router.post("/check_updates")
async def check_regulatory_updates(
    jurisdiction: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
):
    """Check for regulatory updates (stub).
    
    In production, this would query legal databases
    and legislature feeds for changes.
    """
    authorize(persona, "rules", Action.READ)
    
    from app.services.requirements_ops import check_regulatory_updates
    
    updates = await check_regulatory_updates(jurisdiction)
    
    return {
        "checked_at": datetime.utcnow().isoformat(),
        "jurisdiction": jurisdiction or "all",
        "updates_found": len(updates),
        "updates": updates,
    }


@router.get("/requirements/{state}")
async def get_state_requirements(
    state: str,
    topic: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
):
    """Get normalized requirements for a state.
    
    Returns requirements in canonical schema format
    for use by compliance engine.
    """
    authorize(persona, "rules", Action.READ)
    
    from app.services.requirements_ops import RequirementsOpsService
    
    service = RequirementsOpsService()
    pack = service.get_active_pack(state)
    
    if not pack:
        raise HTTPException(
            status_code=404,
            detail=f"No active pack found for state: {state}"
        )
    
    # Re-normalize to get requirements
    requirements = service._normalize_pack_to_requirements(
        pack["content"], state
    )
    
    if topic:
        requirements = [r for r in requirements if r.topic == topic]
    
    return {
        "state": state.upper(),
        "version": pack["version"],
        "requirements_count": len(requirements),
        "requirements": [r.to_dict() for r in requirements],
    }
