"""Intake Agent for case eligibility evaluation and property data fetching.

This agent evaluates new eminent domain cases for:
- Legal eligibility (public use, authority)
- Property data gathering (title records, owner info)
- Risk scoring and flagging

It integrates with:
- Rules engine for jurisdiction-specific eligibility rules
- External property data APIs
- Gemini AI for eligibility analysis
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.rules_engine import evaluate_rules, get_jurisdiction_config
from app.services.property_data_service import PropertyDataService, PropertyData

logger = logging.getLogger(__name__)


# Prompt for eligibility analysis
INTAKE_ELIGIBILITY_PROMPT = """Analyze this eminent domain case for legal eligibility.

Property Data:
{property_data}

Condemning Authority: {authority}
Stated Public Use: {public_use}
Jurisdiction: {jurisdiction}

Jurisdiction Configuration:
- Economic Development Banned: {econ_dev_banned}
- Public Use Restrictions: {public_use_restrictions}

Evaluate:
1. Is the condemning authority legally authorized to exercise eminent domain? (cite relevant statutes)
2. Does the stated purpose qualify as "public use" under {jurisdiction} law?
3. Are there any constitutional or procedural barriers?
4. What is the overall eligibility assessment?

Return your analysis as JSON with these keys:
{{
    "eligibility": true/false,
    "authority_valid": true/false,
    "public_use_valid": true/false,
    "concerns": ["list of concerns"],
    "confidence": 0.0-1.0,
    "citations": ["relevant legal citations"],
    "explanation": "brief explanation of the assessment"
}}
"""


@dataclass
class EligibilityResult:
    """Result of eligibility evaluation."""
    is_eligible: bool
    confidence: float
    authority_valid: bool
    public_use_valid: bool
    concerns: list[str]
    citations: list[str]
    flags: list[str]
    explanation: str


@dataclass
class RiskScore:
    """Risk assessment for a case."""
    score: int  # 0-100
    factors: list[str]
    category: str  # low, medium, high


class IntakeAgent(BaseAgent):
    """Agent for case intake and eligibility evaluation.
    
    Responsibilities:
    - Fetch property data from external APIs
    - Evaluate legal eligibility against jurisdiction rules
    - Calculate risk scores
    - Generate AI-assisted eligibility analysis
    
    Escalation triggers:
    - Confidence below 0.80
    - Risk score above 70
    - Constitutional issues detected
    - Authority concerns
    """
    
    agent_type = AgentType.INTAKE
    confidence_threshold = 0.80
    
    def __init__(self, db_session=None, confidence_threshold: float = None):
        """Initialize the intake agent.
        
        Args:
            db_session: Database session for caching
            confidence_threshold: Override default threshold
        """
        super().__init__(confidence_threshold)
        self.db = db_session
        self.property_service = PropertyDataService(db_session)
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute intake evaluation for a case.
        
        Args:
            context: Agent context with case details
            
        Returns:
            AgentResult with eligibility and property data
        """
        start_time = datetime.utcnow()
        
        try:
            # 1. Fetch property data from external APIs
            property_data = await self.fetch_property_data(
                context.apn, 
                context.county_fips
            )
            
            # 2. Evaluate eligibility using rules engine + AI
            eligibility = await self.evaluate_eligibility(
                context.jurisdiction,
                property_data,
                context.payload or {},
            )
            
            # 3. Calculate risk score
            risk = await self.calculate_risk_score(property_data, eligibility)
            
            # 4. Generate AI summary if needed
            ai_summary = None
            if eligibility.confidence < 0.9 or risk.score > 50:
                ai_summary = await self.generate_summary(
                    property_data, 
                    eligibility, 
                    risk
                )
            
            # Build result
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            result = AgentResult(
                success=eligibility.is_eligible,
                confidence=eligibility.confidence,
                data={
                    "property": property_data.to_dict() if property_data else None,
                    "eligibility": {
                        "is_eligible": eligibility.is_eligible,
                        "authority_valid": eligibility.authority_valid,
                        "public_use_valid": eligibility.public_use_valid,
                        "concerns": eligibility.concerns,
                        "citations": eligibility.citations,
                        "explanation": eligibility.explanation,
                    },
                    "risk": {
                        "score": risk.score,
                        "category": risk.category,
                        "factors": risk.factors,
                    },
                    "ai_summary": ai_summary,
                },
                flags=eligibility.flags,
                requires_review=risk.score > 70 or eligibility.flags,
                audit_payload={
                    "explanation": eligibility.explanation,
                    "risk_factors": risk.factors,
                    "property_source": property_data.source if property_data else None,
                },
                execution_time_ms=int(execution_time),
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Intake execution failed: {e}", exc_info=True)
            return AgentResult.failure_result(
                error=str(e),
                error_code="INTAKE_EXECUTION_ERROR",
            )
    
    async def fetch_property_data(
        self, 
        apn: str, 
        county_fips: str,
    ) -> PropertyData:
        """Fetch property data from external APIs.
        
        Args:
            apn: Assessor's Parcel Number
            county_fips: County FIPS code
            
        Returns:
            PropertyData with available information
        """
        return await self.property_service.fetch_property_data(apn, county_fips)
    
    async def evaluate_eligibility(
        self,
        jurisdiction: str,
        property_data: PropertyData,
        case_payload: dict[str, Any],
    ) -> EligibilityResult:
        """Evaluate legal eligibility for the case.
        
        Args:
            jurisdiction: State code
            property_data: Property information
            case_payload: Additional case data
            
        Returns:
            EligibilityResult with assessment
        """
        concerns = []
        flags = []
        citations = []
        
        # Get jurisdiction configuration
        try:
            config = get_jurisdiction_config(jurisdiction)
        except FileNotFoundError:
            return EligibilityResult(
                is_eligible=False,
                confidence=0.3,
                authority_valid=False,
                public_use_valid=False,
                concerns=[f"No rules configured for jurisdiction: {jurisdiction}"],
                citations=[],
                flags=["jurisdiction_not_configured"],
                explanation=f"Cannot evaluate eligibility without rules for {jurisdiction}",
            )
        
        # Check authority
        authority = case_payload.get("condemning_authority", "")
        authority_type = case_payload.get("authority_type", "")
        authority_valid = self._check_authority(authority, authority_type, jurisdiction)
        
        if not authority_valid:
            concerns.append("Condemning authority may not have proper delegation")
            flags.append("authority_concern")
        
        # Check public use
        public_use = case_payload.get("public_use", "")
        public_use_type = case_payload.get("public_use_type", "")
        public_use_valid = self._check_public_use(
            public_use, 
            public_use_type, 
            config,
            jurisdiction
        )
        
        if not public_use_valid:
            concerns.append("Stated public use may not meet jurisdiction requirements")
            if config.public_use.get("economic_development_banned"):
                concerns.append(f"{jurisdiction} bans takings for economic development")
                flags.append("constitutional_issue")
        
        # Check for liens that could complicate taking
        if property_data and property_data.liens:
            concerns.append(f"Property has {len(property_data.liens)} outstanding liens")
            if len(property_data.liens) > 3:
                flags.append("complex_title")
        
        # Run rules engine for additional checks
        rule_payload = {
            "jurisdiction": jurisdiction,
            "property.assessed_value": property_data.assessed_value if property_data else 0,
            "case.authority_type": authority_type,
            "case.public_use_type": public_use_type,
        }
        rule_results = evaluate_rules(jurisdiction, rule_payload)
        
        for result in rule_results:
            if result.fired and result.citation:
                citations.append(result.citation)
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            authority_valid, 
            public_use_valid, 
            property_data,
            concerns,
        )
        
        # Determine overall eligibility
        is_eligible = authority_valid and public_use_valid
        
        explanation = self._generate_eligibility_explanation(
            is_eligible,
            authority_valid,
            public_use_valid,
            concerns,
            jurisdiction,
        )
        
        return EligibilityResult(
            is_eligible=is_eligible,
            confidence=confidence,
            authority_valid=authority_valid,
            public_use_valid=public_use_valid,
            concerns=concerns,
            citations=citations,
            flags=flags,
            explanation=explanation,
        )
    
    async def calculate_risk_score(
        self,
        property_data: PropertyData,
        eligibility: EligibilityResult,
    ) -> RiskScore:
        """Calculate risk score for the case.
        
        Args:
            property_data: Property information
            eligibility: Eligibility assessment
            
        Returns:
            RiskScore with score and factors
        """
        score = 0
        factors = []
        
        # Eligibility-based risk
        if not eligibility.is_eligible:
            score += 40
            factors.append("Case does not meet eligibility requirements")
        elif eligibility.concerns:
            score += 10 * len(eligibility.concerns)
            factors.extend(eligibility.concerns[:3])  # Top 3 concerns
        
        # Property-based risk
        if property_data:
            # High-value property
            if property_data.assessed_value and property_data.assessed_value > 1000000:
                score += 15
                factors.append("High-value property (>$1M)")
            
            # Complex ownership
            if property_data.owner_names and len(property_data.owner_names) > 2:
                score += 10
                factors.append("Multiple property owners")
            
            # Outstanding liens
            if property_data.liens:
                score += 5 * min(len(property_data.liens), 4)
                factors.append(f"{len(property_data.liens)} outstanding liens")
            
            # Low data confidence
            if property_data.confidence < 0.7:
                score += 10
                factors.append("Low confidence in property data")
        
        # Authority/public use flags
        if "constitutional_issue" in eligibility.flags:
            score += 30
            factors.append("Potential constitutional issue")
        
        if "authority_concern" in eligibility.flags:
            score += 15
            factors.append("Authority concerns")
        
        # Cap score at 100
        score = min(score, 100)
        
        # Determine category
        if score >= 70:
            category = "high"
        elif score >= 40:
            category = "medium"
        else:
            category = "low"
        
        return RiskScore(
            score=score,
            factors=factors,
            category=category,
        )
    
    async def generate_summary(
        self,
        property_data: PropertyData,
        eligibility: EligibilityResult,
        risk: RiskScore,
    ) -> Optional[dict[str, Any]]:
        """Generate AI summary of intake analysis.
        
        Args:
            property_data: Property information
            eligibility: Eligibility assessment
            risk: Risk score
            
        Returns:
            AI summary or None if unavailable
        """
        try:
            summary_prompt = f"""Summarize this eminent domain case intake analysis:

Property: {property_data.address if property_data else 'Unknown'}
Assessed Value: ${property_data.assessed_value:,.2f} if property_data and property_data.assessed_value else 'Unknown'

Eligibility:
- Eligible: {eligibility.is_eligible}
- Authority Valid: {eligibility.authority_valid}
- Public Use Valid: {eligibility.public_use_valid}
- Concerns: {', '.join(eligibility.concerns) if eligibility.concerns else 'None'}

Risk Score: {risk.score}/100 ({risk.category})
Risk Factors: {', '.join(risk.factors) if risk.factors else 'None'}

Provide a brief 2-3 sentence summary for attorney review.
Return as JSON: {{"summary": "...", "key_issues": [...], "recommendation": "proceed|review|reject"}}
"""
            
            response = await self.call_ai(summary_prompt, task_type="intake_summary")
            return response
            
        except Exception as e:
            self.logger.warning(f"AI summary generation failed: {e}")
            return None
    
    def _check_authority(
        self,
        authority: str,
        authority_type: str,
        jurisdiction: str,
    ) -> bool:
        """Check if condemning authority is valid.
        
        Args:
            authority: Name of condemning authority
            authority_type: Type (government, utility, etc.)
            jurisdiction: State code
            
        Returns:
            True if authority appears valid
        """
        # Valid authority types
        valid_types = [
            "government",
            "municipality",
            "county",
            "state_agency",
            "utility",
            "transportation",
            "redevelopment",
        ]
        
        if not authority:
            return False
        
        if authority_type and authority_type.lower() in valid_types:
            return True
        
        # Default to requiring review
        return False
    
    def _check_public_use(
        self,
        public_use: str,
        public_use_type: str,
        config: Any,
        jurisdiction: str,
    ) -> bool:
        """Check if stated public use is valid.
        
        Args:
            public_use: Description of public use
            public_use_type: Type classification
            config: Jurisdiction configuration
            jurisdiction: State code
            
        Returns:
            True if public use appears valid
        """
        # Valid public use types
        valid_types = [
            "transportation",
            "infrastructure",
            "utilities",
            "public_facilities",
            "flood_control",
            "environmental",
        ]
        
        # Types that may be restricted post-Kelo
        restricted_types = [
            "economic_development",
            "redevelopment",
            "blight_removal",
        ]
        
        if not public_use:
            return False
        
        public_use_type_lower = (public_use_type or "").lower()
        
        # Check for clearly valid uses
        if public_use_type_lower in valid_types:
            return True
        
        # Check for restricted uses based on jurisdiction
        if public_use_type_lower in restricted_types:
            if config.public_use.get("economic_development_banned"):
                return False
        
        # Default to requiring review
        return True
    
    def _calculate_confidence(
        self,
        authority_valid: bool,
        public_use_valid: bool,
        property_data: PropertyData,
        concerns: list[str],
    ) -> float:
        """Calculate confidence score for eligibility assessment.
        
        Args:
            authority_valid: Whether authority is valid
            public_use_valid: Whether public use is valid
            property_data: Property information
            concerns: List of concerns
            
        Returns:
            Confidence score 0.0-1.0
        """
        confidence = 1.0
        
        # Reduce confidence for invalid components
        if not authority_valid:
            confidence -= 0.3
        if not public_use_valid:
            confidence -= 0.3
        
        # Reduce confidence for each concern
        confidence -= 0.05 * len(concerns)
        
        # Reduce confidence for low-quality data
        if property_data and property_data.confidence < 0.7:
            confidence -= 0.1
        elif not property_data:
            confidence -= 0.2
        
        return max(0.1, min(1.0, confidence))
    
    def _generate_eligibility_explanation(
        self,
        is_eligible: bool,
        authority_valid: bool,
        public_use_valid: bool,
        concerns: list[str],
        jurisdiction: str,
    ) -> str:
        """Generate human-readable explanation.
        
        Args:
            is_eligible: Overall eligibility
            authority_valid: Authority validation
            public_use_valid: Public use validation
            concerns: List of concerns
            jurisdiction: State code
            
        Returns:
            Explanation string
        """
        parts = []
        
        if is_eligible:
            parts.append(f"Case appears eligible for {jurisdiction} eminent domain proceedings.")
        else:
            parts.append(f"Case may not be eligible for {jurisdiction} eminent domain proceedings.")
        
        if not authority_valid:
            parts.append("The condemning authority requires verification.")
        
        if not public_use_valid:
            parts.append("The stated public use may not meet jurisdiction requirements.")
        
        if concerns:
            parts.append(f"Additional concerns: {'; '.join(concerns[:3])}")
        
        return " ".join(parts)
