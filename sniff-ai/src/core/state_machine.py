"""State machine for orchestrator runtime flow.

Defines states, transitions, and state management for autonomous run execution.

States:
- SETUP: Initialize run, load config, bootstrap worker
- NAVIGATE: Navigate to starting URL
- ACTION_EXECUTION: Execute agent decision
- EVALUATE_PROGRESS: Check goal completion and progress
- STUCK_DETECTED: Detect stuck/looping/timeout conditions
- DIAGNOSE: Run diagnosis engine on failure
- ALERT: Send Slack alert with evidence
- REPORT: Generate final report artifacts
- DONE: Terminal state (success or failure)
"""

from enum import Enum
from typing import Optional
from datetime import datetime, timezone


class RunState(str, Enum):
    """Orchestrator run states."""
    SETUP = "SETUP"
    NAVIGATE = "NAVIGATE"
    ACTION_EXECUTION = "ACTION_EXECUTION"
    EVALUATE_PROGRESS = "EVALUATE_PROGRESS"
    STUCK_DETECTED = "STUCK_DETECTED"
    DIAGNOSE = "DIAGNOSE"
    ALERT = "ALERT"
    REPORT = "REPORT"
    DONE = "DONE"


class RunOutcome(str, Enum):
    """Final run outcomes."""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ABORTED = "aborted"
    ERROR = "error"


class StateTransition:
    """Represents a state transition with metadata."""

    def __init__(
        self,
        from_state: RunState,
        to_state: RunState,
        reason: str,
        timestamp: Optional[datetime] = None,
    ):
        """Initialize state transition.

        Args:
            from_state: Source state
            to_state: Destination state
            reason: Reason for transition
            timestamp: When transition occurred
        """
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }


class StateMachine:
    """State machine for orchestrator execution flow.

    Manages state transitions, validates transitions, and tracks history.
    """

    # Valid state transitions
    VALID_TRANSITIONS = {
        RunState.SETUP: {RunState.NAVIGATE, RunState.DONE},  # Can fail during setup
        RunState.NAVIGATE: {RunState.ACTION_EXECUTION, RunState.STUCK_DETECTED, RunState.DONE},
        RunState.ACTION_EXECUTION: {RunState.EVALUATE_PROGRESS, RunState.STUCK_DETECTED, RunState.DONE},
        RunState.EVALUATE_PROGRESS: {RunState.ACTION_EXECUTION, RunState.STUCK_DETECTED, RunState.DONE},
        RunState.STUCK_DETECTED: {RunState.DIAGNOSE},
        RunState.DIAGNOSE: {RunState.ALERT, RunState.REPORT},  # Can skip alert if no webhook
        RunState.ALERT: {RunState.REPORT},
        RunState.REPORT: {RunState.DONE},
        RunState.DONE: set(),  # Terminal state
    }

    def __init__(self, initial_state: RunState = RunState.SETUP):
        """Initialize state machine.

        Args:
            initial_state: Starting state (default: SETUP)
        """
        self.current_state = initial_state
        self.transitions: list[StateTransition] = []
        self.outcome: Optional[RunOutcome] = None
        self.start_time = datetime.now(timezone.utc)

    def transition(self, to_state: RunState, reason: str) -> None:
        """Transition to a new state.

        Args:
            to_state: Target state
            reason: Reason for transition

        Raises:
            ValueError: If transition is invalid
        """
        # Validate transition
        if to_state not in self.VALID_TRANSITIONS.get(self.current_state, set()):
            raise ValueError(
                f"Invalid transition from {self.current_state} to {to_state}. "
                f"Valid transitions: {self.VALID_TRANSITIONS.get(self.current_state, set())}"
            )

        # Record transition
        transition = StateTransition(
            from_state=self.current_state,
            to_state=to_state,
            reason=reason,
        )
        self.transitions.append(transition)

        # Update state
        self.current_state = to_state

    def is_terminal(self) -> bool:
        """Check if current state is terminal.

        Returns:
            True if in DONE state
        """
        return self.current_state == RunState.DONE

    def set_outcome(self, outcome: RunOutcome) -> None:
        """Set final run outcome.

        Args:
            outcome: Run outcome
        """
        self.outcome = outcome

    def get_duration_seconds(self) -> float:
        """Get total duration of state machine execution.

        Returns:
            Duration in seconds
        """
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()

    def get_transition_history(self) -> list[dict]:
        """Get full transition history.

        Returns:
            List of transition dictionaries
        """
        return [t.to_dict() for t in self.transitions]

    def to_dict(self) -> dict:
        """Convert state machine to dictionary for logging.

        Returns:
            Dictionary representation
        """
        return {
            "current_state": self.current_state.value,
            "outcome": self.outcome.value if self.outcome else None,
            "start_time": self.start_time.isoformat(),
            "duration_seconds": self.get_duration_seconds(),
            "transitions": self.get_transition_history(),
        }
