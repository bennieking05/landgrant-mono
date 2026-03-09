"""Tests for AI agents.

This module tests the agent infrastructure and individual agents:
- Base agent classes
- Agent orchestrator
- Individual agent functionality
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.base import (
    BaseAgent,
    AgentContext,
    AgentResult,
    AgentType,
    EscalationReason,
)
from app.agents.orchestrator import (
    AgentOrchestrator,
    OrchestratedResult,
    ConsensusResult,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def agent_context():
    """Create a basic agent context."""
    return AgentContext(
        case_id="TEST-001",
        project_id="PRJ-001",
        parcel_id="PARCEL-001",
        jurisdiction="TX",
        apn="123-456-789",
        county_fips="48439",
    )


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


# =============================================================================
# Base Agent Tests
# =============================================================================

class TestAgentResult:
    """Tests for AgentResult."""

    def test_success_result(self):
        """Test creating successful result."""
        result = AgentResult.success_result(
            data={"key": "value"},
            confidence=0.95,
            flags=["flag1"],
        )
        
        assert result.success is True
        assert result.confidence == 0.95
        assert result.data == {"key": "value"}
        assert result.flags == ["flag1"]
        assert result.requires_review is False

    def test_failure_result(self):
        """Test creating failure result."""
        result = AgentResult.failure_result(
            error="Something went wrong",
            error_code="TEST_ERROR",
        )
        
        assert result.success is False
        assert result.confidence == 0.0
        assert result.error == "Something went wrong"
        assert result.error_code == "TEST_ERROR"
        assert result.requires_review is True

    def test_to_dict(self):
        """Test serialization to dict."""
        result = AgentResult(
            success=True,
            confidence=0.85,
            data={"test": True},
            flags=[],
        )
        
        d = result.to_dict()
        assert d["success"] is True
        assert d["confidence"] == 0.85
        assert d["data"] == {"test": True}


class TestAgentContext:
    """Tests for AgentContext."""

    def test_to_dict(self, agent_context):
        """Test serialization to dict."""
        d = agent_context.to_dict()
        
        assert d["case_id"] == "TEST-001"
        assert d["jurisdiction"] == "TX"
        assert "requested_at" in d

    def test_optional_fields(self):
        """Test that optional fields are excluded when None."""
        context = AgentContext(case_id="TEST-001")
        d = context.to_dict()
        
        assert "parcel_id" not in d
        assert "document_id" not in d


class TestBaseAgent:
    """Tests for BaseAgent class."""

    def test_should_escalate_low_confidence(self):
        """Test escalation for low confidence."""
        class TestAgent(BaseAgent):
            async def execute(self, context):
                pass
        
        agent = TestAgent()
        result = AgentResult(
            success=True,
            confidence=0.70,  # Below threshold
            data={},
            flags=[],
        )
        
        assert agent.should_escalate(result) is True

    def test_should_escalate_critical_flag(self):
        """Test escalation for critical flag."""
        class TestAgent(BaseAgent):
            async def execute(self, context):
                pass
        
        agent = TestAgent()
        result = AgentResult(
            success=True,
            confidence=0.95,  # Above threshold
            data={},
            flags=["constitutional_issue"],  # Critical flag
        )
        
        assert agent.should_escalate(result) is True

    def test_no_escalation_for_good_result(self):
        """Test no escalation for good result."""
        class TestAgent(BaseAgent):
            async def execute(self, context):
                pass
        
        agent = TestAgent()
        result = AgentResult(
            success=True,
            confidence=0.95,
            data={},
            flags=[],
        )
        
        assert agent.should_escalate(result) is False

    def test_get_escalation_reason(self):
        """Test getting escalation reason."""
        class TestAgent(BaseAgent):
            async def execute(self, context):
                pass
        
        agent = TestAgent()
        
        # Test low confidence
        result = AgentResult(success=True, confidence=0.5, data={}, flags=[])
        assert agent.get_escalation_reason(result) == EscalationReason.LOW_CONFIDENCE
        
        # Test constitutional issue
        result = AgentResult(success=True, confidence=0.95, data={}, flags=["constitutional_issue"])
        assert agent.get_escalation_reason(result) == EscalationReason.CONSTITUTIONAL_ISSUE


# =============================================================================
# Orchestrator Tests
# =============================================================================

class TestAgentOrchestrator:
    """Tests for AgentOrchestrator."""

    @pytest.mark.asyncio
    async def test_execute_with_oversight_auto_approve(self, agent_context):
        """Test auto-approval for high-confidence result."""
        class MockAgent(BaseAgent):
            async def execute(self, context):
                return AgentResult.success_result(
                    data={"result": "test"},
                    confidence=0.95,
                )
        
        orchestrator = AgentOrchestrator()
        result = await orchestrator.execute_with_oversight(
            MockAgent(),
            agent_context,
        )
        
        assert result.status == "approved"
        assert result.result.success is True
        assert result.escalation is None

    @pytest.mark.asyncio
    async def test_execute_with_oversight_escalation(self, agent_context):
        """Test escalation for low-confidence result."""
        class MockAgent(BaseAgent):
            async def execute(self, context):
                return AgentResult.success_result(
                    data={"result": "test"},
                    confidence=0.70,  # Below threshold
                )
        
        orchestrator = AgentOrchestrator()
        result = await orchestrator.execute_with_oversight(
            MockAgent(),
            agent_context,
        )
        
        assert result.status == "pending_review"
        assert result.escalation is not None

    @pytest.mark.asyncio
    async def test_execute_with_oversight_failure(self, agent_context):
        """Test handling of agent failure."""
        class FailingAgent(BaseAgent):
            async def execute(self, context):
                raise ValueError("Test error")
        
        orchestrator = AgentOrchestrator()
        result = await orchestrator.execute_with_oversight(
            FailingAgent(),
            agent_context,
        )
        
        assert result.status == "failed"
        assert result.result.success is False

    @pytest.mark.asyncio
    async def test_cross_verification_agreement(self, agent_context):
        """Test cross-verification with agreement."""
        class PrimaryAgent(BaseAgent):
            async def execute(self, context):
                return AgentResult.success_result(
                    data={"result": "test"},
                    confidence=0.90,
                )
        
        class VerificationAgent(BaseAgent):
            async def execute(self, context):
                return AgentResult.success_result(
                    data={"result": "verify"},
                    confidence=0.88,
                )
        
        orchestrator = AgentOrchestrator()
        result = await orchestrator.execute_with_oversight(
            PrimaryAgent(),
            agent_context,
            verification_agents=[VerificationAgent()],
        )
        
        assert result.status == "approved"

    @pytest.mark.asyncio
    async def test_cross_verification_disagreement(self, agent_context):
        """Test cross-verification with disagreement."""
        class PrimaryAgent(BaseAgent):
            async def execute(self, context):
                return AgentResult.success_result(
                    data={"result": "test"},
                    confidence=0.90,
                    flags=["flag_a"],
                )
        
        class VerificationAgent(BaseAgent):
            async def execute(self, context):
                return AgentResult.success_result(
                    data={"result": "verify"},
                    confidence=0.30,  # Very different confidence
                    flags=["flag_b", "flag_c"],  # Different flags
                )
        
        orchestrator = AgentOrchestrator()
        result = await orchestrator.execute_with_oversight(
            PrimaryAgent(),
            agent_context,
            verification_agents=[VerificationAgent()],
            require_consensus=True,
        )
        
        assert result.status == "pending_review"


# =============================================================================
# Individual Agent Tests
# =============================================================================

class TestIntakeAgent:
    """Tests for IntakeAgent."""

    @pytest.mark.asyncio
    async def test_execute_success(self, agent_context):
        """Test successful intake execution."""
        from app.agents.intake_agent import IntakeAgent
        
        agent = IntakeAgent()
        
        # Mock property service
        with patch.object(agent.property_service, 'fetch_property_data') as mock_fetch:
            from app.services.property_data_service import PropertyData
            mock_fetch.return_value = PropertyData(
                apn="123-456-789",
                county_fips="48439",
                address="123 Main St",
                owner_names=["John Doe"],
                assessed_value=350000,
                source="mock",
                confidence=0.8,
            )
            
            result = await agent.execute(agent_context)
            
            assert result.success is True
            assert "property" in result.data
            assert "eligibility" in result.data
            assert "risk" in result.data


class TestComplianceAgent:
    """Tests for ComplianceAgent."""

    @pytest.mark.asyncio
    async def test_check_case_compliance(self, agent_context):
        """Test compliance check execution."""
        from app.agents.compliance_agent import ComplianceAgent
        
        agent = ComplianceAgent()
        result = await agent.check_case_compliance("TEST-001")
        
        assert hasattr(result, 'compliant')
        assert hasattr(result, 'violations')
        assert hasattr(result, 'warnings')


class TestValuationAgent:
    """Tests for ValuationAgent."""

    @pytest.mark.asyncio
    async def test_calculate_compensation(self, agent_context):
        """Test compensation calculation."""
        from app.agents.valuation_agent import ValuationAgent
        
        agent = ValuationAgent()
        
        result = await agent.calculate_full_compensation(
            parcel_id="PARCEL-001",
            jurisdiction="TX",
            appraisal_value=350000,
        )
        
        assert result.base_fmv == 350000
        assert result.total_compensation >= result.base_fmv


class TestFilingAgent:
    """Tests for FilingAgent."""

    @pytest.mark.asyncio
    async def test_check_deadlines(self):
        """Test deadline checking."""
        from app.agents.filing_agent import FilingAgent
        
        agent = FilingAgent()
        results = await agent.check_deadlines(days_ahead=7)
        
        assert isinstance(results, list)


class TestEdgeCaseAgent:
    """Tests for EdgeCaseAgent."""

    @pytest.mark.asyncio
    async def test_detect_edge_cases(self):
        """Test edge case detection."""
        from app.agents.edge_case_agent import EdgeCaseAgent
        
        agent = EdgeCaseAgent()
        detection = await agent.detect_edge_cases("PARCEL-001")
        
        assert hasattr(detection, 'detected_cases')
        assert hasattr(detection, 'confidence')
        assert hasattr(detection, 'workflow_adjustments')


# =============================================================================
# Integration Tests
# =============================================================================

class TestAgentIntegration:
    """Integration tests for agent system."""

    @pytest.mark.asyncio
    async def test_full_intake_flow(self, agent_context):
        """Test full intake flow with orchestration."""
        from app.agents.intake_agent import IntakeAgent
        from app.agents.orchestrator import AgentOrchestrator
        
        agent = IntakeAgent()
        orchestrator = AgentOrchestrator()
        
        result = await orchestrator.execute_with_oversight(agent, agent_context)
        
        assert result.decision_id is not None
        assert result.status in ["approved", "pending_review", "failed"]

    @pytest.mark.asyncio
    async def test_compliance_with_valuation(self, agent_context):
        """Test compliance check followed by valuation."""
        from app.agents.compliance_agent import ComplianceAgent
        from app.agents.valuation_agent import ValuationAgent
        from app.agents.orchestrator import AgentOrchestrator
        
        orchestrator = AgentOrchestrator()
        
        # First compliance check
        compliance_result = await orchestrator.execute_with_oversight(
            ComplianceAgent(),
            agent_context,
        )
        
        # Then valuation if compliant
        if compliance_result.result and compliance_result.result.success:
            valuation_result = await orchestrator.execute_with_oversight(
                ValuationAgent(),
                agent_context,
            )
            assert valuation_result.decision_id is not None
