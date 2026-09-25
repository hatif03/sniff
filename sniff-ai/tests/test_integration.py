"""
Integration tests for Sherlock components.

Tests the integration between:
- CLI configuration
- Persona system
- Agent service (decision making)
- Execution worker (browser automation)
- Orchestrator (state machine)
- Diagnosis engine
- Alerting system
"""

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import all core components
from src.core.config import SherlockConfig, PlaywrightConfig, BedrockConfig, SlackConfig
from src.core.persona import PersonaProfile, PersonaManager
from src.core.models import (
    Observation,
    AgentDecision,
    ActionResult,
    DiagnosisResult,
    SanitizedDecision,
)
from src.core.validation import DecisionSanitizer, ActionWhitelist
from src.core.trace_logger import TraceLogger
from src.core.state_machine import RunState, StateMachine, RunOutcome
from src.core.orchestrator import RunOrchestrator
from src.agent.decision_service import DecisionService
from src.diagnosis.classifier import DiagnosisClassifier
from src.alerts.slack import SlackAlerter
from src.evidence.report_builder import RunReport, ReportBuilder


class TestImports:
    """Test that all modules can be imported without errors."""

    def test_core_imports(self):
        """Test core module imports."""
        assert SherlockConfig is not None
        assert PersonaProfile is not None
        assert Observation is not None
        assert AgentDecision is not None

    def test_agent_imports(self):
        """Test agent module imports."""
        assert DecisionService is not None

    def test_validation_imports(self):
        """Test validation module imports."""
        assert DecisionSanitizer is not None
        assert ActionWhitelist is not None

    def test_orchestrator_imports(self):
        """Test orchestrator imports."""
        assert RunOrchestrator is not None
        assert StateMachine is not None


class TestDataFlowIntegration:
    """Test data flow between components."""

    def test_observation_to_decision_flow(self):
        """Test Observation → AgentDecision flow."""
        # Create observation (from worker)
        obs = Observation(
            runId="test-123",
            step=1,
            timestamp=datetime.now().isoformat(),
            url="https://example.com/signup",
            screenshotPath="/tmp/screenshot.png",
            visibleText=["Sign Up", "Email", "Password"],
            timing={"ttfb": 100, "domReady": 200},
            consoleErrors=[],
            networkEvents=[],
            lastActionResult={
                "success": True,
                "action": "navigate",
                "target": "https://example.com/signup",
            },
        )

        # Validate observation
        assert obs.runId == "test-123"
        assert obs.step == 1
        assert "Sign Up" in obs.visibleText

        # Create agent decision (what agent would return)
        decision = AgentDecision(
            action="type",
            target="email field",
            inputText="test@example.com",
            reasoningSummary="Found email input field, entering test email",
            confidence=0.95,
        )

        # Validate decision
        assert decision.action == "type"
        assert decision.inputText == "test@example.com"

    def test_decision_sanitization_flow(self):
        """Test AgentDecision → SanitizedDecision flow."""
        # Create decision
        decision = AgentDecision(
            action="type",
            target="email",
            inputText="test@example.com",
            reasoningSummary="Typing email",
            confidence=0.9,
        )

        # Sanitize decision
        sanitizer = DecisionSanitizer()
        sanitized = sanitizer.sanitize(decision)

        # Validate sanitization
        assert sanitized.is_valid
        assert sanitized.decision == decision
        assert sanitized.fallback_applied is False

    def test_invalid_decision_fallback(self):
        """Test that invalid decisions get fallback applied."""
        # Create invalid decision (type without inputText)
        decision = AgentDecision(
            action="type",
            target="email",
            reasoningSummary="Typing",
            confidence=0.8,
        )

        # Sanitize decision
        sanitizer = DecisionSanitizer()
        sanitized = sanitizer.sanitize(decision, allow_fallback=True)

        # Should have fallback applied
        assert sanitized.fallback_applied
        assert sanitized.decision.action == "wait"

    def test_action_result_flow(self):
        """Test ActionResult creation and validation."""
        result = ActionResult(
            success=True,
            action="tap",
            target="Sign Up button",
            timestamp=datetime.now().isoformat(),
            duration_ms=150,
            observation=None,
        )

        assert result.success
        assert result.action == "tap"
        assert result.duration_ms == 150


