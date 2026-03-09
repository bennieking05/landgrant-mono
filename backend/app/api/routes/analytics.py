"""Predictive Analytics API endpoints.

Provides settlement predictions, risk profiles, and negotiation recommendations
based on jurisdiction rules and property characteristics.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any
import logging

from app.services.prediction_service import (
    predict_settlement,
    compute_risk_profile,
    PredictionInput,
    PropertyType,
    ProjectType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Predictive Analytics"])


# =============================================================================
# Request/Response Models
# =============================================================================

class PredictSettlementRequest(BaseModel):
    """Request model for settlement prediction."""
    jurisdiction: str = Field(..., description="Two-letter state code (e.g., TX, CA)")
    assessed_value: float = Field(..., gt=0, description="Property assessed value")
    property_type: str = Field("residential_single", description="Property type")
    project_type: str = Field("utility", description="Infrastructure project type")
    
    # Property characteristics
    owner_occupied: bool = Field(False, description="Owner-occupied property")
    principal_residence: bool = Field(False, description="Principal residence")
    family_ownership_years: int = Field(0, ge=0, description="Years property held by family")
    
    # Acquisition details
    partial_taking: bool = Field(False, description="Partial taking (not full acquisition)")
    severance_impact: float = Field(0, ge=0, description="Estimated severance impact on remainder")
    access_impact: bool = Field(False, description="Taking affects property access")
    business_on_property: bool = Field(False, description="Business operations on property")
    
    # Dispute indicators
    owner_has_attorney: bool = Field(False, description="Owner has legal representation")
    previous_counter_offer: bool = Field(False, description="Owner made counter-offer")
    counter_offer_amount: Optional[float] = Field(None, description="Amount of owner's counter-offer")
    owner_contested_appraisal: bool = Field(False, description="Owner contested appraisal")


class SettlementRangeModel(BaseModel):
    """Settlement range in prediction response."""
    low: float
    expected: float
    high: float


class TimelineModel(BaseModel):
    """Timeline estimates in prediction response."""
    expected_days: int
    min_days: int
    max_days: int


class RiskModel(BaseModel):
    """Risk metrics in prediction response."""
    litigation_probability: float
    dispute_level: str
    risk_factors: list[str]


class RecommendationsModel(BaseModel):
    """Recommendations in prediction response."""
    initial_offer: float
    ceiling: float
    strategy: str


class PredictSettlementResponse(BaseModel):
    """Response model for settlement prediction."""
    settlement_range: SettlementRangeModel
    confidence: float
    timeline: TimelineModel
    risk: RiskModel
    recommendations: RecommendationsModel
    factors: list[str]
    model_version: str
    generated_at: str


class RiskFactorModel(BaseModel):
    """Individual risk factor."""
    name: str
    score: int
    description: str


class RiskProfileResponse(BaseModel):
    """Response model for risk profile."""
    case_id: Optional[str]
    parcel_id: Optional[str]
    overall_risk: float
    risk_level: str
    factors: list[RiskFactorModel]
    recommendations: list[str]
    litigation_indicators: list[str]


class CounterOfferRequest(BaseModel):
    """Request for optimal counter-offer suggestion."""
    jurisdiction: str
    assessed_value: float
    owner_counter_amount: float
    property_type: str = "residential_single"
    owner_has_attorney: bool = False
    dispute_level: Optional[str] = None


class CounterOfferResponse(BaseModel):
    """Response with counter-offer suggestion."""
    suggested_amount: float
    suggested_range_low: float
    suggested_range_high: float
    rationale: str
    next_steps: list[str]


# =============================================================================
# Prediction Endpoints
# =============================================================================

@router.post("/predict-settlement", response_model=PredictSettlementResponse)
async def predict_case_settlement(request: PredictSettlementRequest):
    """Predict settlement outcome for a case.
    
    Returns predicted settlement range, timeline, litigation probability,
    and negotiation recommendations based on jurisdiction rules and
    property characteristics.
    """
    try:
        # Convert request to PredictionInput
        inp = PredictionInput(
            jurisdiction=request.jurisdiction.upper(),
            assessed_value=request.assessed_value,
            property_type=PropertyType(request.property_type),
            project_type=ProjectType(request.project_type),
            owner_occupied=request.owner_occupied,
            principal_residence=request.principal_residence,
            family_ownership_years=request.family_ownership_years,
            partial_taking=request.partial_taking,
            severance_impact=request.severance_impact,
            access_impact=request.access_impact,
            business_on_property=request.business_on_property,
            owner_has_attorney=request.owner_has_attorney,
            previous_counter_offer=request.previous_counter_offer,
            counter_offer_amount=request.counter_offer_amount,
            owner_contested_appraisal=request.owner_contested_appraisal,
        )
        
        # Generate prediction
        prediction = predict_settlement(inp)
        
        return prediction.to_dict()
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Settlement prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/case/{case_id}/risk-profile", response_model=RiskProfileResponse)
async def get_case_risk_profile(
    case_id: str,
    parcel_id: Optional[str] = None,
):
    """Get risk profile for a specific case.
    
    Analyzes the case data and returns a detailed risk assessment
    with factors, indicators, and recommendations.
    """
    from app.db.session import SessionLocal
    from app.db import models
    
    db = SessionLocal()
    try:
        # Fetch project/case data
        project = db.query(models.Project).filter(models.Project.id == case_id).first()
        if not project:
            raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")
        
        # Fetch parcel if specified
        parcel = None
        if parcel_id:
            parcel = db.query(models.Parcel).filter(models.Parcel.id == parcel_id).first()
            if not parcel:
                raise HTTPException(status_code=404, detail=f"Parcel not found: {parcel_id}")
        
        # Analyze risk factors based on actual data
        factors = []
        indicators = []
        recommendations = []
        total_risk = 0
        
        # Check for offers with counters
        offers = db.query(models.Offer).filter(
            models.Offer.project_id == case_id,
            models.Offer.parcel_id == parcel_id if parcel_id else True,
        ).all()
        
        counter_offers = [o for o in offers if o.offer_type and "counter" in str(o.offer_type).lower()]
        if counter_offers:
            factors.append(RiskFactorModel(
                name="Counter-Offers",
                score=15,
                description=f"Owner has made {len(counter_offers)} counter-offer(s)",
            ))
            total_risk += 15
            indicators.append("Owner actively negotiating counter-offers")
        
        # Check for litigation
        lit_cases = db.query(models.LitigationCase).filter(
            models.LitigationCase.project_id == case_id,
            models.LitigationCase.parcel_id == parcel_id if parcel_id else True,
        ).all()
        
        if lit_cases:
            factors.append(RiskFactorModel(
                name="Active Litigation",
                score=30,
                description=f"{len(lit_cases)} active litigation case(s)",
            ))
            total_risk += 30
            indicators.append("Litigation has been filed")
            recommendations.append("Coordinate with outside counsel on litigation strategy")
        
        # Check risk score from parcel/project
        if parcel and parcel.risk_score:
            risk_contribution = min(parcel.risk_score // 3, 20)
            factors.append(RiskFactorModel(
                name="Parcel Risk Score",
                score=risk_contribution,
                description=f"Parcel risk score: {parcel.risk_score}/100",
            ))
            total_risk += risk_contribution
        elif project.risk_score:
            risk_contribution = min(project.risk_score // 3, 20)
            factors.append(RiskFactorModel(
                name="Project Risk Score",
                score=risk_contribution,
                description=f"Project risk score: {project.risk_score}/100",
            ))
            total_risk += risk_contribution
        
        # Check appraisals
        if parcel_id:
            appraisal = db.query(models.Appraisal).filter(
                models.Appraisal.parcel_id == parcel_id
            ).first()
            if not appraisal or not appraisal.completed_at:
                factors.append(RiskFactorModel(
                    name="Incomplete Appraisal",
                    score=10,
                    description="Appraisal not yet completed",
                ))
                total_risk += 10
                recommendations.append("Complete appraisal before proceeding with offer")
        
        # Add default recommendations if empty
        if not recommendations:
            recommendations = [
                "Document all landowner communications",
                "Ensure compliance with statutory notice requirements",
                "Maintain detailed negotiation records",
            ]
        
        # Determine risk level
        if total_risk >= 60:
            risk_level = "high"
        elif total_risk >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return RiskProfileResponse(
            case_id=case_id,
            parcel_id=parcel_id,
            overall_risk=float(total_risk),
            risk_level=risk_level,
            factors=factors if factors else [
                RiskFactorModel(name="Baseline", score=0, description="No specific risk factors identified")
            ],
            recommendations=recommendations,
            litigation_indicators=indicators,
        )
        
    finally:
        db.close()


@router.post("/suggest-counter-offer", response_model=CounterOfferResponse)
async def suggest_counter_offer(request: CounterOfferRequest):
    """Suggest optimal counter-offer response.
    
    Given an owner's counter-offer, suggests an appropriate response
    amount and negotiation approach.
    """
    try:
        # Calculate position
        assessed = request.assessed_value
        owner_counter = request.owner_counter_amount
        
        # Ratio of counter to assessed
        ratio = owner_counter / assessed if assessed > 0 else 1
        
        # Base response: move towards middle
        if ratio > 2.0:
            # Owner is far above - suggest modest increase
            suggested = assessed * 1.05  # 5% above assessed
            suggested_low = assessed * 1.0
            suggested_high = assessed * 1.10
            rationale = (
                f"Owner's counter at {ratio:.0%} of assessed is significantly above market. "
                "Recommend modest increase from initial position to show good faith while "
                "maintaining defensible position."
            )
            next_steps = [
                "Document basis for assessed value",
                "Request owner's appraisal or valuation basis",
                "Consider joint appraisal agreement",
                "Prepare comparable sales analysis",
            ]
        elif ratio > 1.5:
            # Owner is somewhat above
            suggested = assessed * 1.10
            suggested_low = assessed * 1.05
            suggested_high = assessed * 1.15
            rationale = (
                f"Owner's counter at {ratio:.0%} indicates room for negotiation. "
                "Suggest measured increase to demonstrate willingness to negotiate."
            )
            next_steps = [
                "Schedule face-to-face meeting if possible",
                "Identify specific valuation disagreements",
                "Consider mediation if gap persists",
            ]
        elif ratio > 1.2:
            # Reasonable negotiating range
            midpoint = (assessed + owner_counter) / 2
            suggested = midpoint
            suggested_low = assessed * 1.05
            suggested_high = owner_counter * 0.95
            rationale = (
                f"Owner's counter at {ratio:.0%} is within reasonable negotiating range. "
                "Settlement near midpoint is achievable."
            )
            next_steps = [
                "Consider splitting the difference",
                "Identify non-monetary terms that might bridge gap",
                "Document agreement timeline",
            ]
        else:
            # Owner is close to assessed
            suggested = owner_counter * 0.98
            suggested_low = assessed
            suggested_high = owner_counter
            rationale = (
                f"Owner's counter at {ratio:.0%} is very close to assessed value. "
                "Quick resolution is likely."
            )
            next_steps = [
                "Move quickly to acceptance",
                "Prepare closing documents",
                "Confirm timeline with owner",
            ]
        
        # Adjust for attorney involvement
        if request.owner_has_attorney:
            next_steps.insert(0, "Direct all communications through owner's counsel")
        
        return CounterOfferResponse(
            suggested_amount=round(suggested, 2),
            suggested_range_low=round(suggested_low, 2),
            suggested_range_high=round(suggested_high, 2),
            rationale=rationale,
            next_steps=next_steps,
        )
        
    except Exception as e:
        logger.error(f"Counter-offer suggestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Stats Endpoints
# =============================================================================

@router.get("/stats/jurisdiction/{jurisdiction}")
async def get_jurisdiction_stats(jurisdiction: str):
    """Get settlement statistics for a jurisdiction.
    
    Returns aggregated settlement data based on historical cases.
    (Currently returns mock data - real data from RAG in future)
    """
    jurisdiction = jurisdiction.upper()
    
    # Mock stats - would come from historical data in production
    return {
        "jurisdiction": jurisdiction,
        "total_cases": 150,
        "avg_settlement_ratio": 1.08,  # Ratio to assessed value
        "median_days_to_settlement": 95,
        "litigation_rate": 0.18,
        "settlement_by_property_type": {
            "residential": {"avg_ratio": 1.05, "count": 80},
            "commercial": {"avg_ratio": 1.12, "count": 45},
            "agricultural": {"avg_ratio": 1.02, "count": 25},
        },
        "notes": "Statistics based on historical case outcomes",
    }


@router.get("/property-types")
async def list_property_types():
    """List available property types for prediction."""
    return {
        "property_types": [
            {"value": pt.value, "name": pt.name.replace("_", " ").title()}
            for pt in PropertyType
        ]
    }


@router.get("/project-types")
async def list_project_types():
    """List available project types for prediction."""
    return {
        "project_types": [
            {"value": pt.value, "name": pt.name.replace("_", " ").title()}
            for pt in ProjectType
        ]
    }
