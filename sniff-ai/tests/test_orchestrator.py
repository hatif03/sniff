"""Tests for orchestrator and related components.

These tests validate:
- State machine transitions
- Guardrail enforcement
- Diagnosis classification
- Slack alert formatting
- Report generation
"""

import asyncio
import time
from datetime import UTC, datetime

import pytest

from src.agent.website_analyzer import create_website_analyzer
from src.core.models import ActionResult, DiagnosisResult, Observation
from src.core.orchestrator import RunOrchestrator
from src.core.persona import PersonaProfile
from src.core.state_machine import RunOutcome, RunState, StateMachine
from src.diagnosis.classifier import DiagnosisClassifier, DiagnosisSignals
from src.evidence.report_builder import RunReport


class TestStateMachine:
    """Test state machine transitions and validation."""

    def test_initial_state(self):
        """Test state machine initializes correctly."""
        sm = StateMachine(initial_state=RunState.SETUP)
        assert sm.current_state == RunState.SETUP
        assert not sm.is_terminal()
        assert sm.outcome is None

    def test_valid_transition(self):
        """Test valid state transition."""
        sm = StateMachine(initial_state=RunState.SETUP)
        sm.transition(RunState.NAVIGATE, "Setup complete")

        assert sm.current_state == RunState.NAVIGATE
        assert len(sm.transitions) == 1
        assert sm.transitions[0].from_state == RunState.SETUP
        assert sm.transitions[0].to_state == RunState.NAVIGATE

    def test_invalid_transition(self):
        """Test invalid state transition raises error."""
        sm = StateMachine(initial_state=RunState.SETUP)

        with pytest.raises(ValueError, match="Invalid transition"):
            sm.transition(RunState.DIAGNOSE, "Invalid jump")

    def test_terminal_state(self):
        """Test terminal state detection."""
        sm = StateMachine(initial_state=RunState.REPORT)
        sm.transition(RunState.DONE, "Report complete")

        assert sm.is_terminal()
        assert sm.current_state == RunState.DONE

    def test_outcome_setting(self):
        """Test setting run outcome."""
        sm = StateMachine()
        sm.set_outcome(RunOutcome.SUCCESS)

        assert sm.outcome == RunOutcome.SUCCESS

    def test_duration_calculation(self):
        """Test duration calculation."""
        sm = StateMachine()
        duration = sm.get_duration_seconds()

        assert isinstance(duration, float)
        assert duration >= 0

    def test_transition_history(self):
        """Test transition history tracking."""
        sm = StateMachine(initial_state=RunState.SETUP)
        sm.transition(RunState.NAVIGATE, "Setup complete")
        sm.transition(RunState.ACTION_EXECUTION, "Navigation complete")

        history = sm.get_transition_history()

        assert len(history) == 2
        assert history[0]["from_state"] == "SETUP"
        assert history[0]["to_state"] == "NAVIGATE"
        assert history[1]["from_state"] == "NAVIGATE"
        assert history[1]["to_state"] == "ACTION_EXECUTION"

    def test_serialization(self):
        """Test state machine serialization."""
        sm = StateMachine(initial_state=RunState.SETUP)
        sm.transition(RunState.NAVIGATE, "Test")
        sm.set_outcome(RunOutcome.SUCCESS)

        data = sm.to_dict()

        assert data["current_state"] == "NAVIGATE"
        assert data["outcome"] == "success"
        assert "start_time" in data
        assert "duration_seconds" in data
        assert len(data["transitions"]) == 1


