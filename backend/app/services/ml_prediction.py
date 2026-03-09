"""ML-Based Settlement Prediction Service.

Uses Vertex AI for machine learning-based settlement predictions
when historical data is available, falling back to rules-based
predictions otherwise.

Features:
- Vertex AI AutoML model integration
- Feature engineering from case data
- Model training pipeline (batch mode)
- Prediction with confidence intervals
- A/B testing between ML and rules-based predictions
"""

from __future__ import annotations

import logging
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import random

from app.core.config import get_settings
from app.services.prediction_service import (
    PredictionInput,
    SettlementPrediction,
    DisputeLevel,
    predict_settlement as rules_predict_settlement,
)

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# ML Model Configuration
# =============================================================================

@dataclass
class MLModelConfig:
    """Configuration for ML model."""
    model_id: str = "settlement_predictor_v1"
    endpoint_id: str = ""
    project_id: str = ""
    location: str = "us-central1"
    enabled: bool = False
    ab_test_percentage: float = 0.0  # Percentage of predictions to use ML
    min_training_samples: int = 100
    retrain_threshold_days: int = 30


# Global model config (can be updated from settings/DB)
_ml_config = MLModelConfig(
    project_id=settings.gcp_project,
    location=settings.gemini_location,
)


# =============================================================================
# Feature Engineering
# =============================================================================

CATEGORICAL_FEATURES = [
    "jurisdiction",
    "property_type",
    "project_type",
]

NUMERICAL_FEATURES = [
    "assessed_value",
    "family_ownership_years",
    "severance_impact",
]

BOOLEAN_FEATURES = [
    "owner_occupied",
    "principal_residence",
    "partial_taking",
    "access_impact",
    "business_on_property",
    "owner_has_attorney",
    "previous_counter_offer",
    "owner_contested_appraisal",
]


def engineer_features(inp: PredictionInput) -> dict[str, Any]:
    """Convert prediction input to ML model features.
    
    Returns:
        Dictionary of features for ML model input
    """
    features = {}
    
    # Categorical features (one-hot encoded or label encoded)
    features["jurisdiction"] = inp.jurisdiction
    features["property_type"] = inp.property_type.value
    features["project_type"] = inp.project_type.value
    
    # Numerical features
    features["assessed_value"] = inp.assessed_value
    features["log_assessed_value"] = _safe_log(inp.assessed_value)
    features["family_ownership_years"] = inp.family_ownership_years
    features["severance_impact"] = inp.severance_impact
    
    # Boolean features (as 0/1)
    features["owner_occupied"] = 1 if inp.owner_occupied else 0
    features["principal_residence"] = 1 if inp.principal_residence else 0
    features["partial_taking"] = 1 if inp.partial_taking else 0
    features["access_impact"] = 1 if inp.access_impact else 0
    features["business_on_property"] = 1 if inp.business_on_property else 0
    features["owner_has_attorney"] = 1 if inp.owner_has_attorney else 0
    features["previous_counter_offer"] = 1 if inp.previous_counter_offer else 0
    features["owner_contested_appraisal"] = 1 if inp.owner_contested_appraisal else 0
    
    # Derived features
    features["counter_offer_ratio"] = 0.0
    if inp.previous_counter_offer and inp.counter_offer_amount and inp.assessed_value > 0:
        features["counter_offer_ratio"] = inp.counter_offer_amount / inp.assessed_value
    
    # Risk indicator count
    features["dispute_indicator_count"] = sum([
        features["owner_has_attorney"],
        features["previous_counter_offer"],
        features["owner_contested_appraisal"],
        features["partial_taking"],
        features["business_on_property"],
    ])
    
    return features


def _safe_log(value: float) -> float:
    """Safe log transformation."""
    import math
    if value <= 0:
        return 0
    return math.log(value + 1)


# =============================================================================
# Vertex AI Integration
# =============================================================================

def get_vertex_ai_endpoint():
    """Get Vertex AI endpoint for prediction.
    
    Returns:
        Endpoint object or None if not configured
    """
    if not _ml_config.enabled or not _ml_config.endpoint_id:
        return None
    
    try:
        from google.cloud import aiplatform
        
        aiplatform.init(
            project=_ml_config.project_id,
            location=_ml_config.location,
        )
        
        endpoint = aiplatform.Endpoint(_ml_config.endpoint_id)
        return endpoint
    except Exception as e:
        logger.warning(f"Failed to get Vertex AI endpoint: {e}")
        return None


