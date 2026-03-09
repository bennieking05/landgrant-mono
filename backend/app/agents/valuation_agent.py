"""Valuation Agent for appraisal cross-checking and compensation calculation.

This agent handles:
- Cross-checking appraisals against AVM data
- Calculating full compensation packages
- Generating negotiation strategies
- Flagging valuation discrepancies

It integrates with:
- AVM service for market value estimates
- Rules engine for jurisdiction-specific multipliers
- Gemini AI for strategy recommendations
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.rules_engine import (
    get_jurisdiction_config,
    get_compensation_multiplier,
    get_attorney_fee_rules,
)
from app.services.avm_service import AVMService, CombinedAVMResult

logger = logging.getLogger(__name__)


# Prompt for negotiation strategy
NEGOTIATION_STRATEGY_PROMPT = """Analyze this eminent domain compensation case.

Property Value Analysis:
- Appraisal Value: ${appraisal_value:,.2f}
- AVM Consensus: ${avm_consensus:,.2f}
- AVM Range: ${avm_low:,.2f} - ${avm_high:,.2f}
- Discrepancy: {discrepancy_percent:.1f}%

Full Compensation Breakdown:
{compensation_breakdown}

Jurisdiction: {jurisdiction}
Attorney Fee Rules:
- Automatic Fees: {fee_automatic}
- Threshold-Based: {fee_threshold}% above offer
- Mandatory: {fee_mandatory}

Consider:
1. Is the appraisal defensible given AVM data?
2. What is the likely range at trial?
3. Settlement vs litigation cost-benefit analysis
4. Risk factors for each side

Return JSON:
{{
    "recommendation": "settle|negotiate|litigate",
    "confidence": 0.0-1.0,
    "settlement_range": {{
        "min": <number>,
        "target": <number>,
        "max": <number>
    }},
    "litigation_risk": {{
        "owner_upside_percent": <number>,
        "condemnor_risk_percent": <number>
    }},
    "key_factors": ["factor1", "factor2"],
    "suggested_offer": <number>,
    "rationale": "brief explanation"
}}
"""


@dataclass
class CompensationBreakdown:
    """Full compensation calculation."""
    base_fmv: float
    multiplier: float
    adjusted_fmv: float
    severance_damages: float
    relocation_costs: float
    estimated_fees: float
    total_compensation: float
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "base_fmv": self.base_fmv,
            "multiplier": self.multiplier,
            "adjusted_fmv": self.adjusted_fmv,
            "severance_damages": self.severance_damages,
            "relocation_costs": self.relocation_costs,
            "estimated_fees": self.estimated_fees,
            "total_compensation": self.total_compensation,
        }
    
    def to_string(self) -> str:
        return f"""