class TestDiagnosisClassifier:
    """Test diagnosis classification logic."""

    def test_backend_classification(self):
        """Test backend error classification."""
        # Create observation with server error
        obs = Observation(
            runId="test",
            step=1,
            url="https://example.com",
            screenshotPath="/tmp/screenshot.png",
            networkEvents=[{"status": 500, "url": "https://api.example.com"}]
        )

        action_result = ActionResult(
            success=False,
            action="tap",
            status="failed",
            error="Server error",
            durationMs=100
        )

        classifier = DiagnosisClassifier()
        diagnosis = classifier.classify(
            observations=[obs],
            action_results=[action_result],
            run_goal="Test goal",
            stuck_reason="Server error"
        )

        assert diagnosis.rootCause == "Backend"
        assert diagnosis.severity == "P0"  # Server error is P0

    def test_performance_classification(self):
        """Test performance issue classification."""
        obs = Observation(
            runId="test",
            step=1,
            url="https://example.com",
            screenshotPath="/tmp/screenshot.png",
            timing={"ttfb": 6000, "domReady": 8000}  # Slow
        )

        action_result = ActionResult(
            success=False,
            action="tap",
            status="timeout",
            error="Action timeout",
            durationMs=5000
        )

        classifier = DiagnosisClassifier()
        diagnosis = classifier.classify(
            observations=[obs],
            action_results=[action_result],
            run_goal="Test goal",
            stuck_reason="Timeout"
        )

        assert diagnosis.rootCause == "Performance"
        assert diagnosis.severity == "P1"  # Performance issue is P1

    def test_ux_classification(self):
        """Test UX/Content issue classification."""
        obs = Observation(
            runId="test",
            step=1,
            url="https://example.com",
            screenshotPath="/tmp/screenshot.png",
        )

        action_results = [
            ActionResult(
                success=False,
                action="tap",
                status="element_not_found",
                error="Element not found",
                durationMs=100
            )
        ] * 3  # 3 repeated failures

        classifier = DiagnosisClassifier()
        diagnosis = classifier.classify(
            observations=[obs],
            action_results=action_results,
            run_goal="Test goal",
            stuck_reason="Element not found"
        )

        assert diagnosis.rootCause == "UX/Content"
        assert diagnosis.severity in ["P1", "P2"]  # Repeated failures

    def test_diagnostic_signals(self):
        """Test diagnostic signal detection."""
        obs = Observation(
            runId="test",
            step=1,
            url="https://example.com",
            screenshotPath="/tmp/screenshot.png",
            consoleErrors=["TypeError: undefined is not a function"],
            networkEvents=[{"status": 404, "url": "https://api.example.com"}],
            timing={"ttfb": 6000}
        )

        action_result = ActionResult(
            success=False,
            action="tap",
            status="timeout",
            durationMs=5000
        )

        signals = DiagnosisSignals([obs], [action_result], obs)

        assert signals.has_console_errors()
        assert signals.has_http_errors()
        assert signals.has_timeout()
        assert not signals.has_element_not_found()

    def test_repro_steps_generation(self):
        """Test reproduction steps generation."""
        obs1 = Observation(
            runId="test",
            step=1,
            url="https://example.com/signup",
            screenshotPath="/tmp/screenshot1.png",
        )

        obs2 = Observation(
            runId="test",
            step=2,
            url="https://example.com/form",
            screenshotPath="/tmp/screenshot2.png",
        )

        actions = [
            ActionResult(success=True, action="tap", status="success", target="Start", durationMs=100),
            ActionResult(success=True, action="type", status="success", target="email", durationMs=150),
            ActionResult(success=False, action="tap", status="element_not_found", target="Submit", error="Not found", durationMs=100),
        ]

        classifier = DiagnosisClassifier()
        diagnosis = classifier.classify(
            observations=[obs1, obs2],
            action_results=actions,
            run_goal="Complete signup",
            stuck_reason="Element not found"
        )

        assert len(diagnosis.reproSteps) >= 3
        assert diagnosis.reproSteps[0].startswith("Goal:")
        assert any("FAILED" in step for step in diagnosis.reproSteps)


class TestRunReport:
    """Test run report generation and formatting."""

    def test_report_creation(self):
        """Test report creation with basic data."""
        report = RunReport(
            run_id="test-123",
            outcome=RunOutcome.SUCCESS,
            goal="Test goal",
            persona_name="test_persona",
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            total_steps=5,
            observations=[],
            action_results=[],
        )

        assert report.run_id == "test-123"
        assert report.outcome == RunOutcome.SUCCESS
        assert report.total_steps == 5

    def test_report_to_dict(self):
        """Test report serialization to dict."""
        start = datetime.now(UTC)
        end = datetime.now(UTC)

        report = RunReport(
            run_id="test-123",
            outcome=RunOutcome.FAILURE,
            goal="Test goal",
            persona_name="test_persona",
            start_time=start,
            end_time=end,
            total_steps=10,
            observations=[],
            action_results=[],
            diagnosis=DiagnosisResult(
                rootCause="Backend",
                severity="P0",
                likelyOwner="Backend Team",
                suggestedFix="Fix server",
                reproSteps=["Step 1", "Step 2"],
                evidence={}
            )
        )

        data = report.to_dict()

        assert data["run_id"] == "test-123"
        assert data["outcome"] == "failure"
        assert data["total_steps"] == 10
        assert "diagnosis" in data
        assert data["diagnosis"]["root_cause"] == "Backend"
        assert data["diagnosis"]["severity"] == "P0"

    def test_terminal_summary(self):
        """Test terminal summary formatting."""
        report = RunReport(
            run_id="test-123",
            outcome=RunOutcome.SUCCESS,
            goal="Complete signup",
            persona_name="careful_user",
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            total_steps=8,
            observations=[],
            action_results=[
                ActionResult(success=True, action="tap", status="success", durationMs=100),
                ActionResult(success=True, action="type", status="success", durationMs=150),
            ],
        )

        summary = report.to_terminal_summary()

        assert "sniff Run Report" in summary
        assert "test-123" in summary
        assert "SUCCESS" in summary
        assert "Complete signup" in summary
        assert "careful_user" in summary
        assert "=" in summary  # ASCII border


