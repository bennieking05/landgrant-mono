"""Edge Case Agent for handling special eminent domain scenarios.

This agent handles:
- Business relocations (URA compliance, goodwill calculation)
- Partial takings (severance damages, uneconomic remnants)
- Inverse condemnation claims
- Heritage/long-term family properties
- Workflow adaptations for special scenarios

It integrates with:
- Rules engine for jurisdiction-specific requirements
- Valuation agent for damage calculations
- Gemini AI for complex scenario analysis
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.rules_engine import get_jurisdiction_config, get_compensation_multiplier

logger = logging.getLogger(__name__)


# Prompts for edge case analysis
EDGE_CASE_DETECTION_PROMPT = """Analyze this parcel for special eminent domain scenarios.

Parcel Data:
{parcel_data}

Property Type: {property_type}
Taking Type: {taking_type}
Business Information: {business_info}
Historical Context: {historical_context}

Detect:
1. Is this a business relocation requiring URA compliance?
2. Is this a partial taking with potential severance damages?
3. Could this be an inverse condemnation claim?
4. Is this a heritage/long-term family property (MO 150% multiplier)?
5. Any environmental contamination issues?
6. Any cultural/historical significance?

Return JSON:
{{
    "detected_edge_cases": ["business_relocation", "partial_taking", etc.],
    "confidence": {{"case_type": confidence_score}},
    "workflow_adjustments": [
        {{"edge_case": "...", "required_steps": [...], "additional_documents": [...]}}
    ],
    "alerts": ["important notices for attorney"]
}}
"""

SEVERANCE_DAMAGE_PROMPT = """Calculate severance damages for this partial taking.

Before Condition:
{before_data}

Taking:
{taking_data}

After Condition:
{after_data}

Comparable Sales:
{comps}

Analyze:
1. Impact on remainder's access
2. Impact on remainder's utility/functionality
3. Cost to cure (if applicable)
4. Is the remainder an uneconomic remnant?

Return JSON:
{{
    "before_value": <float>,
    "taking_value": <float>,
    "after_value": <float>,
    "severance_damages": <float>,
    "cost_to_cure": <float>,
    "is_uneconomic_remnant": true/false,
    "remnant_analysis": "explanation",
    "recommendation": "partial|full_taking"
}}
"""

GOODWILL_CALCULATION_PROMPT = """Calculate business goodwill for this relocation.

Business Information:
{business_info}

Jurisdiction: {jurisdiction}
Goodwill Requirements: {goodwill_rules}

Calculate:
1. Annual net income (3-year average)
2. Going concern value
3. Relocation feasibility
4. Loss of customer base
5. Goodwill amount (if jurisdiction allows)

