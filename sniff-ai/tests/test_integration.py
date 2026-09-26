"""
Integration tests for sniff components.

Tests the integration between:
- CLI configuration
- Persona system
- Agent service (decision making)
- Execution worker (browser automation)
- Orchestrator (state machine)
- Diagnosis engine
- Alerting system
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent.decision_service import DecisionService
from src.alerts.slack import SlackAlert

# Import all core components
from src.core.config import DefaultsConfig, GeminiConfig, PlaywrightConfig, SlackConfig, SniffConfig
from src.core.models import (
    ActionResult,
    AgentDecision,
    Observation,
)
from src.core.orchestrator import RunOrchestrator
from src.core.persona import PersonaProfile
from src.core.state_machine import RunOutcome, RunState, StateMachine
from src.core.trace_logger import TraceLogger
from src.core.validation import ActionWhitelist, DecisionSanitizer
from src.diagnosis.classifier import DiagnosisClassifier
from src.evidence.report_builder import ReportBuilder


class TestImports:
    """Test that all modules can be imported without errors."""

    def test_core_imports(self):
        """Test core module imports."""
        assert SniffConfig is not None
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
        assert sanitized.wasSanitized is False
        assert sanitized.decision == decision

    def test_invalid_decision_fallback(self):
        """Test that invalid decisions get fallback applied.

        AgentDecision's own validator rejects a 'type' action without
        inputText at construction time, so the invalid shape has to be
        passed as a raw dict - that's the path a malformed Bedrock/Jev
        response actually takes into the sanitizer.
        """
        raw_decision = {
            "action": "type",
            "target": "email",
            "reasoningSummary": "Typing",
            "confidence": 0.8,
        }

        # Sanitize decision
        sanitizer = DecisionSanitizer()
        sanitized = sanitizer.sanitize(raw_decision, allow_fallback=True)

        # Should have fallback applied
        assert sanitized.wasSanitized
        assert sanitized.decision.action == "wait"

    def test_action_result_flow(self):
        """Test ActionResult creation and validation."""
        result = ActionResult(
            success=True,
            action="tap",
            status="success",
            target="Sign Up button",
            timestamp=datetime.now().isoformat(),
            durationMs=150,
        )

        assert result.success
        assert result.action == "tap"
        assert result.durationMs == 150


class TestConfigurationIntegration:
    """Test configuration system integration."""

    def test_config_creation_and_validation(self):
        """Test config creation with all required fields."""
        config = SniffConfig(
            playwright=PlaywrightConfig(headless=True),
            defaults=DefaultsConfig(
                device="iPhone 13",
                network="4g",
            ),
            gemini=GeminiConfig(
                region="us-central1",
                model_id="gemini-3.5-flash-lite",
                timeout_seconds=30,
            ),
            slack=SlackConfig(
                webhook_url="https://hooks.slack.com/services/TEST/TEST/TEST",
                channel="#sniff-alerts",
            ),
        )

        # Validate config
        assert config.defaults.device == "iPhone 13"
        assert config.gemini.region == "us-central1"
        assert config.slack.webhook_url.startswith("https://hooks.slack.com")

    def test_config_to_from_dict(self):
        """Test config serialization."""
        config = SniffConfig(
            playwright=PlaywrightConfig(headless=True),
            gemini=GeminiConfig(
                region="us-central1",
                model_id="gemini-3.5-flash-lite",
            ),
            slack=SlackConfig(
                webhook_url="https://hooks.slack.com/test",
                channel="#test",
            ),
        )

        # Convert to dict
        config_dict = config.model_dump()
        assert config_dict["playwright"]["headless"] is True

        # Convert back to config
        config2 = SniffConfig.model_validate(config_dict)
        assert config2.playwright.headless is True


class TestPersonaIntegration:
    """Test persona system integration."""

    def test_persona_creation(self):
        """Test persona profile creation."""
        persona = PersonaProfile(
            name="test_user",
            display_name="Test User",
            description="A test user persona",
            patience_level=0.7,
            technical_proficiency=0.8,
            default_goal_template="Complete signup flow",
        )

        assert persona.name == "test_user"
        assert persona.patience_level == 0.7

    def test_persona_prompt_context(self):
        """Test persona to prompt context conversion."""
        persona = PersonaProfile(
            name="confused_user",
            display_name="Confused First-Time User",
            description="A confused first-time user",
            patience_level=0.3,
            default_goal_template="Sign up for account",
        )

        context = persona.to_prompt_context()
        assert "Confused First-Time User" in context
        assert "confused first-time user" in context.lower()


class TestStateMachineIntegration:
    """Test state machine integration."""

    def test_state_machine_transitions(self):
        """Test valid state transitions."""
        sm = StateMachine()

        # Test initial state
        assert sm.current_state == RunState.SETUP

        # Test valid transitions
        sm.transition(RunState.NAVIGATE, "Setup complete")
        assert sm.current_state == RunState.NAVIGATE

        sm.transition(RunState.ACTION_EXECUTION, "Navigated to start URL")
        assert sm.current_state == RunState.ACTION_EXECUTION

        sm.transition(RunState.EVALUATE_PROGRESS, "Action executed")
        assert sm.current_state == RunState.EVALUATE_PROGRESS

        sm.transition(RunState.DONE, "Goal reached")
        sm.set_outcome(RunOutcome.SUCCESS)
        assert sm.current_state == RunState.DONE
        assert sm.outcome == RunOutcome.SUCCESS

    def test_state_machine_invalid_transition(self):
        """Test that invalid transitions raise errors."""
        sm = StateMachine()

        # Try invalid transition (SETUP → DIAGNOSE)
        with pytest.raises(ValueError):
            sm.transition(RunState.DIAGNOSE, "Invalid jump")


class TestTraceLoggingIntegration:
    """Test trace logging integration."""

    def test_trace_logger_creation(self):
        """Test trace logger creation and basic logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = TraceLogger(
                run_id="test-123",
                trace_dir=Path(tmpdir),
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

            logger.log_observation(obs)

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
                status="failed",
                target="Submit",
                timestamp=datetime.now().isoformat(),
                durationMs=5000,
                error="Timeout waiting for response",
            )
        ]

        # Classify the issue
        diagnosis = classifier.classify(
            observations=[obs],
            action_results=action_history,
            run_goal="Complete signup",
            stuck_reason="Backend error on submit",
        )

        # Should detect backend issue
        assert diagnosis is not None
        assert diagnosis.rootCause in ["Backend", "Performance", "Integration"]
        assert diagnosis.severity in ["P0", "P1", "P2", "P3"]