Base FMV: ${self.base_fmv:,.2f}
Multiplier: {self.multiplier}x
Adjusted FMV: ${self.adjusted_fmv:,.2f}
Severance Damages: ${self.severance_damages:,.2f}
Relocation Costs: ${self.relocation_costs:,.2f}
Estimated Fees: ${self.estimated_fees:,.2f}
Total: ${self.total_compensation:,.2f}
"""


@dataclass
class NegotiationStrategy:
    """Negotiation strategy recommendation."""
    recommendation: str  # settle, negotiate, litigate
    confidence: float
    settlement_range: dict[str, float]  # min, target, max
    litigation_risk: dict[str, float]
    key_factors: list[str]
    suggested_offer: float
    rationale: str


class ValuationAgent(BaseAgent):
    """Agent for valuation cross-checking and compensation calculation.
    
    Responsibilities:
    - Fetch and compare AVM estimates
    - Cross-check against appraisals
    - Calculate jurisdiction-specific compensation
    - Generate negotiation strategies
    
    Escalation triggers:
    - Significant discrepancy (>15%) between appraisal and AVM
    - High-value properties (>$1M)
    - Complex compensation calculations
    """
    
    agent_type = AgentType.VALUATION
    confidence_threshold = 0.85
    
    # Discrepancy threshold for flagging
    DISCREPANCY_THRESHOLD = 15.0  # percent
    
    def __init__(self, db_session=None, confidence_threshold: float = None):
        """Initialize the valuation agent.
        
        Args:
            db_session: Database session
            confidence_threshold: Override default threshold
        """
        super().__init__(confidence_threshold)
        self.db = db_session
        self.avm_service = AVMService(db_session)
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute valuation analysis for a parcel.
        
        Args:
            context: Agent context with parcel details
            
        Returns:
            AgentResult with valuation analysis
        """
        start_time = datetime.utcnow()
        
        try:
            if not context.parcel_id:
                return AgentResult.failure_result(
                    error="No parcel_id provided",
                    error_code="MISSING_PARCEL_ID",
                )
            
            # Get parcel and appraisal data
            parcel_data = await self._get_parcel_data(context.parcel_id)
            if not parcel_data:
                return AgentResult.failure_result(
                    error=f"Parcel {context.parcel_id} not found",
                    error_code="PARCEL_NOT_FOUND",
                )
            
            appraisal_value = parcel_data.get("appraisal_value", 0)
            address = parcel_data.get("address", "")
            jurisdiction = context.jurisdiction or parcel_data.get("jurisdiction", "TX")
            
            # Fetch AVM estimates
            avm_result = await self.avm_service.get_combined_estimates(
                address=address,
                parcel_id=context.parcel_id,
            )
            
            # Calculate discrepancy
            discrepancy = self._calculate_discrepancy(appraisal_value, avm_result)
            
            # Calculate full compensation
            compensation = await self.calculate_full_compensation(
                context.parcel_id,
                jurisdiction,
                appraisal_value,
                parcel_data,
            )
            
            # Generate negotiation strategy
            strategy = await self.generate_negotiation_strategy(
                appraisal_value,
                avm_result,
                compensation,
                jurisdiction,
            )
            
            # Determine flags
            flags = []
            if abs(discrepancy) > self.DISCREPANCY_THRESHOLD:
                flags.append("significant_discrepancy")
            if appraisal_value > 1000000:
                flags.append("high_value_property")
            
            # Calculate confidence
            confidence = self._calculate_confidence(avm_result, discrepancy)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return AgentResult(
                success=True,
                confidence=confidence,
                data={
                    "appraisal_value": appraisal_value,
                    "avm": avm_result.to_dict(),
                    "discrepancy_percent": discrepancy,
                    "compensation": compensation.to_dict(),
                    "strategy": {
                        "recommendation": strategy.recommendation,
                        "confidence": strategy.confidence,
                        "settlement_range": strategy.settlement_range,
                        "litigation_risk": strategy.litigation_risk,
                        "key_factors": strategy.key_factors,
                        "suggested_offer": strategy.suggested_offer,
                        "rationale": strategy.rationale,
                    } if strategy else None,
                },
                flags=flags,
                requires_review=abs(discrepancy) > self.DISCREPANCY_THRESHOLD,
                audit_payload={
                    "explanation": f"Valuation analysis: appraisal ${appraisal_value:,.0f}, AVM ${avm_result.consensus_value:,.0f}, discrepancy {discrepancy:.1f}%",
                },
                execution_time_ms=int(execution_time),
            )
            
        except Exception as e:
            self.logger.error(f"Valuation analysis failed: {e}", exc_info=True)
            return AgentResult.failure_result(
                error=str(e),
                error_code="VALUATION_ERROR",
            )
    
    async def fetch_avm_estimates(
        self,
        parcel_id: str,
        address: str,
    ) -> CombinedAVMResult:
        """Fetch AVM estimates for a property.
        
        Args:
            parcel_id: Parcel ID
            address: Property address
            
        Returns:
            Combined AVM results
        """
        return await self.avm_service.get_combined_estimates(
            address=address,
            parcel_id=parcel_id,
        )
    
    async def calculate_full_compensation(
        self,
        parcel_id: str,
        jurisdiction: str,
        appraisal_value: float = None,
        parcel_data: dict[str, Any] = None,
        include_severance: bool = True,
        include_relocation: bool = True,
    ) -> CompensationBreakdown:
        """Calculate full compensation package.
        
        Args:
            parcel_id: Parcel ID
            jurisdiction: State code
            appraisal_value: Base appraisal value
            parcel_data: Additional parcel data
            include_severance: Include severance damages
            include_relocation: Include relocation costs
            
        Returns:
            Complete compensation breakdown
        """
        # Get parcel data if not provided
        if parcel_data is None:
            parcel_data = await self._get_parcel_data(parcel_id) or {}
        
        # Use appraisal value or fetch
        if appraisal_value is None:
            appraisal_value = parcel_data.get("appraisal_value", 0)
        
        # Get compensation multiplier from rules
        multiplier = get_compensation_multiplier(jurisdiction, parcel_data)
        adjusted_fmv = appraisal_value * multiplier
        
        # Calculate severance damages
        severance = 0.0
        if include_severance and parcel_data.get("is_partial_taking"):
            severance = await self._calculate_severance(parcel_data)
        
        # Calculate relocation costs
        relocation = 0.0
        if include_relocation:
            relocation = await self._estimate_relocation(parcel_data)
        
        # Estimate attorney/expert fees
        fees = await self._estimate_fees(jurisdiction, adjusted_fmv)
        
        total = adjusted_fmv + severance + relocation + fees
        
        return CompensationBreakdown(
            base_fmv=appraisal_value,
            multiplier=multiplier,
            adjusted_fmv=adjusted_fmv,
            severance_damages=severance,
            relocation_costs=relocation,
            estimated_fees=fees,
            total_compensation=total,
        )
    
    async def generate_negotiation_strategy(
        self,
        appraisal_value: float,
        avm_result: CombinedAVMResult,
        compensation: CompensationBreakdown,
        jurisdiction: str,
    ) -> Optional[NegotiationStrategy]:
        """Generate negotiation strategy recommendation.
        
        Args:
            appraisal_value: Appraisal value
            avm_result: AVM results
            compensation: Compensation breakdown
            jurisdiction: State code
            
        Returns:
            NegotiationStrategy or None if AI unavailable
        """
        # Get fee rules
        fee_rules = get_attorney_fee_rules(jurisdiction)
        
        discrepancy = self._calculate_discrepancy(appraisal_value, avm_result)
        
        prompt = NEGOTIATION_STRATEGY_PROMPT.format(
            appraisal_value=appraisal_value,
            avm_consensus=avm_result.consensus_value,
            avm_low=avm_result.consensus_low,
            avm_high=avm_result.consensus_high,
            discrepancy_percent=discrepancy,
            compensation_breakdown=compensation.to_string(),
            jurisdiction=jurisdiction,
            fee_automatic=fee_rules.get("automatic", False),
            fee_threshold=fee_rules.get("threshold_percent", 0),
            fee_mandatory=fee_rules.get("mandatory", False),
        )
        
        response = await self.call_ai(prompt, task_type="negotiation_strategy")
        
        if response:
            return NegotiationStrategy(
                recommendation=response.get("recommendation", "negotiate"),
                confidence=response.get("confidence", 0.7),
                settlement_range=response.get("settlement_range", {}),
                litigation_risk=response.get("litigation_risk", {}),
                key_factors=response.get("key_factors", []),
                suggested_offer=response.get("suggested_offer", appraisal_value),
                rationale=response.get("rationale", ""),
            )
        
        # Default strategy if AI unavailable
        return self._generate_default_strategy(
            appraisal_value, 
            avm_result, 
            compensation,
            discrepancy,
        )
    
    def _calculate_discrepancy(
        self,
        appraisal_value: float,
        avm_result: CombinedAVMResult,
    ) -> float:
        """Calculate discrepancy between appraisal and AVM.
        
        Args:
            appraisal_value: Appraisal value
            avm_result: AVM results
            
        Returns:
            Discrepancy as percentage
        """
        if appraisal_value == 0 or avm_result.consensus_value == 0:
            return 0.0
        
        return ((appraisal_value - avm_result.consensus_value) / avm_result.consensus_value) * 100
    
    def _calculate_confidence(
        self,
        avm_result: CombinedAVMResult,
        discrepancy: float,
    ) -> float:
        """Calculate confidence in valuation analysis.
        
        Args:
            avm_result: AVM results
            discrepancy: Discrepancy percentage
            
        Returns:
            Confidence score 0.0-1.0
        """
        confidence = avm_result.overall_confidence
        
        # Reduce confidence for high discrepancy
        if abs(discrepancy) > 30:
            confidence -= 0.3
        elif abs(discrepancy) > 20:
            confidence -= 0.2
        elif abs(discrepancy) > 15:
            confidence -= 0.1
        
        # Reduce confidence for high AVM spread
        if avm_result.discrepancy_percent > 20:
            confidence -= 0.1
        
        return max(0.3, min(1.0, confidence))
    
    async def _get_parcel_data(self, parcel_id: str) -> Optional[dict[str, Any]]:
        """Fetch parcel data from database."""
        if not self.db:
            # Return mock data
            return {
                "id": parcel_id,
                "address": "123 Main Street, Anytown, TX 75001",
                "jurisdiction": "TX",
                "appraisal_value": 350000.0,
                "is_partial_taking": False,
                "owner_occupied": True,
                "principal_residence": True,
                "property_type": "residential",
            }
        
        try:
            from app.db.models import Parcel, Appraisal, Project
            from sqlalchemy import select
            
            # Fetch parcel with appraisal
            result = await self.db.execute(
                select(Parcel).where(Parcel.id == parcel_id)
            )
            parcel = result.scalar_one_or_none()
            
            if parcel:
                # Get project for jurisdiction
                project_result = await self.db.execute(
                    select(Project).where(Project.id == parcel.project_id)
                )
                project = project_result.scalar_one_or_none()
                
                # Get appraisal
                appraisal_result = await self.db.execute(
                    select(Appraisal).where(Appraisal.parcel_id == parcel_id)
                )
                appraisal = appraisal_result.scalar_one_or_none()
                
                return {
                    "id": parcel.id,
                    "address": parcel.metadata_json.get("address", ""),
                    "jurisdiction": project.jurisdiction_code if project else "TX",
                    "appraisal_value": float(appraisal.value) if appraisal else 0,
                    "is_partial_taking": parcel.metadata_json.get("is_partial_taking", False),
                    "owner_occupied": parcel.metadata_json.get("owner_occupied", False),
                    "principal_residence": parcel.metadata_json.get("principal_residence", False),
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to fetch parcel data: {e}")
            return None
    
    async def _calculate_severance(self, parcel_data: dict[str, Any]) -> float:
        """Calculate severance damages for partial taking.
        
        Args:
            parcel_data: Parcel information
            
        Returns:
            Estimated severance damages
        """
        # This would involve complex analysis in production
        # For now, return a placeholder based on property value
        before_value = parcel_data.get("appraisal_value", 0)
        taking_percent = parcel_data.get("taking_percent", 30)  # Default 30%
        
        # Simple estimate: additional 10-20% of taken value for access/utility impacts
        taken_value = before_value * (taking_percent / 100)
        severance = taken_value * 0.15  # 15% of taken value
        
        return severance
    
    async def _estimate_relocation(self, parcel_data: dict[str, Any]) -> float:
        """Estimate relocation costs.
        
        Args:
            parcel_data: Parcel information
            
        Returns:
            Estimated relocation costs
        """
        property_type = parcel_data.get("property_type", "residential")
        
        # URA-based estimates
        if property_type == "residential":
            # Moving costs + temporary housing + incidentals
            return 15000.0
        elif property_type == "commercial":
            # More complex - would need business data
            return 50000.0
        else:
            return 10000.0
    
    async def _estimate_fees(self, jurisdiction: str, base_value: float) -> float:
        """Estimate attorney/expert fees.
        
        Args:
            jurisdiction: State code
            base_value: Base property value
            
        Returns:
            Estimated fees
        """
        fee_rules = get_attorney_fee_rules(jurisdiction)
        
        # If automatic or mandatory fees
        if fee_rules.get("automatic") or fee_rules.get("mandatory"):
            # Estimate 5-10% of property value
            return base_value * 0.07
        
        # If threshold-based, estimate potential fees
        if fee_rules.get("threshold_based"):
            # Assume 50% chance of exceeding threshold
            return base_value * 0.035
        
        return 0.0
    
    def _generate_default_strategy(
        self,
        appraisal_value: float,
        avm_result: CombinedAVMResult,
        compensation: CompensationBreakdown,
        discrepancy: float,
    ) -> NegotiationStrategy:
        """Generate default strategy without AI.
        
        Args:
            appraisal_value: Appraisal value
            avm_result: AVM results
            compensation: Compensation breakdown
            discrepancy: Discrepancy percentage
            
        Returns:
            Default negotiation strategy
        """
        # Determine recommendation based on discrepancy
        if abs(discrepancy) <= 5:
            recommendation = "settle"
            rationale = "Appraisal aligns closely with market data"
        elif abs(discrepancy) <= 15:
            recommendation = "negotiate"
            rationale = "Moderate difference - room for negotiation"
        else:
            recommendation = "negotiate" if discrepancy > 0 else "litigate"
            rationale = "Significant discrepancy requires careful analysis"
        
        # Calculate settlement range
        avg_value = (appraisal_value + avm_result.consensus_value) / 2
        
        return NegotiationStrategy(
            recommendation=recommendation,
            confidence=0.6,  # Lower confidence without AI
            settlement_range={
                "min": avm_result.consensus_low,
                "target": avg_value,
                "max": avm_result.consensus_high,
            },
            litigation_risk={
                "owner_upside_percent": max(0, discrepancy),
                "condemnor_risk_percent": max(0, -discrepancy),
            },
            key_factors=[
                f"Discrepancy: {discrepancy:.1f}%",
                f"AVM confidence: {avm_result.overall_confidence:.0%}",
            ],
            suggested_offer=avg_value,
            rationale=rationale,
        )