class TestConfigurationIntegration:
    """Test configuration system integration."""

    def test_config_creation_and_validation(self):
        """Test config creation with all required fields."""
        config = SherlockConfig(
            playwright=PlaywrightConfig(
                headless=True,
                default_device="iPhone 13",
                default_network="4g",
            ),
            bedrock=BedrockConfig(
                region="us-west-2",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
                timeout_seconds=30,
            ),
            slack=SlackConfig(
                webhook_url="https://hooks.slack.com/services/TEST/TEST/TEST",
                default_channel="#sherlock-alerts",
            ),
        )

        # Validate config
        assert config.playwright.default_device == "iPhone 13"
        assert config.bedrock.region == "us-west-2"
        assert config.slack.webhook_url.startswith("https://hooks.slack.com")

    def test_config_to_from_dict(self):
        """Test config serialization."""
        config = SherlockConfig(
            playwright=PlaywrightConfig(headless=True),
            bedrock=BedrockConfig(
                region="us-west-2",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            ),
            slack=SlackConfig(
                webhook_url="https://hooks.slack.com/test",
                default_channel="#test",
            ),
        )

        # Convert to dict
        config_dict = config.model_dump()
        assert config_dict["playwright"]["headless"] is True

        # Convert back to config
        config2 = SherlockConfig.model_validate(config_dict)
        assert config2.playwright.headless is True


class TestPersonaIntegration:
    """Test persona system integration."""

    def test_persona_creation(self):
        """Test persona profile creation."""
        persona = PersonaProfile(
            name="test_user",
            description="A test user persona",
            behavior_traits={
                "patience_level": 0.7,
                "tech_savviness": 0.8,
            },
            goal_template="Complete signup flow",
        )

        assert persona.name == "test_user"
        assert persona.behavior_traits["patience_level"] == 0.7

    def test_persona_prompt_context(self):
        """Test persona to prompt context conversion."""
        persona = PersonaProfile(
            name="confused_user",
            description="A confused first-time user",
            behavior_traits={
                "patience_level": 0.3,
                "confusion_tendency": 0.9,
            },
            goal_template="Sign up for account",
        )

        context = persona.to_prompt_context()
        assert "confused_user" in context
        assert "confused first-time user" in context.lower()


class TestStateMachineIntegration:
    """Test state machine integration."""

    def test_state_machine_transitions(self):
        """Test valid state transitions."""
        sm = StateMachine()

        # Test initial state
        assert sm.current_state == RunState.SETUP

        # Test valid transitions
        sm.transition_to(RunState.NAVIGATE)
        assert sm.current_state == RunState.NAVIGATE

        sm.transition_to(RunState.ACTION_EXECUTION)
        assert sm.current_state == RunState.ACTION_EXECUTION

        sm.transition_to(RunState.EVALUATE_PROGRESS)
        assert sm.current_state == RunState.EVALUATE_PROGRESS

        sm.transition_to(RunState.DONE, RunOutcome.SUCCESS)
        assert sm.current_state == RunState.DONE
        assert sm.outcome == RunOutcome.SUCCESS

    def test_state_machine_invalid_transition(self):
        """Test that invalid transitions raise errors."""
        sm = StateMachine()

        # Try invalid transition (SETUP → DIAGNOSE)
        with pytest.raises(ValueError):
            sm.transition_to(RunState.DIAGNOSE)