class SlowGoalEnhancer:
    """Simulates enhance_goal()'s real, blocking LLM call with time.sleep
    (not asyncio.sleep) - a genuinely blocking call is exactly the bug."""

    def __init__(self, delay_seconds: float):
        self.delay_seconds = delay_seconds
        self.called = False

    def enhance_goal(self, original_goal, website_context, persona):
        self.called = True
        time.sleep(self.delay_seconds)
        return f"ENHANCED GOAL: {original_goal}"


class FakeNavigateWorker:
    async def navigate(self, url, timeout=30000):
        return Observation(
            runId="test-run", step=0, url=url,
            screenshotPath="/tmp/fake.png", visibleText=["hello"],
        )


def _make_bare_orchestrator() -> RunOrchestrator:
    """A RunOrchestrator built without running __init__ (which creates real
    k2-horizon/Gemini clients) - only the attributes _handle_navigate
    itself touches are set."""
    orchestrator = RunOrchestrator.__new__(RunOrchestrator)
    orchestrator.progress_callback = None
    orchestrator.observations = []
    orchestrator.enhanced_goal = None
    orchestrator.goal = "Find the signup button"
    orchestrator.persona = PersonaProfile(
        name="test_persona", display_name="Test Persona", description="A test persona.",
    )
    orchestrator.website_analyzer = create_website_analyzer()
    orchestrator.worker = FakeNavigateWorker()
    orchestrator.start_url = "https://example.com"
    orchestrator.state_machine = StateMachine(initial_state=RunState.NAVIGATE)
    orchestrator.last_url = None
    orchestrator.current_url_dwell_start = None
    return orchestrator


class TestHandleNavigateGoalEnhancement:
    """Regression tests for a real production bug found via a user-reported
    failed run: enhance_goal() (routed to k2-horizon) is a blocking call.
    Called directly inside _handle_navigate (not via run_in_executor, unlike
    every other LLM call in this codebase), it froze the single-process
    server for every other request during the call - confirmed live via
    Cloud Run logs, where a concurrent status-poll request logged 36s of
    latency for what should be an instant in-memory dict read. Because the
    dwell-time clock started right after navigate(), a merely-slow (not
    even frozen) enhancement call could also burn through the whole
    max_dwell_time budget before the agent ever got a chance to act -
    failing the run with zero steps taken and no error ever recorded."""

    @pytest.mark.asyncio
    async def test_enhance_goal_does_not_block_the_event_loop(self):
        orchestrator = _make_bare_orchestrator()
        orchestrator.goal_enhancer = SlowGoalEnhancer(delay_seconds=0.3)

        tick_count = 0

        async def tick_counter():
            nonlocal tick_count
            while True:
                tick_count += 1
                await asyncio.sleep(0.01)

        ticker = asyncio.ensure_future(tick_counter())
        await orchestrator._handle_navigate()
        ticker.cancel()

        assert orchestrator.goal_enhancer.called
        # If enhance_goal blocked the event loop for its whole 0.3s delay,
        # nothing else could run concurrently and this would be ~0.
        assert tick_count > 5

    @pytest.mark.asyncio
    async def test_dwell_clock_starts_after_goal_enhancement_not_before(self):
        orchestrator = _make_bare_orchestrator()
        orchestrator.goal_enhancer = SlowGoalEnhancer(delay_seconds=0.2)

        before = datetime.utcnow()
        await orchestrator._handle_navigate()

        assert orchestrator.current_url_dwell_start is not None
        elapsed_before_dwell_start = (orchestrator.current_url_dwell_start - before).total_seconds()
        # Must be set close to *after* the slow enhancement call, not right
        # after navigate() and before it - otherwise the guardrail budget
        # is spent on setup work the agent never got a chance to act on.
        assert elapsed_before_dwell_start >= 0.2

    @pytest.mark.asyncio
    async def test_transitions_to_action_execution_after_enhancement(self):
        orchestrator = _make_bare_orchestrator()
        orchestrator.goal_enhancer = SlowGoalEnhancer(delay_seconds=0.05)

        await orchestrator._handle_navigate()

        assert orchestrator.state_machine.current_state == RunState.ACTION_EXECUTION
        assert orchestrator.enhanced_goal == "ENHANCED GOAL: Find the signup button"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
