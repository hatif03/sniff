"""Tests for orchestrator and related components.

These tests validate:
- State machine transitions
- Guardrail enforcement
- Diagnosis classification
- Slack alert formatting
- Report generation
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path

from src.core.state_machine import StateMachine, RunState, RunOutcome, StateTransition
from src.core.models import Observation, ActionResult, DiagnosisResult
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
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            total_steps=5,
            observations=[],
            action_results=[],
        )

        assert report.run_id == "test-123"
        assert report.outcome == RunOutcome.SUCCESS
        assert report.total_steps == 5

    def test_report_to_dict(self):
        """Test report serialization to dict."""
        start = datetime.now(timezone.utc)
        end = datetime.now(timezone.utc)

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
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
