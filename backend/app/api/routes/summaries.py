"""API routes for State Summaries and Comparisons.

Provides endpoints for:
- Common-core requirements across states
- State clusters (quick-take, commissioners, etc.)
- State-specific deltas
- Markdown/JSON exports
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from typing import Optional, Any
from pydantic import BaseModel

from app.api.deps import get_current_persona
from app.db.models import Persona
from app.security.rbac import authorize, Action

router = APIRouter(prefix="/rules/summary", tags=["summaries"])


# Response models
class CommonCoreRequirementResponse(BaseModel):
    """A common-core requirement."""
    requirement_id: str
    description: str
    applies_to_all: bool
    coverage: str
    exceptions: list[str]
    category: str


class StateClusterResponse(BaseModel):
    """A cluster of similar states."""
    name: str
    description: str
    states: list[str]
    count: int


class StateDeltaResponse(BaseModel):
    """How a state differs from common core."""
    requirement_id: str
    common_core_value: Any
    state_value: Any
    category: str
    citation: Optional[str]


@router.get("/common")
async def get_common_core(
    persona: Persona = Depends(get_current_persona),
):
    """Get requirements common to all (or most) states.
    
    Returns the baseline requirements that apply
    across jurisdictions.
    """
    authorize(persona, "rules", Action.READ)
    
    from app.services.state_summary import StateSummaryService
    
    service = StateSummaryService()
    common = service.get_common_core()
    
    return {
        "count": len(common),
        "requirements": [
            CommonCoreRequirementResponse(
                requirement_id=r.requirement_id,
                description=r.description,
                applies_to_all=r.applies_to_all,
                coverage=f"{r.states_count}/{r.total_states}",
                exceptions=r.exceptions,
                category=r.category,
            )
            for r in common
        ],
    }


@router.get("/clusters")
async def get_state_clusters(
    persona: Persona = Depends(get_current_persona),
):
    """Get state clusters by characteristics.
    
    Groups states by common features like:
    - Quick-take availability
    - Commissioner panels
    - Enhanced compensation
    - Post-Kelo reforms
    """
    authorize(persona, "rules", Action.READ)
    
    from app.services.state_summary import StateSummaryService
    
    service = StateSummaryService()
    clusters = service.get_clusters()
    
    return {
        "count": len(clusters),
        "clusters": [
            StateClusterResponse(
                name=c.name,
                description=c.description,
                states=c.states,
                count=len(c.states),
            )
            for c in clusters
        ],
    }


@router.get("/state/{state}")
async def get_state_summary(
    state: str,
    persona: Persona = Depends(get_current_persona),
):
    """Get complete summary for a state.
    
    Includes key characteristics, cluster membership,
    and deltas from common core.
    """
    authorize(persona, "rules", Action.READ)
    
    from app.services.state_summary import StateSummaryService
    
    service = StateSummaryService()
    summary = service.get_state_summary(state)
    
    if "error" in summary:
        raise HTTPException(status_code=404, detail=summary["error"])
    
    return summary


@router.get("/state/{state}/deltas", response_model=list[StateDeltaResponse])
async def get_state_deltas(
    state: str,
    persona: Persona = Depends(get_current_persona),
):
    """Get deltas showing how a state differs.
    
    Lists specific requirements where the state
    differs from the common core or default.
    """
    authorize(persona, "rules", Action.READ)
    
    from app.services.state_summary import StateSummaryService
    
    service = StateSummaryService()
    deltas = service.get_state_delta(state)
    
    return [
        StateDeltaResponse(
            requirement_id=d.requirement_id,
            common_core_value=d.common_core_value,
            state_value=d.state_value,
            category=d.category,
            citation=d.citation,
        )
        for d in deltas
    ]


@router.get("/compare")
async def compare_states(
    states: str = Query(..., description="Comma-separated state codes"),
    persona: Persona = Depends(get_current_persona),
):
    """Compare multiple states side-by-side.
    
    Shows key characteristics for each state
    in a comparison format.
    """
    authorize(persona, "rules", Action.READ)
    
    from app.services.state_summary import StateSummaryService
    
    service = StateSummaryService()
    state_list = [s.strip().upper() for s in states.split(",")]
    
    comparison = {}
    for state in state_list:
        summary = service.get_state_summary(state)
        if "error" not in summary:
            comparison[state] = {
                "key_characteristics": summary.get("key_characteristics", {}),
                "clusters": summary.get("clusters", []),
            }
    
    return {
        "states": state_list,
        "comparison": comparison,
    }


@router.get("/export/markdown", response_class=PlainTextResponse)
async def export_markdown(
    persona: Persona = Depends(get_current_persona),
):
    """Export full comparison as Markdown.
    
    Generates a formatted document suitable
    for documentation or sharing.
    """
    authorize(persona, "rules", Action.READ)
    
    from app.services.state_summary import StateSummaryService
    
    service = StateSummaryService()
    markdown = service.export_markdown()
    
    return PlainTextResponse(
        content=markdown,
        media_type="text/markdown",
    )


@router.get("/export/json")
async def export_json(
    persona: Persona = Depends(get_current_persona),
):
    """Export full comparison as JSON.
    
    Complete data export for analysis
    or integration with other systems.
    """
    authorize(persona, "rules", Action.READ)
    
    from app.services.state_summary import StateSummaryService
    
    service = StateSummaryService()
    return service.export_json()


@router.get("/matrix")
async def get_comparison_matrix(
    characteristic: str = Query(..., description="Characteristic to compare"),
    persona: Persona = Depends(get_current_persona),
):
    """Get a matrix of states by characteristic.
    
    Supported characteristics:
    - quick_take
    - bill_of_rights
    - residence_multiplier
    - attorney_fees_automatic
    - economic_development_banned
    """
    authorize(persona, "rules", Action.READ)
    
    from app.services.state_summary import StateSummaryService
    
    service = StateSummaryService()
    
    # Map characteristic to path
    char_map = {
        "quick_take": ("initiation", "quick_take", "available"),
        "bill_of_rights": ("initiation", "landowner_bill_of_rights"),
        "residence_multiplier": ("compensation", "residence_multiplier"),
        "attorney_fees_automatic": ("compensation", "attorney_fees", "automatic"),
        "economic_development_banned": ("public_use", "economic_development_banned"),
    }
    
    if characteristic not in char_map:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown characteristic: {characteristic}. Supported: {list(char_map.keys())}"
        )
    
    path = char_map[characteristic]
    
    # Get all states and check characteristic
    states_with = []
    states_without = []
    
    for state, config in service._state_configs.items():
        # Navigate to value
        value = config
        for key in path:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                value = None
                break
        
        if value:
            states_with.append(state)
        else:
            states_without.append(state)
    
    return {
        "characteristic": characteristic,
        "states_with": sorted(states_with),
        "states_without": sorted(states_without),
        "count_with": len(states_with),
        "count_without": len(states_without),
    }
