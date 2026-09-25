"""Structured trace logging for agent-worker execution flow.

This module provides step-by-step execution logging for:
- Agent decisions
- Worker actions
- Sanitization events
- Validation failures
- Fallback activations

Logs are structured for easy debugging and demo transparency.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .models import AgentDecision, ActionResult, Observation, SanitizedDecision

logger = logging.getLogger(__name__)


class TraceLogger:
    """Structured logger for agent-worker execution traces.

    Maintains a timeline of all decisions, actions, and outcomes per run.
    """

    def __init__(self, run_id: str, trace_dir: Optional[Path] = None):
        """Initialize trace logger for a run.

        Args:
            run_id: Unique identifier for the run
            trace_dir: Directory to store trace logs. If None, uses default.
        """
        self.run_id = run_id
        self.trace_dir = trace_dir or Path("artifacts") / run_id / "traces"
        self.trace_dir.mkdir(parents=True, exist_ok=True)

        self.trace_file = self.trace_dir / "execution_trace.jsonl"
        self.step_count = 0

    def log_observation(self, observation: Observation) -> None:
        """Log an observation from worker.

        Args:
            observation: Observation captured by worker
        """
        self._write_trace_entry({
            "event_type": "observation",
            "step": observation.step,
            "timestamp": observation.timestamp,
            "url": observation.url,
            "screenshot_path": observation.screenshotPath,
            "visible_text_count": len(observation.visibleText),
            "console_errors_count": len(observation.consoleErrors),
            "network_events_count": len(observation.networkEvents),
            "last_action_result": observation.lastActionResult,
        })

    def log_agent_decision(
        self,
        decision: AgentDecision,
        step: int,
        confidence_threshold: Optional[float] = None,
    ) -> None:
        """Log a decision from agent.

        Args:
            decision: Decision made by agent
            step: Current step number
            confidence_threshold: Optional confidence threshold for flagging
        """
        entry = {
            "event_type": "agent_decision",
            "step": step,
            "timestamp": datetime.utcnow().isoformat(),
            "action": decision.action,
            "target": decision.target,
            "reasoning": decision.reasoningSummary,
            "confidence": decision.confidence,
        }

        # Add action-specific fields
        if decision.inputText:
            entry["input_text"] = decision.inputText
        if decision.scrollDirection:
            entry["scroll_direction"] = decision.scrollDirection
        if decision.waitDurationMs:
            entry["wait_duration_ms"] = decision.waitDurationMs
        if decision.abortReason:
            entry["abort_reason"] = decision.abortReason

        # Flag low confidence decisions
        if confidence_threshold and decision.confidence < confidence_threshold:
            entry["low_confidence_warning"] = True

        # Log fallback action if present
        if decision.fallbackAction:
            entry["has_fallback"] = True
            entry["fallback_action"] = decision.fallbackAction.action

        self._write_trace_entry(entry)

    def log_sanitization(
        self,
        sanitized: SanitizedDecision,
        step: int,
    ) -> None:
        """Log decision sanitization event.

        Args:
            sanitized: Sanitized decision result
            step: Current step number
        """
        if not sanitized.wasSanitized:
            # No sanitization needed, just log validation success
            self._write_trace_entry({
                "event_type": "validation_success",
                "step": step,
                "timestamp": datetime.utcnow().isoformat(),
                "action": sanitized.decision.action,
            })
            return

        # Sanitization occurred
        self._write_trace_entry({
            "event_type": "sanitization",
            "step": step,
            "timestamp": datetime.utcnow().isoformat(),
            "original_action": sanitized.originalAction,
            "sanitized_action": sanitized.decision.action,
            "reason": sanitized.sanitizationReason,
            "fallback_applied": True,
        })

    def log_action_result(
        self,
        result: ActionResult,
        step: int,
    ) -> None:
        """Log result of action execution.

        Args:
            result: Action execution result
            step: Current step number
        """
        entry = {
            "event_type": "action_result",
            "step": step,
            "timestamp": result.timestamp,
            "action": result.action,
            "status": result.status,
            "success": result.success,
            "duration_ms": result.durationMs,
        }

        if result.target:
            entry["target"] = result.target
        if result.error:
            entry["error"] = result.error
        if result.screenshotPath:
            entry["screenshot_path"] = result.screenshotPath

        self._write_trace_entry(entry)

    def log_validation_error(
        self,
        error: Exception,
        raw_decision: dict,
        step: int,
    ) -> None:
        """Log validation error from malformed decision.

        Args:
            error: Validation error that occurred
            raw_decision: Raw decision that failed validation
            step: Current step number
        """
        self._write_trace_entry({
            "event_type": "validation_error",
            "step": step,
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "raw_decision": raw_decision,
        })

    def log_fallback_activation(
        self,
        reason: str,
        original_action: Optional[str],
        fallback_action: str,
        step: int,
    ) -> None:
        """Log fallback policy activation.

        Args:
            reason: Reason for fallback
            original_action: Original action that failed
            fallback_action: Fallback action being used
            step: Current step number
        """
        self._write_trace_entry({
            "event_type": "fallback_activation",
            "step": step,
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason,
            "original_action": original_action,
            "fallback_action": fallback_action,
        })

    def log_whitelist_violation(
        self,
        action: str,
        step: int,
    ) -> None:
        """Log action whitelist violation.

        Args:
            action: Action that violated whitelist
            step: Current step number
        """
        self._write_trace_entry({
            "event_type": "whitelist_violation",
            "step": step,
            "timestamp": datetime.utcnow().isoformat(),
            "blocked_action": action,
        })

    def log_step_summary(
        self,
        step: int,
        duration_ms: int,
        success: bool,
        notes: Optional[str] = None,
    ) -> None:
        """Log summary for completed step.

        Args:
            step: Step number
            duration_ms: Total step duration in ms
            success: Whether step succeeded
            notes: Optional notes about the step
        """
        entry = {
            "event_type": "step_summary",
            "step": step,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_ms": duration_ms,
            "success": success,
        }

        if notes:
            entry["notes"] = notes

        self._write_trace_entry(entry)

    def _write_trace_entry(self, entry: dict[str, Any]) -> None:
        """Write a trace entry to the trace file.

        Args:
            entry: Trace entry data to write
        """
        entry["run_id"] = self.run_id

        try:
            with open(self.trace_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

            # Also log to standard logger for real-time monitoring
            logger.info(
                f"[{entry.get('event_type')}] Step {entry.get('step')}: "
                f"{self._format_entry_summary(entry)}"
            )
        except Exception as e:
            logger.error(f"Failed to write trace entry: {e}", exc_info=True)

    def _format_entry_summary(self, entry: dict[str, Any]) -> str:
        """Format trace entry for log output.

        Args:
            entry: Trace entry data

        Returns:
            Formatted summary string
        """
        event_type = entry.get("event_type", "unknown")

        if event_type == "agent_decision":
            return f"{entry.get('action')} (confidence: {entry.get('confidence')})"
        elif event_type == "action_result":
            return f"{entry.get('action')} {entry.get('status')}"
        elif event_type == "sanitization":
            return f"{entry.get('original_action')} → {entry.get('sanitized_action')}"
        elif event_type == "validation_error":
            return f"Error: {entry.get('error_message')}"
        else:
            return json.dumps(entry)

    def get_trace_summary(self) -> dict[str, Any]:
        """Get summary of execution trace.

        Returns:
            Dictionary with trace statistics
        """
        try:
            with open(self.trace_file, "r") as f:
                entries = [json.loads(line) for line in f]

            event_counts = {}
            for entry in entries:
                event_type = entry.get("event_type", "unknown")
                event_counts[event_type] = event_counts.get(event_type, 0) + 1

            return {
                "run_id": self.run_id,
                "total_entries": len(entries),
                "event_counts": event_counts,
                "trace_file": str(self.trace_file),
            }
        except Exception as e:
            logger.error(f"Failed to generate trace summary: {e}")
            return {"error": str(e)}


def create_trace_logger(run_id: str, trace_dir: Optional[Path] = None) -> TraceLogger:
    """Create a TraceLogger for a run.

    Args:
        run_id: Unique identifier for the run
        trace_dir: Optional directory for trace files

    Returns:
        Configured TraceLogger instance
    """
    return TraceLogger(run_id=run_id, trace_dir=trace_dir)
