"""Predictive Settlement Analytics Service.

Provides settlement predictions based on jurisdiction rules, property characteristics,
and historical case outcomes. Initially rules-based, designed to graduate to ML
when sufficient historical data is available.

Features:
- Settlement range prediction based on jurisdiction-specific rules
- Timeline estimation using deadline chain analysis
- Risk profiling for negotiation strategy
- Optimal counter-offer suggestions
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional
from enum import Enum

from app.core.config import get_settings
from app.services.rules_engine import (
    get_jurisdiction_config,
    get_compensation_multiplier,
    get_attorney_fee_rules,
    is_quick_take_available,
)

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# Prediction Models
# =============================================================================

class DisputeLevel(str, Enum):
    """Level of dispute in negotiation."""
    LOW = "low"  # Owner likely to accept reasonable offer
    MEDIUM = "medium"  # Some negotiation expected
    HIGH = "high"  # Significant disagreement, may go to litigation
    VERY_HIGH = "very_high"  # Almost certain litigation


class PropertyType(str, Enum):
    """Type of property being acquired."""
    RESIDENTIAL_SINGLE = "residential_single"
    RESIDENTIAL_MULTI = "residential_multi"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    AGRICULTURAL = "agricultural"
    VACANT_LAND = "vacant_land"
    MIXED_USE = "mixed_use"


class ProjectType(str, Enum):
    """Type of infrastructure project."""
    HIGHWAY = "highway"
    UTILITY = "utility"
    TRANSIT = "transit"
    PIPELINE = "pipeline"
    FLOOD_CONTROL = "flood_control"
    AIRPORT = "airport"
    URBAN_RENEWAL = "urban_renewal"
    OTHER = "other"


@dataclass
class SettlementPrediction:
    """Predicted settlement outcome."""
    # Range predictions
    low_settlement: float  # 25th percentile estimate
    expected_settlement: float  # Median estimate
    high_settlement: float  # 75th percentile estimate
    
    # Confidence
    confidence: float  # 0-1 confidence in prediction
    
    # Timeline predictions
    expected_days_to_settlement: int
    min_days: int
    max_days: int
    
    # Risk metrics
    litigation_probability: float  # 0-1
    dispute_level: DisputeLevel
    
    # Factors
    factors: list[str]
    risk_factors: list[str]
    
    # Recommendations
    recommended_initial_offer: float
    recommended_ceiling: float
    negotiation_strategy: str
    
    # Metadata
    model_version: str = "rules_v1.0"
    generated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "settlement_range": {
                "low": self.low_settlement,
                "expected": self.expected_settlement,
                "high": self.high_settlement,
            },
            "confidence": self.confidence,
            "timeline": {
                "expected_days": self.expected_days_to_settlement,
                "min_days": self.min_days,
                "max_days": self.max_days,
            },
            "risk": {
                "litigation_probability": self.litigation_probability,
                "dispute_level": self.dispute_level.value,
                "risk_factors": self.risk_factors,
            },
            "recommendations": {
                "initial_offer": self.recommended_initial_offer,
                "ceiling": self.recommended_ceiling,
                "strategy": self.negotiation_strategy,
            },
            "factors": self.factors,
            "model_version": self.model_version,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class RiskProfile:
    """Risk profile for a case."""
    overall_risk: float  # 0-100 score
    risk_level: str  # low, medium, high, critical
    factors: list[dict[str, Any]]
    recommendations: list[str]
    litigation_indicators: list[str]


@dataclass
class PredictionInput:
    """Input data for settlement prediction."""
    jurisdiction: str
    assessed_value: float
    property_type: PropertyType = PropertyType.RESIDENTIAL_SINGLE
    project_type: ProjectType = ProjectType.UTILITY
    
    # Property characteristics
    owner_occupied: bool = False
    principal_residence: bool = False
    family_ownership_years: int = 0
    
    # Acquisition details
    partial_taking: bool = False
    severance_impact: float = 0.0  # Estimated impact on remainder
    access_impact: bool = False  # Loss of access
    business_on_property: bool = False
    
    # Dispute indicators
    owner_has_attorney: bool = False
    previous_counter_offer: bool = False
    counter_offer_amount: Optional[float] = None
    owner_contested_appraisal: bool = False


# =============================================================================
# Rules-Based Prediction Engine
# =============================================================================

# Adjustment factors by property type
PROPERTY_TYPE_FACTORS = {
    PropertyType.RESIDENTIAL_SINGLE: 1.0,
    PropertyType.RESIDENTIAL_MULTI: 1.1,
    PropertyType.COMMERCIAL: 1.15,
    PropertyType.INDUSTRIAL: 1.2,
    PropertyType.AGRICULTURAL: 0.95,
    PropertyType.VACANT_LAND: 0.9,
    PropertyType.MIXED_USE: 1.15,
}

# Project type impact on settlement (inverse = owner leverage)
PROJECT_TYPE_URGENCY = {
    ProjectType.HIGHWAY: 0.95,  # High urgency, less owner leverage
    ProjectType.UTILITY: 1.0,
    ProjectType.TRANSIT: 0.97,
    ProjectType.PIPELINE: 1.05,  # Regulatory pressure, slight owner leverage
    ProjectType.FLOOD_CONTROL: 0.92,  # Public safety urgency
    ProjectType.AIRPORT: 1.1,  # Complex projects, more owner leverage
    ProjectType.URBAN_RENEWAL: 1.15,  # Historically contentious
    ProjectType.OTHER: 1.0,
}

# Dispute level indicators
DISPUTE_INDICATORS = {
    "owner_has_attorney": 0.15,
    "previous_counter_offer": 0.1,
    "counter_above_2x_assessed": 0.2,
    "owner_contested_appraisal": 0.15,
    "partial_taking": 0.1,
    "business_on_property": 0.1,
    "owner_occupied_home": 0.05,
    "long_term_ownership": 0.1,
}


def calculate_base_settlement(
    inp: PredictionInput,
) -> tuple[float, float, float]:
    """Calculate base settlement range from assessed value and adjustments.
    
    Returns:
        Tuple of (low, expected, high) settlement values
    """
    base = inp.assessed_value
    
    # Apply property type factor
    property_factor = PROPERTY_TYPE_FACTORS.get(inp.property_type, 1.0)
    base *= property_factor
    
    # Apply project urgency factor
    urgency_factor = PROJECT_TYPE_URGENCY.get(inp.project_type, 1.0)
    base *= urgency_factor
    
    # Apply jurisdiction multipliers
    comp_multiplier = get_compensation_multiplier(
        inp.jurisdiction,
        {
            "owner_occupied": inp.owner_occupied,
            "principal_residence": inp.principal_residence,
            "family_ownership_years": inp.family_ownership_years,
        }
    )
    base *= comp_multiplier
    
    # Add severance if partial taking
    if inp.partial_taking and inp.severance_impact > 0:
        # Severance typically ranges from 10-50% of remainder value
        severance_estimate = inp.severance_impact * 0.3  # Mid-range estimate
        base += severance_estimate
    
    # Base settlement range
    # Low: 90% of base (quick settlement)
    # Expected: 105% of base (typical negotiation outcome)
    # High: 120% of base (contentious case)
    low = base * 0.90
    expected = base * 1.05
    high = base * 1.20
    
    return low, expected, high


def calculate_dispute_level(inp: PredictionInput) -> tuple[DisputeLevel, float]:
    """Calculate dispute level and litigation probability.
    
    Returns:
        Tuple of (dispute_level, litigation_probability)
    """
    score = 0.0
    
    # Check indicators
    if inp.owner_has_attorney:
        score += DISPUTE_INDICATORS["owner_has_attorney"]
    
    if inp.previous_counter_offer:
        score += DISPUTE_INDICATORS["previous_counter_offer"]
        
        # Check if counter is way above assessed
        if inp.counter_offer_amount and inp.assessed_value > 0:
            ratio = inp.counter_offer_amount / inp.assessed_value
            if ratio > 2.0:
                score += DISPUTE_INDICATORS["counter_above_2x_assessed"]
    
    if inp.owner_contested_appraisal:
        score += DISPUTE_INDICATORS["owner_contested_appraisal"]
    
    if inp.partial_taking:
        score += DISPUTE_INDICATORS["partial_taking"]
    
    if inp.business_on_property:
        score += DISPUTE_INDICATORS["business_on_property"]
    
    if inp.owner_occupied:
        score += DISPUTE_INDICATORS["owner_occupied_home"]
    
    if inp.family_ownership_years > 20:
        score += DISPUTE_INDICATORS["long_term_ownership"]
    
    # Map score to dispute level
    if score < 0.15:
        level = DisputeLevel.LOW
    elif score < 0.30:
        level = DisputeLevel.MEDIUM
    elif score < 0.50:
        level = DisputeLevel.HIGH
    else:
        level = DisputeLevel.VERY_HIGH
    
    # Litigation probability based on score and factors
    # Base probability by dispute level
    lit_prob = {
        DisputeLevel.LOW: 0.05,
        DisputeLevel.MEDIUM: 0.15,
        DisputeLevel.HIGH: 0.35,
        DisputeLevel.VERY_HIGH: 0.60,
    }[level]
    
    # Adjust based on attorney involvement
    if inp.owner_has_attorney:
        lit_prob *= 1.3  # 30% increase
    
    # Cap at 0.95
    lit_prob = min(lit_prob, 0.95)
    
    return level, lit_prob


def estimate_timeline(
    inp: PredictionInput,
    dispute_level: DisputeLevel,
) -> tuple[int, int, int]:
    """Estimate timeline to settlement.
    
    Returns:
        Tuple of (min_days, expected_days, max_days)
    """
    # Base timelines by dispute level
    base_timelines = {
        DisputeLevel.LOW: (30, 60, 90),
        DisputeLevel.MEDIUM: (60, 120, 180),
        DisputeLevel.HIGH: (120, 240, 365),
        DisputeLevel.VERY_HIGH: (180, 365, 730),  # Up to 2 years for litigation
    }
    
    min_days, expected, max_days = base_timelines[dispute_level]
    
    # Adjust for jurisdiction notice periods
    from app.services.rules_engine import get_notice_requirements
    notice_reqs = get_notice_requirements(inp.jurisdiction)
    
    # Add statutory minimums
    initial_offer_days = notice_reqs.get("offer_notice_days", 30)
    final_offer_days = notice_reqs.get("final_offer_notice_days", 14)
    
    statutory_minimum = initial_offer_days + final_offer_days
    min_days = max(min_days, statutory_minimum)
    
    # Quick-take can shorten possession timeline but not total compensation resolution
    if is_quick_take_available(inp.jurisdiction):
        # Quick-take can allow possession faster, but comp may still be contested
        pass
    
    return min_days, expected, max_days


def generate_factors(inp: PredictionInput, jurisdiction_config) -> tuple[list[str], list[str]]:
    """Generate positive factors and risk factors for the prediction.
    
    Returns:
        Tuple of (positive_factors, risk_factors)
    """
    factors = []
    risk_factors = []
    
    # Jurisdiction-based factors
    initiation = jurisdiction_config.initiation
    compensation = jurisdiction_config.compensation
    
    if initiation.get("landowner_bill_of_rights"):
        risk_factors.append(f"State requires Landowner Bill of Rights - strict procedural compliance needed")
    
    if is_quick_take_available(inp.jurisdiction):
        factors.append("Quick-take available for expedited possession")
    
    if compensation.get("business_goodwill"):
        if inp.business_on_property:
            risk_factors.append("Business goodwill is compensable in this jurisdiction")
    
    # Property-based factors
    if inp.owner_occupied and inp.principal_residence:
        mult = get_compensation_multiplier(inp.jurisdiction, {
            "owner_occupied": True,
            "principal_residence": True,
            "family_ownership_years": inp.family_ownership_years,
        })
        if mult > 1.0:
            risk_factors.append(f"Owner-occupied residence multiplier applies ({mult:.0%})")
    
    if inp.partial_taking:
        risk_factors.append("Partial taking increases severance damage complexity")
    
    if inp.access_impact:
        if jurisdiction_config.compensation.get("lost_access"):
            risk_factors.append("Loss of access is compensable in this jurisdiction")
    
    # Dispute-based factors
    if inp.owner_has_attorney:
        risk_factors.append("Owner has legal representation - expect formal negotiations")
    
    if inp.owner_contested_appraisal:
        risk_factors.append("Owner has contested appraisal value")
    
    if inp.previous_counter_offer:
        if inp.counter_offer_amount and inp.assessed_value > 0:
            ratio = inp.counter_offer_amount / inp.assessed_value
            factors.append(f"Owner counter-offer at {ratio:.0%} of assessed value")
    
    # Positive factors
    if not inp.owner_has_attorney:
        factors.append("Owner not represented by attorney - potential for quicker settlement")
    
    if not inp.business_on_property:
        factors.append("No business operations on property - simpler valuation")
    
    attorney_fees = get_attorney_fee_rules(inp.jurisdiction)
    if attorney_fees.get("automatic"):
        risk_factors.append("Automatic attorney fee recovery for owner - litigation incentive")
    
    return factors, risk_factors


def generate_strategy(
    inp: PredictionInput,
    dispute_level: DisputeLevel,
    expected_settlement: float,
) -> tuple[float, float, str]:
    """Generate negotiation strategy and recommended offer range.
    
    Returns:
        Tuple of (initial_offer, ceiling, strategy_description)
    """
    # Base initial offer as percentage of expected settlement
    if dispute_level == DisputeLevel.LOW:
        initial_pct = 0.85  # Start at 85%
        ceiling_pct = 1.05
        strategy = "Direct approach - make competitive initial offer close to fair value"
    elif dispute_level == DisputeLevel.MEDIUM:
        initial_pct = 0.80
        ceiling_pct = 1.10
        strategy = "Standard negotiation - start slightly below expected, prepare for 2-3 rounds"
    elif dispute_level == DisputeLevel.HIGH:
        initial_pct = 0.75
        ceiling_pct = 1.15
        strategy = "Extended negotiation expected - document all offers thoroughly, prepare for mediation"
    else:
        initial_pct = 0.70
        ceiling_pct = 1.20
        strategy = "High dispute case - consider early mediation, prepare litigation budget, focus on relationship building"
    
    initial_offer = expected_settlement * initial_pct
    ceiling = expected_settlement * ceiling_pct
    
    # Adjust for owner counter-offer if present
    if inp.previous_counter_offer and inp.counter_offer_amount:
        # Initial offer should be at least 50% of counter to show good faith
        min_initial = inp.counter_offer_amount * 0.50
        initial_offer = max(initial_offer, min_initial)
        
        # Ceiling should consider counter
        if inp.counter_offer_amount < ceiling:
            # Owner's counter is within range - good sign
            strategy += ". Owner counter-offer is within settlement range - likely resolution without litigation"
        else:
            # Gap may be too large
            strategy += ". Significant gap between positions - consider joint appraisal or mediation"
    
    return initial_offer, ceiling, strategy


def predict_settlement(inp: PredictionInput) -> SettlementPrediction:
    """Generate a settlement prediction for the given inputs.
    
    This is the main entry point for the prediction service.
    
    Args:
        inp: Prediction input data
        
    Returns:
        SettlementPrediction with range, timeline, and recommendations
    """
    # Get jurisdiction configuration
    jurisdiction_config = get_jurisdiction_config(inp.jurisdiction)
    
    # Calculate base settlement range
    low, expected, high = calculate_base_settlement(inp)
    
    # Determine dispute level and litigation probability
    dispute_level, lit_prob = calculate_dispute_level(inp)
    
    # Adjust settlement range based on dispute level
    if dispute_level in (DisputeLevel.HIGH, DisputeLevel.VERY_HIGH):
        # Higher dispute = wider range
        spread_factor = 1.2 if dispute_level == DisputeLevel.HIGH else 1.4
        low *= 0.95
        high *= spread_factor
    
    # Estimate timeline
    min_days, expected_days, max_days = estimate_timeline(inp, dispute_level)
    
    # Generate factors
    factors, risk_factors = generate_factors(inp, jurisdiction_config)
    
    # Generate strategy
    initial_offer, ceiling, strategy = generate_strategy(
        inp, dispute_level, expected
    )
    
    # Calculate confidence
    # Lower confidence for high-value properties and high dispute
    base_confidence = 0.75
    
    if inp.assessed_value > 1000000:
        base_confidence -= 0.1  # High value = more uncertainty
    
    if dispute_level == DisputeLevel.VERY_HIGH:
        base_confidence -= 0.15
    elif dispute_level == DisputeLevel.HIGH:
        base_confidence -= 0.1
    
    if inp.partial_taking:
        base_confidence -= 0.05  # Severance is uncertain
    
    confidence = max(0.3, base_confidence)  # Floor at 30%
    
    return SettlementPrediction(
        low_settlement=round(low, 2),
        expected_settlement=round(expected, 2),
        high_settlement=round(high, 2),
        confidence=round(confidence, 2),
        expected_days_to_settlement=expected_days,
        min_days=min_days,
        max_days=max_days,
        litigation_probability=round(lit_prob, 2),
        dispute_level=dispute_level,
        factors=factors,
        risk_factors=risk_factors,
        recommended_initial_offer=round(initial_offer, 2),
        recommended_ceiling=round(ceiling, 2),
        negotiation_strategy=strategy,
    )


def compute_risk_profile(
    inp: PredictionInput,
    prediction: SettlementPrediction,
) -> RiskProfile:
    """Compute a detailed risk profile for the case.
    
    Args:
        inp: Prediction input
        prediction: Settlement prediction
        
    Returns:
        RiskProfile with detailed risk analysis
    """
    factors = []
    recommendations = []
    litigation_indicators = []
    
    # Score components
    financial_risk = 0
    timeline_risk = 0
    legal_risk = 0
    
    # Financial risk
    if inp.assessed_value > 500000:
        financial_risk += 20
        factors.append({
            "name": "High Value Property",
            "score": 20,
            "description": "Properties over $500K attract more scrutiny and litigation",
        })
    
    spread = (prediction.high_settlement - prediction.low_settlement) / prediction.expected_settlement
    if spread > 0.3:
        financial_risk += 15
        factors.append({
            "name": "Wide Settlement Range",
            "score": 15,
            "description": f"Settlement range spans {spread:.0%} - significant valuation uncertainty",
        })
    
    # Timeline risk
    if prediction.expected_days_to_settlement > 180:
        timeline_risk += 20
        factors.append({
            "name": "Extended Timeline",
            "score": 20,
            "description": "Expected settlement timeline exceeds 6 months",
        })
        recommendations.append("Consider mediation to accelerate resolution")
    
    # Legal risk
    if prediction.litigation_probability > 0.4:
        legal_risk += 25
        litigation_indicators.append(f"Litigation probability at {prediction.litigation_probability:.0%}")
        recommendations.append("Prepare litigation budget and strategy")
    
    if inp.owner_has_attorney:
        legal_risk += 10
        litigation_indicators.append("Owner represented by counsel")
    
    if inp.owner_contested_appraisal:
        legal_risk += 15
        litigation_indicators.append("Owner has contested appraisal")
        recommendations.append("Consider ordering second appraisal or review appraisal methodology")
    
    # Overall score
    overall_risk = financial_risk + timeline_risk + legal_risk
    
    # Determine risk level
    if overall_risk < 25:
        risk_level = "low"
    elif overall_risk < 50:
        risk_level = "medium"
    elif overall_risk < 75:
        risk_level = "high"
    else:
        risk_level = "critical"
    
    # Add general recommendations based on risk level
    if risk_level in ("high", "critical"):
        recommendations.append("Escalate to senior counsel for review")
        recommendations.append("Document all communications thoroughly")
    
    if not recommendations:
        recommendations.append("Standard negotiation approach recommended")
    
    return RiskProfile(
        overall_risk=overall_risk,
        risk_level=risk_level,
        factors=factors,
        recommendations=recommendations,
        litigation_indicators=litigation_indicators,
    )