Return JSON:
{{
    "goodwill_available": true/false,
    "goodwill_amount": <float>,
    "calculation_method": "income|market|asset",
    "supporting_factors": [...],
    "relocation_feasible": true/false,
    "total_business_loss": <float>
}}
"""


@dataclass
class EdgeCaseDetection:
    """Result of edge case detection."""
    detected_cases: list[str]
    confidence: dict[str, float]
    workflow_adjustments: list[dict[str, Any]]
    alerts: list[str]


@dataclass
class BusinessRelocationResult:
    """Result of business relocation calculation."""
    moving_costs: float
    goodwill: float
    reestablishment_costs: float
    total_relocation: float
    relocation_plan: dict[str, Any]
    ura_compliant: bool


@dataclass
class PartialTakingResult:
    """Result of partial taking analysis."""
    before_value: float
    taking_value: float
    after_value: float
    severance_damages: float
    cost_to_cure: float
    is_uneconomic_remnant: bool
    recommendation: str  # partial or full_taking
    analysis: str


class EdgeCaseAgent(BaseAgent):
    """Agent for handling special eminent domain scenarios.
    
    Responsibilities:
    - Detect edge cases (business, partial, inverse)
    - Calculate business relocation costs and goodwill
    - Analyze partial takings for severance damages
    - Detect and flag inverse condemnation situations
    - Adapt workflows for special scenarios
    
    Escalation triggers:
    - Any edge case detected (requires attorney review)
    - Uneconomic remnant detected
    - Inverse condemnation potential
    """
    
    agent_type = AgentType.EDGE_CASE
    confidence_threshold = 0.80
    
    # All edge cases escalate by default
    critical_flags = [
        "business_relocation",
        "partial_taking",
        "inverse_condemnation",
        "uneconomic_remnant_detected",
        "heritage_property",
    ]
    
    def __init__(self, db_session=None, confidence_threshold: float = None):
        """Initialize the edge case agent.
        
        Args:
            db_session: Database session
            confidence_threshold: Override default threshold
        """
        super().__init__(confidence_threshold)
        self.db = db_session
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute edge case handling based on context.
        
        Args:
            context: Agent context with details
            
        Returns:
            AgentResult with analysis
        """
        start_time = datetime.utcnow()
        
        try:
            if not context.parcel_id:
                return AgentResult.failure_result(
                    error="parcel_id required",
                    error_code="MISSING_PARCEL_ID",
                )
            
            edge_case_type = context.edge_case_type
            
            if edge_case_type == "business_relocation":
                result = await self.handle_business_relocation(context.parcel_id)
                return self._build_business_result(result, start_time)
            
            elif edge_case_type == "partial_taking":
                result = await self.handle_partial_taking(context.parcel_id)
                return self._build_partial_result(result, start_time)
            
            elif edge_case_type == "inverse_condemnation":
                result = await self.handle_inverse_condemnation(context.parcel_id)
                return self._build_inverse_result(result, start_time)
            
            else:
                # Default: detect edge cases
                detection = await self.detect_edge_cases(context.parcel_id)
                return self._build_detection_result(detection, start_time)
            
        except Exception as e:
            self.logger.error(f"Edge case handling failed: {e}", exc_info=True)
            return AgentResult.failure_result(
                error=str(e),
                error_code="EDGE_CASE_ERROR",
            )
    
    async def detect_edge_cases(self, parcel_id: str) -> EdgeCaseDetection:
        """Detect edge cases for a parcel.
        
        Args:
            parcel_id: Parcel to analyze
            
        Returns:
            Detection result
        """
        parcel_data = await self._get_parcel_data(parcel_id)
        if not parcel_data:
            return EdgeCaseDetection([], {}, [], [f"Parcel {parcel_id} not found"])
        
        detected = []
        confidence = {}
        workflow_adjustments = []
        alerts = []
        
        # Rule-based detection
        metadata = parcel_data.get("metadata", {})
        
        # Check for business relocation
        if metadata.get("business_on_property") or metadata.get("property_type") == "commercial":
            detected.append("business_relocation")
            confidence["business_relocation"] = 0.9
            workflow_adjustments.append({
                "edge_case": "business_relocation",
                "required_steps": [
                    "Identify business type and operations",
                    "Calculate URA-compliant moving costs",
                    "Assess goodwill eligibility",
                    "Prepare relocation plan",
                ],
                "additional_documents": [
                    "Business financial statements (3 years)",
                    "Inventory list",
                    "Relocation cost estimates",
                ],
            })
        
        # Check for partial taking
        if metadata.get("taking_type") == "partial" or metadata.get("is_partial_taking"):
            detected.append("partial_taking")
            confidence["partial_taking"] = 0.9
            workflow_adjustments.append({
                "edge_case": "partial_taking",
                "required_steps": [
                    "Calculate before value",
                    "Calculate after value",
                    "Assess severance damages",
                    "Analyze remnant viability",
                ],
                "additional_documents": [
                    "Before/after appraisals",
                    "Survey showing taking area",
                    "Access analysis",
                ],
            })
        
        # Check for heritage property (MO multiplier)
        jurisdiction = parcel_data.get("jurisdiction", "TX")
        if jurisdiction == "MO":
            family_years = metadata.get("family_ownership_years", 0)
            if family_years >= 50:
                detected.append("heritage_property")
                confidence["heritage_property"] = 0.95
                alerts.append(f"Heritage property: {family_years} years family ownership qualifies for 150% multiplier")
            elif family_years >= 10 and metadata.get("owner_occupied"):
                detected.append("heritage_property")
                confidence["heritage_property"] = 0.85
                alerts.append("Homestead may qualify for 125% multiplier")
        
        # AI-assisted detection for complex cases
        ai_detection = await self._ai_detect_edge_cases(parcel_data)
        if ai_detection:
            for case_type in ai_detection.get("detected_edge_cases", []):
                if case_type not in detected:
                    detected.append(case_type)
                    confidence[case_type] = ai_detection.get("confidence", {}).get(case_type, 0.7)
            
            workflow_adjustments.extend(ai_detection.get("workflow_adjustments", []))
            alerts.extend(ai_detection.get("alerts", []))
        
        return EdgeCaseDetection(
            detected_cases=detected,
            confidence=confidence,
            workflow_adjustments=workflow_adjustments,
            alerts=alerts,
        )
    
    async def handle_business_relocation(self, parcel_id: str) -> BusinessRelocationResult:
        """Handle business relocation edge case.
        
        Args:
            parcel_id: Parcel with business
            
        Returns:
            Business relocation calculation
        """
        parcel_data = await self._get_parcel_data(parcel_id)
        if not parcel_data:
            raise ValueError(f"Parcel {parcel_id} not found")
        
        business_info = parcel_data.get("metadata", {}).get("business_info", {})
        jurisdiction = parcel_data.get("jurisdiction", "TX")
        
        # Calculate URA-compliant moving costs
        moving_costs = await self._calculate_moving_costs(business_info)
        
        # Calculate goodwill (if jurisdiction allows)
        goodwill = await self._calculate_goodwill(jurisdiction, business_info)
        
        # Calculate reestablishment costs
        reestablishment = await self._calculate_reestablishment(business_info)
        
        # Generate relocation plan
        plan = await self._generate_relocation_plan(parcel_data, business_info)
        
        total = moving_costs + goodwill + reestablishment
        
        return BusinessRelocationResult(
            moving_costs=moving_costs,
            goodwill=goodwill,
            reestablishment_costs=reestablishment,
            total_relocation=total,
            relocation_plan=plan,
            ura_compliant=True,
        )
    
    async def handle_partial_taking(self, parcel_id: str) -> PartialTakingResult:
        """Handle partial taking edge case.
        
        Args:
            parcel_id: Parcel with partial taking
            
        Returns:
            Partial taking analysis
        """
        parcel_data = await self._get_parcel_data(parcel_id)
        if not parcel_data:
            raise ValueError(f"Parcel {parcel_id} not found")
        
        metadata = parcel_data.get("metadata", {})
        
        # Get valuations
        before_value = metadata.get("before_value", 0) or parcel_data.get("appraisal_value", 0)
        taking_percent = metadata.get("taking_percent", 30)
        taking_value = before_value * (taking_percent / 100)
        
        # Estimate after value and severance
        after_value, severance, cost_to_cure = await self._calculate_severance_damages(
            parcel_data,
            before_value,
            taking_value,
        )
        
        # Analyze remnant
        is_uneconomic, analysis = await self._analyze_remnant(parcel_data, after_value)
        
        # Determine recommendation
        if is_uneconomic:
            recommendation = "full_taking"
        else:
            recommendation = "partial"
        
        return PartialTakingResult(
            before_value=before_value,
            taking_value=taking_value,
            after_value=after_value,
            severance_damages=severance,
            cost_to_cure=cost_to_cure,
            is_uneconomic_remnant=is_uneconomic,
            recommendation=recommendation,
            analysis=analysis,
        )
    
    async def handle_inverse_condemnation(self, parcel_id: str) -> dict[str, Any]:
        """Handle inverse condemnation claim detection.
        
        Args:
            parcel_id: Parcel to analyze
            
        Returns:
            Inverse condemnation analysis
        """
        parcel_data = await self._get_parcel_data(parcel_id)
        if not parcel_data:
            raise ValueError(f"Parcel {parcel_id} not found")
        
        # Analyze for inverse condemnation indicators
        indicators = []
        metadata = parcel_data.get("metadata", {})
        
        # Physical taking without formal proceedings
        if metadata.get("physical_occupation"):
            indicators.append("Physical occupation without condemnation")
        
        # Regulatory taking
        if metadata.get("regulatory_restriction"):
            indicators.append("Regulatory restrictions affecting use")
        
        # Denial of access
        if metadata.get("access_denied"):
            indicators.append("Denial of access to property")
        
        # Flooding/drainage issues
        if metadata.get("flooding_caused"):
            indicators.append("Government-caused flooding")
        
        is_inverse = len(indicators) > 0
        
        return {
            "is_inverse_condemnation": is_inverse,
            "indicators": indicators,
            "confidence": 0.8 if is_inverse else 0.3,
            "recommended_action": "File inverse condemnation claim" if is_inverse else "No action needed",
            "procedural_notes": [
                "Inverse condemnation has different procedural requirements",
                "Property owner must initiate action",
                "Different statute of limitations may apply",
            ] if is_inverse else [],
        }
    
    async def adapt_workflow(
        self,
        parcel_id: str,
        edge_case_type: str,
    ) -> dict[str, Any]:
        """Adapt workflow based on detected edge case.
        
        Args:
            parcel_id: Parcel ID
            edge_case_type: Type of edge case
            
        Returns:
            Workflow adaptations
        """
        adaptations = []
        additional_documents = []
        workflow_steps = []
        
        if edge_case_type == "business_relocation":
            adaptations = [
                "Add business valuation step",
                "Include URA compliance review",
                "Add relocation assistance workflow",
            ]
            additional_documents = [
                "Business financial statements",
                "Inventory list",
                "Moving cost estimates",
                "Goodwill calculation (if applicable)",
            ]
            workflow_steps = [
                {"step": "business_identification", "required": True},
                {"step": "ura_calculation", "required": True},
                {"step": "relocation_plan", "required": True},
            ]
        
        elif edge_case_type == "partial_taking":
            adaptations = [
                "Add before/after appraisal requirement",
                "Include severance damage calculation",
                "Add remnant analysis step",
            ]
            additional_documents = [
                "Before condition appraisal",
                "After condition appraisal",
                "Survey showing taking area",
                "Access impact analysis",
            ]
            workflow_steps = [
                {"step": "before_after_valuation", "required": True},
                {"step": "severance_calculation", "required": True},
                {"step": "remnant_analysis", "required": True},
            ]
        
        elif edge_case_type == "inverse_condemnation":
            adaptations = [
                "Switch to inverse condemnation workflow",
                "Property owner initiates action",
                "Different damage calculation",
            ]
            additional_documents = [
                "Evidence of taking",
                "Damage documentation",
                "Timeline of government action",
            ]
            workflow_steps = [
                {"step": "taking_documentation", "required": True},
                {"step": "damage_assessment", "required": True},
                {"step": "claim_filing", "required": True},
            ]
        
        return {
            "parcel_id": parcel_id,
            "edge_case_type": edge_case_type,
            "adaptations": adaptations,
            "additional_documents": additional_documents,
            "workflow_steps_added": workflow_steps,
        }
    
    async def _get_parcel_data(self, parcel_id: str) -> Optional[dict[str, Any]]:
        """Get parcel data from database."""
        if not self.db:
            return {
                "id": parcel_id,
                "jurisdiction": "TX",
                "appraisal_value": 350000,
                "metadata": {
                    "property_type": "residential",
                    "taking_type": "full",
                },
            }
        
        try:
            from app.db.models import Parcel, Project, Appraisal
            from sqlalchemy import select
            
            result = await self.db.execute(
                select(Parcel).where(Parcel.id == parcel_id)
            )
            parcel = result.scalar_one_or_none()
            
            if parcel:
                project_result = await self.db.execute(
                    select(Project).where(Project.id == parcel.project_id)
                )
                project = project_result.scalar_one_or_none()
                
                appraisal_result = await self.db.execute(
                    select(Appraisal).where(Appraisal.parcel_id == parcel_id)
                )
                appraisal = appraisal_result.scalar_one_or_none()
                
                return {
                    "id": parcel.id,
                    "jurisdiction": project.jurisdiction_code if project else "TX",
                    "appraisal_value": float(appraisal.value) if appraisal else 0,
                    "metadata": parcel.metadata_json or {},
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to fetch parcel: {e}")
            return None
    
    async def _ai_detect_edge_cases(self, parcel_data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Use AI to detect edge cases."""
        prompt = EDGE_CASE_DETECTION_PROMPT.format(
            parcel_data=str(parcel_data)[:2000],
            property_type=parcel_data.get("metadata", {}).get("property_type", "unknown"),
            taking_type=parcel_data.get("metadata", {}).get("taking_type", "full"),
            business_info=str(parcel_data.get("metadata", {}).get("business_info", {})),
            historical_context=str(parcel_data.get("metadata", {}).get("historical_context", {})),
        )
        
        return await self.call_ai(prompt, task_type="edge_case_detection")
    
    async def _calculate_moving_costs(self, business_info: dict[str, Any]) -> float:
        """Calculate URA-compliant moving costs."""
        business_type = business_info.get("type", "small_business")
        sqft = business_info.get("square_feet", 2000)
        
        # URA-based estimates
        if business_type == "residential":
            return 15000.0
        elif business_type == "small_business":
            # $10-20 per sqft for small business
            return min(sqft * 15.0, 50000.0)
        elif business_type == "large_business":
            return min(sqft * 20.0, 200000.0)
        else:
            return 25000.0
    
    async def _calculate_goodwill(
        self,
        jurisdiction: str,
        business_info: dict[str, Any],
    ) -> float:
        """Calculate business goodwill if jurisdiction allows."""
        # Check if jurisdiction allows goodwill
        config = get_jurisdiction_config(jurisdiction)
        goodwill_allowed = config.compensation.get("business_goodwill", {}).get("available", False)
        
        if not goodwill_allowed:
            return 0.0
        
        # Calculate based on net income
        net_income = business_info.get("net_income", 0)
        years = business_info.get("years_in_business", 0)
        
        if net_income > 0 and years >= 2:
            # Simple goodwill calculation: 2x average net income
            return net_income * 2
        
        return 0.0
    
    async def _calculate_reestablishment(self, business_info: dict[str, Any]) -> float:
        """Calculate reestablishment costs."""
        # URA allows up to $25,000 for reestablishment
        return min(25000.0, business_info.get("estimated_reestablishment", 10000.0))
    
    async def _generate_relocation_plan(
        self,
        parcel_data: dict[str, Any],
        business_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate business relocation plan."""
        return {
            "timeline": {
                "notice_date": None,
                "relocation_deadline": None,
                "estimated_duration_days": 90,
            },
            "requirements": [
                "Identify comparable replacement location",
                "Coordinate move to minimize business interruption",
                "Maintain records for reimbursement",
            ],
            "assistance_available": [
                "Moving cost reimbursement",
                "Search costs for new location",
                "Reestablishment expenses",
            ],
        }
    
    async def _calculate_severance_damages(
        self,
        parcel_data: dict[str, Any],
        before_value: float,
        taking_value: float,
    ) -> tuple[float, float, float]:
        """Calculate severance damages for partial taking."""
        metadata = parcel_data.get("metadata", {})
        
        # Estimate after value (simplified)
        taking_percent = metadata.get("taking_percent", 30)
        
        # Basic calculation: after value is not simply proportional
        # Severance considers impacts to remainder
        remainder_percent = (100 - taking_percent) / 100
        
        # Factors affecting after value
        access_impact = metadata.get("access_impact", 0.05)  # 5% default
        utility_impact = metadata.get("utility_impact", 0.05)  # 5% default
        
        # After value = before * remainder% * (1 - impacts)
        impact_factor = 1 - access_impact - utility_impact
        after_value = before_value * remainder_percent * impact_factor
        
        # Severance = before - taking - after
        severance = before_value - taking_value - after_value
        severance = max(0, severance)  # Cannot be negative
        
        # Cost to cure (if any)
        cost_to_cure = metadata.get("cost_to_cure", 0)
        
        return after_value, severance, cost_to_cure
    
    async def _analyze_remnant(
        self,
        parcel_data: dict[str, Any],
        after_value: float,
    ) -> tuple[bool, str]:
        """Analyze if remnant is uneconomic."""
        metadata = parcel_data.get("metadata", {})
        before_value = parcel_data.get("appraisal_value", 0)
        
        # Uneconomic remnant criteria
        is_uneconomic = False
        analysis = []
        
        # Check size
        original_size = metadata.get("lot_size_sqft", 10000)
        taking_percent = metadata.get("taking_percent", 30)
        remainder_size = original_size * (100 - taking_percent) / 100
        
        min_lot_size = metadata.get("min_lot_size", 5000)  # Zoning minimum
        if remainder_size < min_lot_size:
            is_uneconomic = True
            analysis.append(f"Remainder ({remainder_size:.0f} sqft) below minimum lot size ({min_lot_size} sqft)")
        
        # Check value ratio
        if before_value > 0:
            value_ratio = after_value / before_value
            if value_ratio < 0.3:  # Less than 30% of original value
                is_uneconomic = True
                analysis.append(f"Remainder value ({value_ratio:.1%}) is less than 30% of original")
        
        # Check access
        if metadata.get("access_lost", False):
            is_uneconomic = True
            analysis.append("Remainder would lose access")
        
        analysis_text = "; ".join(analysis) if analysis else "Remainder appears economically viable"
        
        return is_uneconomic, analysis_text
    
    def _build_business_result(
        self,
        result: BusinessRelocationResult,
        start_time: datetime,
    ) -> AgentResult:
        """Build AgentResult from business relocation."""
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return AgentResult(
            success=True,
            confidence=0.85,
            data={
                "moving_costs": result.moving_costs,
                "goodwill": result.goodwill,
                "reestablishment_costs": result.reestablishment_costs,
                "total_relocation": result.total_relocation,
                "relocation_plan": result.relocation_plan,
                "ura_compliant": result.ura_compliant,
            },
            flags=["business_relocation"],
            requires_review=True,
            audit_payload={
                "explanation": f"Business relocation: ${result.total_relocation:,.2f} total (moving: ${result.moving_costs:,.2f}, goodwill: ${result.goodwill:,.2f})",
            },
            execution_time_ms=int(execution_time),
        )
    
    def _build_partial_result(
        self,
        result: PartialTakingResult,
        start_time: datetime,
    ) -> AgentResult:
        """Build AgentResult from partial taking."""
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        flags = ["partial_taking"]
        if result.is_uneconomic_remnant:
            flags.append("uneconomic_remnant_detected")
        
        return AgentResult(
            success=True,
            confidence=0.80,
            data={
                "before_value": result.before_value,
                "taking_value": result.taking_value,
                "after_value": result.after_value,
                "severance_damages": result.severance_damages,
                "cost_to_cure": result.cost_to_cure,
                "is_uneconomic_remnant": result.is_uneconomic_remnant,
                "recommendation": result.recommendation,
                "analysis": result.analysis,
            },
            flags=flags,
            requires_review=True,
            audit_payload={
                "explanation": f"Partial taking: severance ${result.severance_damages:,.2f}, recommendation: {result.recommendation}",
            },
            execution_time_ms=int(execution_time),
        )
    
    def _build_inverse_result(
        self,
        result: dict[str, Any],
        start_time: datetime,
    ) -> AgentResult:
        """Build AgentResult from inverse condemnation."""
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        flags = []
        if result.get("is_inverse_condemnation"):
            flags.append("inverse_condemnation")
        
        return AgentResult(
            success=True,
            confidence=result.get("confidence", 0.5),
            data=result,
            flags=flags,
            requires_review=result.get("is_inverse_condemnation", False),
            audit_payload={
                "explanation": f"Inverse condemnation: {'detected' if result.get('is_inverse_condemnation') else 'not detected'}",
            },
            execution_time_ms=int(execution_time),
        )
    
    def _build_detection_result(
        self,
        detection: EdgeCaseDetection,
        start_time: datetime,
    ) -> AgentResult:
        """Build AgentResult from edge case detection."""
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return AgentResult(
            success=True,
            confidence=max(detection.confidence.values()) if detection.confidence else 0.5,
            data={
                "detected_cases": detection.detected_cases,
                "confidence": detection.confidence,
                "workflow_adjustments": detection.workflow_adjustments,
                "alerts": detection.alerts,
            },
            flags=detection.detected_cases,
            requires_review=len(detection.detected_cases) > 0,
            audit_payload={
                "explanation": f"Detected {len(detection.detected_cases)} edge cases: {', '.join(detection.detected_cases)}",
            },
            execution_time_ms=int(execution_time),
        )


# Handler classes for specific edge cases
class BusinessRelocationHandler(BaseAgent):
    """Handler for business relocation scenarios."""
    
    agent_type = AgentType.EDGE_CASE
    
    def __init__(self, db_session=None):
        super().__init__()
        self.db = db_session
        self.edge_case_agent = EdgeCaseAgent(db_session)
    
    async def execute(self, context: AgentContext) -> AgentResult:
        result = await self.edge_case_agent.handle_business_relocation(context.parcel_id)
        return self.edge_case_agent._build_business_result(result, datetime.utcnow())
    
    async def calculate_goodwill(
        self,
        parcel_id: str,
        jurisdiction: str,
        business_info: dict[str, Any],
    ) -> dict[str, Any]:
        return {"goodwill": await self.edge_case_agent._calculate_goodwill(jurisdiction, business_info)}


class PartialTakingHandler(BaseAgent):
    """Handler for partial taking scenarios."""
    
    agent_type = AgentType.EDGE_CASE
    
    def __init__(self, db_session=None):
        super().__init__()
        self.db = db_session
        self.edge_case_agent = EdgeCaseAgent(db_session)
    
    async def execute(self, context: AgentContext) -> AgentResult:
        result = await self.edge_case_agent.handle_partial_taking(context.parcel_id)
        return self.edge_case_agent._build_partial_result(result, datetime.utcnow())
    
    async def calculate_severance_damages(
        self,
        parcel_id: str,
        before_value: float,
        taking_area: float,
        after_conditions: dict[str, Any],
    ) -> dict[str, Any]:
        parcel_data = await self.edge_case_agent._get_parcel_data(parcel_id)
        if parcel_data:
            parcel_data["metadata"].update(after_conditions)
        taking_value = before_value * (taking_area / 100)
        after_value, severance, cost_to_cure = await self.edge_case_agent._calculate_severance_damages(
            parcel_data, before_value, taking_value
        )
        return {
            "severance_damages": severance,
            "after_value": after_value,
            "cost_to_cure": cost_to_cure,
        }


class InverseCondemnationHandler(BaseAgent):
    """Handler for inverse condemnation scenarios."""
    
    agent_type = AgentType.EDGE_CASE
    
    def __init__(self, db_session=None):
        super().__init__()
        self.db = db_session
        self.edge_case_agent = EdgeCaseAgent(db_session)
    
    async def execute(self, context: AgentContext) -> AgentResult:
        result = await self.edge_case_agent.handle_inverse_condemnation(context.parcel_id)
        return self.edge_case_agent._build_inverse_result(result, datetime.utcnow())