async def predict_with_vertex_ai(features: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Make prediction using Vertex AI model.
    
    Args:
        features: Engineered features for prediction
        
    Returns:
        Prediction result or None if failed
    """
    endpoint = get_vertex_ai_endpoint()
    if not endpoint:
        return None
    
    try:
        # Format features for Vertex AI
        instances = [features]
        
        # Call prediction
        response = endpoint.predict(instances=instances)
        
        # Parse response
        if response.predictions:
            prediction = response.predictions[0]
            return {
                "settlement_low": prediction.get("settlement_low", 0),
                "settlement_expected": prediction.get("settlement_expected", 0),
                "settlement_high": prediction.get("settlement_high", 0),
                "confidence": prediction.get("confidence", 0.5),
                "litigation_probability": prediction.get("litigation_probability", 0.2),
            }
    except Exception as e:
        logger.error(f"Vertex AI prediction failed: {e}")
    
    return None


# =============================================================================
# Training Data Management
# =============================================================================

@dataclass
class TrainingRecord:
    """A single training record from historical data."""
    features: dict[str, Any]
    actual_settlement: float
    days_to_settlement: int
    went_to_litigation: bool
    case_id: str
    closed_date: datetime


async def get_training_data(
    jurisdiction: Optional[str] = None,
    min_records: int = 100,
) -> list[TrainingRecord]:
    """Fetch training data from historical case outcomes.
    
    Args:
        jurisdiction: Filter by jurisdiction (optional)
        min_records: Minimum records required
        
    Returns:
        List of training records
    """
    # TODO: Implement actual data fetching from database
    # This would query closed cases with known outcomes
    
    # For now, return empty list (rules-based will be used)
    logger.info(f"Training data query: jurisdiction={jurisdiction}, min_records={min_records}")
    return []


async def prepare_training_dataset(records: list[TrainingRecord]) -> dict[str, Any]:
    """Prepare dataset for Vertex AI training.
    
    Args:
        records: Training records
        
    Returns:
        Dataset configuration for Vertex AI
    """
    if len(records) < _ml_config.min_training_samples:
        raise ValueError(f"Insufficient training data: {len(records)} < {_ml_config.min_training_samples}")
    
    # Convert to training format
    training_data = []
    for record in records:
        row = {
            **record.features,
            "label_settlement": record.actual_settlement,
            "label_days": record.days_to_settlement,
            "label_litigation": 1 if record.went_to_litigation else 0,
        }
        training_data.append(row)
    
    return {
        "records": training_data,
        "feature_columns": list(CATEGORICAL_FEATURES + NUMERICAL_FEATURES + BOOLEAN_FEATURES),
        "label_columns": ["label_settlement", "label_days", "label_litigation"],
    }


async def train_model(dataset: dict[str, Any]) -> str:
    """Train a new model using Vertex AI AutoML.
    
    Args:
        dataset: Prepared training dataset
        
    Returns:
        Model ID of the trained model
    """
    if not _ml_config.project_id:
        raise ValueError("GCP project not configured")
    
    try:
        from google.cloud import aiplatform
        
        aiplatform.init(
            project=_ml_config.project_id,
            location=_ml_config.location,
        )
        
        # Create dataset
        tabular_dataset = aiplatform.TabularDataset.create(
            display_name=f"settlement_prediction_{datetime.utcnow().strftime('%Y%m%d')}",
            gcs_source=None,  # Would be GCS path with actual data
        )
        
        # Start training job
        job = aiplatform.AutoMLTabularTrainingJob(
            display_name=f"settlement_training_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            optimization_prediction_type="regression",
            optimization_objective="minimize-rmse",
        )
        
        model = job.run(
            dataset=tabular_dataset,
            target_column="label_settlement",
            training_fraction_split=0.8,
            validation_fraction_split=0.1,
            test_fraction_split=0.1,
        )
        
        logger.info(f"Model trained: {model.resource_name}")
        return model.resource_name
        
    except Exception as e:
        logger.error(f"Model training failed: {e}")
        raise


# =============================================================================
# Hybrid Prediction Service
# =============================================================================

@dataclass
class MLPredictionResult:
    """Result from ML prediction with metadata."""
    prediction: SettlementPrediction
    model_used: str  # "ml" or "rules"
    ml_available: bool
    ab_test_selected: Optional[str] = None


async def predict_settlement_hybrid(
    inp: PredictionInput,
    force_ml: bool = False,
    force_rules: bool = False,
) -> MLPredictionResult:
    """Make prediction using ML model if available, otherwise rules.
    
    Implements A/B testing between ML and rules-based predictions.
    
    Args:
        inp: Prediction input
        force_ml: Force ML prediction (for testing)
        force_rules: Force rules-based prediction
        
    Returns:
        MLPredictionResult with prediction and metadata
    """
    # Check if we should use ML
    use_ml = False
    ab_selected = None
    
    if force_rules:
        use_ml = False
    elif force_ml:
        use_ml = True
    elif _ml_config.enabled and _ml_config.ab_test_percentage > 0:
        # A/B test selection
        if random.random() < _ml_config.ab_test_percentage:
            ab_selected = "ml"
            use_ml = True
        else:
            ab_selected = "rules"
    
    # Attempt ML prediction
    if use_ml:
        features = engineer_features(inp)
        ml_result = await predict_with_vertex_ai(features)
        
        if ml_result:
            # Convert ML result to SettlementPrediction
            # For now, use rules-based for factors and strategy
            rules_pred = rules_predict_settlement(inp)
            
            prediction = SettlementPrediction(
                low_settlement=ml_result["settlement_low"],
                expected_settlement=ml_result["settlement_expected"],
                high_settlement=ml_result["settlement_high"],
                confidence=ml_result["confidence"],
                expected_days_to_settlement=rules_pred.expected_days_to_settlement,
                min_days=rules_pred.min_days,
                max_days=rules_pred.max_days,
                litigation_probability=ml_result["litigation_probability"],
                dispute_level=rules_pred.dispute_level,
                factors=rules_pred.factors,
                risk_factors=rules_pred.risk_factors,
                recommended_initial_offer=ml_result["settlement_expected"] * 0.85,
                recommended_ceiling=ml_result["settlement_high"],
                negotiation_strategy=rules_pred.negotiation_strategy,
                model_version="ml_v1.0",
            )
            
            return MLPredictionResult(
                prediction=prediction,
                model_used="ml",
                ml_available=True,
                ab_test_selected=ab_selected,
            )
    
    # Fall back to rules-based
    prediction = rules_predict_settlement(inp)
    
    return MLPredictionResult(
        prediction=prediction,
        model_used="rules",
        ml_available=_ml_config.enabled,
        ab_test_selected=ab_selected,
    )


# =============================================================================
# Model Management API
# =============================================================================

def get_ml_config() -> dict[str, Any]:
    """Get current ML configuration."""
    return {
        "model_id": _ml_config.model_id,
        "endpoint_id": _ml_config.endpoint_id,
        "enabled": _ml_config.enabled,
        "ab_test_percentage": _ml_config.ab_test_percentage,
        "min_training_samples": _ml_config.min_training_samples,
    }


def update_ml_config(
    enabled: Optional[bool] = None,
    endpoint_id: Optional[str] = None,
    ab_test_percentage: Optional[float] = None,
):
    """Update ML configuration.
    
    Args:
        enabled: Enable/disable ML predictions
        endpoint_id: Vertex AI endpoint ID
        ab_test_percentage: Percentage for A/B testing (0-1)
    """
    global _ml_config
    
    if enabled is not None:
        _ml_config.enabled = enabled
    if endpoint_id is not None:
        _ml_config.endpoint_id = endpoint_id
    if ab_test_percentage is not None:
        _ml_config.ab_test_percentage = max(0, min(1, ab_test_percentage))
    
    logger.info(f"ML config updated: enabled={_ml_config.enabled}, endpoint={_ml_config.endpoint_id}")


async def check_ml_health() -> dict[str, Any]:
    """Check health of ML prediction service.
    
    Returns:
        Health status dictionary
    """
    status = {
        "enabled": _ml_config.enabled,
        "endpoint_configured": bool(_ml_config.endpoint_id),
        "endpoint_reachable": False,
        "model_version": _ml_config.model_id,
    }
    
    if _ml_config.enabled and _ml_config.endpoint_id:
        endpoint = get_vertex_ai_endpoint()
        status["endpoint_reachable"] = endpoint is not None
    
    return status


# =============================================================================
# Prediction Comparison and Learning Loop
# =============================================================================

@dataclass
class PredictionOutcome:
    """Tracks prediction outcome for model improvement."""
    prediction_id: str
    input_features: dict[str, Any]
    predicted_settlement: float
    actual_settlement: Optional[float] = None
    model_used: str = "rules"
    prediction_date: datetime = field(default_factory=datetime.utcnow)
    outcome_date: Optional[datetime] = None


async def record_prediction_outcome(
    prediction_id: str,
    actual_settlement: float,
    outcome_date: datetime,
):
    """Record actual outcome for a prediction to improve models.
    
    This data is used for:
    1. Model accuracy tracking
    2. Retraining decisions
    3. A/B test analysis
    
    Args:
        prediction_id: ID of original prediction
        actual_settlement: Actual settlement amount
        outcome_date: Date case was settled
    """
    # TODO: Store in database for model improvement
    logger.info(f"Recorded outcome for prediction {prediction_id}: ${actual_settlement:,.2f}")


async def calculate_model_accuracy(
    model_type: str = "rules",
    window_days: int = 90,
) -> dict[str, Any]:
    """Calculate model accuracy metrics over a time window.
    
    Args:
        model_type: "rules" or "ml"
        window_days: Days to look back
        
    Returns:
        Accuracy metrics
    """
    # TODO: Query historical predictions with outcomes
    
    # Placeholder metrics
    return {
        "model_type": model_type,
        "window_days": window_days,
        "predictions_evaluated": 0,
        "mean_absolute_error": None,
        "mean_percentage_error": None,
        "within_10_percent": None,
        "within_20_percent": None,
    }