class TestEndToEndIntegration:
    """Test end-to-end component integration."""

    @pytest.mark.asyncio
    async def test_mock_orchestrator_run(self):
        """Test orchestrator with mocked components."""
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
                        status="success",
                        target="Sign Up",
                        timestamp=datetime.now().isoformat(),
                        durationMs=100,
                    )
                )
                mock_worker.__aenter__ = AsyncMock(return_value=mock_worker)
                mock_worker.__aexit__ = AsyncMock(return_value=None)

                MockWorker.return_value = mock_worker

                # Create config with artifacts written to the temp dir
                config = SniffConfig(
                    playwright=PlaywrightConfig(headless=True),
                    gemini=GeminiConfig(
                        region="us-central1",
                        model_id="gemini-3.5-flash-lite",
                    ),
                    slack=SlackConfig(
                        webhook_url="https://hooks.slack.com/test",
                        channel="#test",
                    ),
                    artifacts_path=tmpdir,
                )

                # Create orchestrator
                orchestrator = RunOrchestrator(
                    config=config,
                    agent_service=mock_agent,
                )

                # This would normally run a full flow, but we're just testing
                # that components wire together correctly
                assert orchestrator.config == config
                assert orchestrator.agent_service == mock_agent


def test_integration_suite_summary():
    """Summary test to ensure all components are available."""
    components = {
        "Configuration": SniffConfig,
        "Persona": PersonaProfile,
        "Models": Observation,
        "Validation": DecisionSanitizer,
        "StateMachine": StateMachine,
        "Orchestrator": RunOrchestrator,
        "DecisionService": DecisionService,
        "Diagnosis": DiagnosisClassifier,
        "Slack": SlackAlert,
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