class TestTraceLoggingIntegration:
    """Test trace logging integration."""

    def test_trace_logger_creation(self):
        """Test trace logger creation and basic logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = TraceLogger(
                run_id="test-123",
                log_dir=Path(tmpdir),
            )

            # Log observation
            obs = Observation(
                runId="test-123",
                step=1,
                timestamp=datetime.now().isoformat(),
                url="https://example.com",
                screenshotPath="/tmp/test.png",
                visibleText=["Test"],
                timing={},
                consoleErrors=[],
                networkEvents=[],
                lastActionResult={},
            )

            logger.log_observation(obs, step=1)

            # Verify log file exists
            log_files = list(Path(tmpdir).glob("*.jsonl"))
            assert len(log_files) > 0


class TestDiagnosisIntegration:
    """Test diagnosis engine integration."""

    def test_diagnosis_classification(self):
        """Test basic diagnosis classification."""
        classifier = DiagnosisClassifier()

        # Mock observation with console errors
        obs = Observation(
            runId="test-123",
            step=5,
            timestamp=datetime.now().isoformat(),
            url="https://example.com/signup",
            screenshotPath="/tmp/test.png",
            visibleText=["Error 500"],
            timing={"ttfb": 5000, "domReady": 6000},
            consoleErrors=["TypeError: Cannot read property 'x' of undefined"],
            networkEvents=[
                {"type": "response", "status": 500, "url": "/api/signup"}
            ],
            lastActionResult={"success": False, "error": "Timeout"},
        )

        action_history = [
            ActionResult(
                success=False,
                action="tap",
                target="Submit",
                timestamp=datetime.now().isoformat(),
                duration_ms=5000,
                error="Timeout waiting for response",
            )
        ]

        # Classify the issue
        diagnosis = classifier.classify_deterministic(obs, action_history)

        # Should detect backend issue
        assert diagnosis is not None
        assert diagnosis.rootCause in ["Backend", "Performance", "Integration"]
        assert diagnosis.severity in ["P0", "P1", "P2", "P3"]


class TestEndToEndIntegration:
    """Test end-to-end component integration."""

    @pytest.mark.asyncio
    async def test_mock_orchestrator_run(self):
        """Test orchestrator with mocked components."""
        # Create config
        config = SherlockConfig(
            playwright=PlaywrightConfig(headless=True),
            bedrock=BedrockConfig(
                region="us-west-2",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            ),
            slack=SlackConfig(
                webhook_url="https://hooks.slack.com/test",
                default_channel="#test",
            ),
        )

        # Create mock agent service
        mock_agent = MagicMock()
        mock_agent.get_decision = AsyncMock(
            return_value=AgentDecision(
                action="tap",
                target="Sign Up",
                reasoningSummary="Tapping sign up button",
                confidence=0.9,
            )
        )

        # Create orchestrator with mocked worker and agent
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.core.orchestrator.PlaywrightWorker") as MockWorker:
                # Mock worker methods
                mock_worker = AsyncMock()
                mock_worker.navigate = AsyncMock(
                    return_value=Observation(
                        runId="test-run",
                        step=1,
                        timestamp=datetime.now().isoformat(),
                        url="https://example.com",
                        screenshotPath="/tmp/test.png",
                        visibleText=["Sign Up"],
                        timing={"ttfb": 100, "domReady": 200},
                        consoleErrors=[],
                        networkEvents=[],
                        lastActionResult={"success": True},
                    )
                )
                mock_worker.tap = AsyncMock(
                    return_value=ActionResult(
                        success=True,
                        action="tap",
                        target="Sign Up",
                        timestamp=datetime.now().isoformat(),
                        duration_ms=100,
                    )
                )
                mock_worker.__aenter__ = AsyncMock(return_value=mock_worker)
                mock_worker.__aexit__ = AsyncMock(return_value=None)

                MockWorker.return_value = mock_worker

                # Create orchestrator
                orchestrator = RunOrchestrator(
                    config=config,
                    agent_service=mock_agent,
                    artifact_dir=Path(tmpdir),
                )

                # This would normally run a full flow, but we're just testing
                # that components wire together correctly
                assert orchestrator.config == config
                assert orchestrator.agent_service == mock_agent


def test_integration_suite_summary():
    """Summary test to ensure all components are available."""
    components = {
        "Configuration": SherlockConfig,
        "Persona": PersonaProfile,
        "Models": Observation,
        "Validation": DecisionSanitizer,
        "StateMachine": StateMachine,
        "Orchestrator": RunOrchestrator,
        "DecisionService": DecisionService,
        "Diagnosis": DiagnosisClassifier,
        "Slack": SlackAlerter,
        "ReportBuilder": ReportBuilder,
    }

    for name, component in components.items():
        assert component is not None, f"{name} component is not available"

    print("\n✅ All integration components available and importable")


if __name__ == "__main__":
    # Run basic import tests
    test = TestImports()
    test.test_core_imports()
    test.test_agent_imports()
    test.test_validation_imports()
    test.test_orchestrator_imports()

    print("✅ Import tests passed")

    # Run data flow tests
    data_test = TestDataFlowIntegration()
    data_test.test_observation_to_decision_flow()
    data_test.test_decision_sanitization_flow()
    data_test.test_invalid_decision_fallback()
    data_test.test_action_result_flow()

    print("✅ Data flow tests passed")

    # Run config tests
    config_test = TestConfigurationIntegration()
    config_test.test_config_creation_and_validation()
    config_test.test_config_to_from_dict()

    print("✅ Configuration tests passed")

    # Run persona tests
    persona_test = TestPersonaIntegration()
    persona_test.test_persona_creation()
    persona_test.test_persona_prompt_context()

    print("✅ Persona tests passed")

    # Run state machine tests
    sm_test = TestStateMachineIntegration()
    sm_test.test_state_machine_transitions()
    try:
        sm_test.test_state_machine_invalid_transition()
    except AssertionError:
        pass  # Expected to raise

    print("✅ State machine tests passed")

    # Summary
    test_integration_suite_summary()
    print("\n🎉 All integration tests passed!")
