"""Settlement Prediction API Endpoints.

Provides REST API for settlement predictions using both rules-based
and ML-based prediction models.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime

from app.services.prediction_service import (
    PredictionInput,
    PropertyType,
    ProjectType,
    predict_settlement,
    compute_risk_profile,
)
from app.services.ml_prediction import (
    predict_settlement_hybrid,
    get_ml_config,
    update_ml_config,
    check_ml_health,
    engineer_features,
    calculate_model_accuracy,
    MLPredictionResult,
)

router = APIRouter(prefix="/predictions", tags=["Predictions"])


# =============================================================================
# Request/Response Models
# =============================================================================

class PredictionRequest(BaseModel):
    """Request for settlement prediction."""
    jurisdiction: str = Field(..., description="State jurisdiction code (e.g., TX, CA)")
    assessed_value: float = Field(..., gt=0, description="Property assessed value")
    property_type: str = Field(default="residential_single", description="Property type")
    project_type: str = Field(default="utility", description="Infrastructure project type")
    
    # Property characteristics
    owner_occupied: bool = Field(default=False)
    principal_residence: bool = Field(default=False)
    family_ownership_years: int = Field(default=0, ge=0)
    
    # Acquisition details
    partial_taking: bool = Field(default=False)
    severance_impact: float = Field(default=0.0, ge=0, description="Impact on remainder")
    access_impact: bool = Field(default=False)
    business_on_property: bool = Field(default=False)
    
    # Dispute indicators
    owner_has_attorney: bool = Field(default=False)
    previous_counter_offer: bool = Field(default=False)
    counter_offer_amount: Optional[float] = Field(default=None, ge=0)
    owner_contested_appraisal: bool = Field(default=False)
    
    # Model selection
    force_ml: bool = Field(default=False, description="Force ML model (if available)")
    force_rules: bool = Field(default=False, description="Force rules-based model")


class SettlementRangeResponse(BaseModel):
    """Settlement range in the response."""
    low: float
    expected: float
    high: float


class TimelineResponse(BaseModel):
    """Timeline estimates in the response."""
    expected_days: int
    min_days: int
    max_days: int


class RiskResponse(BaseModel):
    """Risk metrics in the response."""
    litigation_probability: float
    dispute_level: str
    risk_factors: list[str]


class RecommendationsResponse(BaseModel):
    """Recommendations in the response."""
    initial_offer: float
    ceiling: float
    strategy: str


class PredictionResponse(BaseModel):
    """Full prediction response."""
    settlement_range: SettlementRangeResponse
    confidence: float
    timeline: TimelineResponse
    risk: RiskResponse
    recommendations: RecommendationsResponse
    factors: list[str]
    model_version: str
    model_used: str
    ml_available: bool
    generated_at: str


class RiskProfileResponse(BaseModel):
    """Risk profile response."""
    overall_risk: float
    risk_level: str
    factors: list[dict[str, Any]]
    recommendations: list[str]
    litigation_indicators: list[str]


class MLConfigResponse(BaseModel):
    """ML configuration response."""
    model_id: str
    endpoint_id: str
    enabled: bool
    ab_test_percentage: float
    min_training_samples: int


class MLConfigUpdate(BaseModel):
    """ML configuration update request."""
    enabled: Optional[bool] = None
    endpoint_id: Optional[str] = None
    ab_test_percentage: Optional[float] = Field(None, ge=0, le=1)


class ModelAccuracyResponse(BaseModel):
    """Model accuracy metrics response."""
    model_type: str
    window_days: int
    predictions_evaluated: int
    mean_absolute_error: Optional[float]
    mean_percentage_error: Optional[float]
    within_10_percent: Optional[float]
    within_20_percent: Optional[float]


# =============================================================================
# Helper Functions
# =============================================================================

def convert_request_to_input(req: PredictionRequest) -> PredictionInput:
    """Convert API request to prediction input."""
    # Map string property type to enum
    try:
        property_type = PropertyType(req.property_type)
    except ValueError:
        property_type = PropertyType.RESIDENTIAL_SINGLE
    
    # Map string project type to enum
    try:
        project_type = ProjectType(req.project_type)
    except ValueError:
        project_type = ProjectType.UTILITY
    
    return PredictionInput(
        jurisdiction=req.jurisdiction.upper(),
        assessed_value=req.assessed_value,
        property_type=property_type,
        project_type=project_type,
        owner_occupied=req.owner_occupied,
        principal_residence=req.principal_residence,
        family_ownership_years=req.family_ownership_years,
        partial_taking=req.partial_taking,
        severance_impact=req.severance_impact,
        access_impact=req.access_impact,
        business_on_property=req.business_on_property,
        owner_has_attorney=req.owner_has_attorney,
        previous_counter_offer=req.previous_counter_offer,
        counter_offer_amount=req.counter_offer_amount,
        owner_contested_appraisal=req.owner_contested_appraisal,
    )


# =============================================================================
# Prediction Endpoints
# =============================================================================

@router.post("/predict", response_model=PredictionResponse)
async def make_prediction(request: PredictionRequest) -> PredictionResponse:
    """Generate settlement prediction.
    
    Uses ML model if available and enabled, otherwise falls back
    to rules-based prediction.
    """
    inp = convert_request_to_input(request)
    
    # Get hybrid prediction (ML or rules)
    result: MLPredictionResult = await predict_settlement_hybrid(
        inp,
        force_ml=request.force_ml,
        force_rules=request.force_rules,
    )
    
    prediction = result.prediction
    
    return PredictionResponse(
        settlement_range=SettlementRangeResponse(
            low=prediction.low_settlement,
            expected=prediction.expected_settlement,
            high=prediction.high_settlement,
        ),
        confidence=prediction.confidence,
        timeline=TimelineResponse(
            expected_days=prediction.expected_days_to_settlement,
            min_days=prediction.min_days,
            max_days=prediction.max_days,
        ),
        risk=RiskResponse(
            litigation_probability=prediction.litigation_probability,
            dispute_level=prediction.dispute_level.value,
            risk_factors=prediction.risk_factors,
        ),
        recommendations=RecommendationsResponse(
            initial_offer=prediction.recommended_initial_offer,
            ceiling=prediction.recommended_ceiling,
            strategy=prediction.negotiation_strategy,
        ),
        factors=prediction.factors,
        model_version=prediction.model_version,
        model_used=result.model_used,
        ml_available=result.ml_available,
        generated_at=prediction.generated_at.isoformat(),
    )


@router.post("/predict/rules", response_model=PredictionResponse)
async def make_rules_prediction(request: PredictionRequest) -> PredictionResponse:
    """Generate settlement prediction using rules-based model only.
    
    Always uses the rules-based model regardless of ML configuration.
    """
    request.force_rules = True
    return await make_prediction(request)


@router.post("/risk-profile", response_model=RiskProfileResponse)
async def get_risk_profile(request: PredictionRequest) -> RiskProfileResponse:
    """Generate detailed risk profile for a case.
    
    Provides comprehensive risk analysis with factors, recommendations,
    and litigation indicators.
    """
    inp = convert_request_to_input(request)
    
    # Get prediction first
    result = await predict_settlement_hybrid(inp, force_rules=True)
    prediction = result.prediction
    
    # Compute risk profile
    risk_profile = compute_risk_profile(inp, prediction)
    
    return RiskProfileResponse(
        overall_risk=risk_profile.overall_risk,
        risk_level=risk_profile.risk_level,
        factors=risk_profile.factors,
        recommendations=risk_profile.recommendations,
        litigation_indicators=risk_profile.litigation_indicators,
    )


@router.post("/features")
async def get_prediction_features(request: PredictionRequest) -> dict[str, Any]:
    """Get engineered features for a prediction.
    
    Useful for debugging and understanding model inputs.
    Returns the feature vector that would be sent to ML model.
    """
    inp = convert_request_to_input(request)
    features = engineer_features(inp)
    return {
        "features": features,
        "feature_count": len(features),
    }


# =============================================================================
# ML Configuration Endpoints
# =============================================================================

@router.get("/ml/config", response_model=MLConfigResponse)
async def get_ml_configuration() -> MLConfigResponse:
    """Get current ML model configuration."""
    config = get_ml_config()
    return MLConfigResponse(**config)


@router.put("/ml/config", response_model=MLConfigResponse)
async def update_ml_configuration(update: MLConfigUpdate) -> MLConfigResponse:
    """Update ML model configuration.
    
    Requires admin permissions in production.
    """
    update_ml_config(
        enabled=update.enabled,
        endpoint_id=update.endpoint_id,
        ab_test_percentage=update.ab_test_percentage,
    )
    config = get_ml_config()
    return MLConfigResponse(**config)


@router.get("/ml/health")
async def check_ml_service_health() -> dict[str, Any]:
    """Check health of ML prediction service.
    
    Returns status of Vertex AI endpoint connectivity.
    """
    return await check_ml_health()


@router.get("/ml/accuracy", response_model=ModelAccuracyResponse)
async def get_model_accuracy(
    model_type: str = Query(default="rules", description="Model type: 'rules' or 'ml'"),
    window_days: int = Query(default=90, ge=7, le=365, description="Days to analyze"),
) -> ModelAccuracyResponse:
    """Get model accuracy metrics.
    
    Calculates accuracy based on predictions with known outcomes.
    """
    metrics = await calculate_model_accuracy(model_type, window_days)
    return ModelAccuracyResponse(**metrics)


# =============================================================================
# Batch Prediction Endpoints
# =============================================================================

class BatchPredictionRequest(BaseModel):
    """Request for batch predictions."""
    predictions: list[PredictionRequest]


class BatchPredictionResponse(BaseModel):
    """Response for batch predictions."""
    predictions: list[PredictionResponse]
    total: int
    processing_time_ms: float


@router.post("/predict/batch", response_model=BatchPredictionResponse)
async def make_batch_predictions(request: BatchPredictionRequest) -> BatchPredictionResponse:
    """Generate predictions for multiple cases.
    
    Limited to 50 predictions per request.
    """
    if len(request.predictions) > 50:
        raise HTTPException(
            status_code=400,
            detail="Maximum 50 predictions per batch request"
        )
    
    import time
    start = time.time()
    
    results = []
    for pred_request in request.predictions:
        result = await make_prediction(pred_request)
        results.append(result)
    
    elapsed = (time.time() - start) * 1000
    
    return BatchPredictionResponse(
        predictions=results,
        total=len(results),
        processing_time_ms=round(elapsed, 2),
    )


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health")
async def predictions_health() -> dict[str, Any]:
    """Health check for predictions service."""
    ml_health = await check_ml_health()
    
    return {
        "status": "healthy",
        "rules_engine": "available",
        "ml_engine": ml_health,
        "timestamp": datetime.utcnow().isoformat(),
    }
