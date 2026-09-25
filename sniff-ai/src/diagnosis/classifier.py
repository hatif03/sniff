"""Diagnosis classifier for root cause and severity analysis.

Hybrid approach combining:
- Deterministic signals (HTTP errors, timeouts, console errors)
- LLM interpretation (UX issues, ambiguous failures)

Output: DiagnosisResult with root cause, severity, owner, repro steps, and suggested fix.
"""

import logging
from typing import Any, Optional
from datetime import datetime

from ..core.models import DiagnosisResult, Observation, ActionResult

logger = logging.getLogger(__name__)


class DiagnosisSignals:
    """Deterministic signals for diagnosis classification."""

    def __init__(
        self,
        observations: list[Observation],
        action_results: list[ActionResult],
        final_observation: Optional[Observation] = None,
    ):
        """Initialize signals from run data.

        Args:
            observations: All observations from run
            action_results: All action results from run
            final_observation: Final observation before failure
        """
        self.observations = observations
        self.action_results = action_results
        self.final_observation = final_observation or (observations[-1] if observations else None)

    def has_http_errors(self) -> bool:
        """Check if there are HTTP error responses."""
        if not self.final_observation:
            return False

        # Check network events for 4xx/5xx
        for event in self.final_observation.networkEvents:
            status = event.get('status')
            if status and (400 <= status < 600):
                return True

        return False

    def has_console_errors(self) -> bool:
        """Check if there are console errors."""
        if not self.final_observation:
            return False
        return len(self.final_observation.consoleErrors) > 0

    def has_timeout(self) -> bool:
        """Check if there were timeout issues."""
        # Check action results for timeouts
        for result in self.action_results[-5:]:  # Check last 5 actions
            if result.status == "timeout":
                return True

        # Check timing metrics for slow responses
        if self.final_observation:
            timing = self.final_observation.timing
            if timing.get('ttfb', 0) > 5000:  # TTFB > 5s
                return True

        return False

    def has_element_not_found(self) -> bool:
        """Check if there were element not found errors."""
        for result in self.action_results[-5:]:
            if result.status == "element_not_found":
                return True
        return False

    def has_repeated_failures(self) -> bool:
        """Check for repeated action failures (stuck pattern)."""
        if len(self.action_results) < 3:
            return False

        recent_failures = [
            r for r in self.action_results[-5:]
            if not r.success
        ]

        return len(recent_failures) >= 3

    def get_error_messages(self) -> list[str]:
        """Extract all error messages."""
        errors = []

        # Console errors
        if self.final_observation:
            errors.extend(self.final_observation.consoleErrors)

        # Action errors
        for result in self.action_results[-5:]:
            if result.error:
                errors.append(result.error)

        return errors

    def get_network_failures(self) -> list[dict]:
        """Get network failure events."""
        if not self.final_observation:
            return []

        failures = []
        for event in self.final_observation.networkEvents:
            if event.get('status', 0) >= 400:
                failures.append(event)

        return failures


class DiagnosisClassifier:
    """Classifies failures into root cause categories with severity.

    Uses hybrid approach:
    - Deterministic rules for clear signals (HTTP errors, timeouts)
    - Optional LLM interpretation for ambiguous cases
    """

    def __init__(self, owner_routing: Optional[dict[str, str]] = None):
        """Initialize classifier.

        Args:
            owner_routing: Mapping of root cause to owner team/person
        """
        self.owner_routing = owner_routing or {
            "Backend": "Backend Team",
            "UX/Content": "Product/Design Team",
            "Performance": "Infrastructure Team",
            "Integration": "Integration Team",
        }

    def classify(
        self,
        observations: list[Observation],
        action_results: list[ActionResult],
        run_goal: str,
        stuck_reason: str,
    ) -> DiagnosisResult:
        """Classify failure and generate diagnosis.

        Args:
            observations: All observations from run
            action_results: All action results from run
            run_goal: Original run goal
            stuck_reason: Reason for stuck detection

        Returns:
            DiagnosisResult with classification and recommendations
        """
        signals = DiagnosisSignals(observations, action_results)

        # Classify root cause using deterministic rules
        root_cause = self._classify_root_cause(signals, stuck_reason)

        # Determine severity
        severity = self._determine_severity(root_cause, signals, stuck_reason)

        # Build evidence bundle
        evidence = self._build_evidence(signals, observations, action_results)

        # Get likely owner
        likely_owner = self.owner_routing.get(root_cause, "Unknown Team")

        # Generate reproduction steps
        repro_steps = self._generate_repro_steps(observations, action_results, run_goal)

        # Suggest fix
        suggested_fix = self._suggest_fix(root_cause, signals, stuck_reason)

        return DiagnosisResult(
            rootCause=root_cause,
            severity=severity,
            evidence=evidence,
            likelyOwner=likely_owner,
            reproSteps=repro_steps,
            suggestedFix=suggested_fix,
        )

    def _classify_root_cause(
        self,
        signals: DiagnosisSignals,
        stuck_reason: str,
    ) -> str:
        """Classify root cause category.

        Args:
            signals: Diagnostic signals
            stuck_reason: Reason for stuck detection

        Returns:
            Root cause category
        """
        # Backend: HTTP errors, server failures
        if signals.has_http_errors():
            network_failures = signals.get_network_failures()
            for failure in network_failures:
                status = failure.get('status', 0)
                if 500 <= status < 600:
                    return "Backend"

        # Performance: Timeouts, slow responses
        if signals.has_timeout():
            return "Performance"

        # Integration: Element not found (could be backend or UX)
        # Check for upload/integration related patterns
        if signals.has_element_not_found():
            error_messages = signals.get_error_messages()
            integration_keywords = ['upload', 'file', 'document', 'integration', 'api', 'third-party']
            for msg in error_messages:
                if any(keyword in msg.lower() for keyword in integration_keywords):
                    return "Integration"

        # UX/Content: Element not found, unclear flow, stuck on navigation
        if signals.has_element_not_found() or signals.has_repeated_failures():
            return "UX/Content"

        # Backend: If we see 4xx errors (client error but often server config)
        if signals.has_http_errors():
            return "Backend"

        # Default to UX/Content for unclear cases
        return "UX/Content"

    def _determine_severity(
        self,
        root_cause: str,
        signals: DiagnosisSignals,
        stuck_reason: str,
    ) -> str:
        """Determine severity level P0-P3.

        P0: Blocking signup completion (hard failures)
        P1: Major friction, likely abandonment
        P2: Noticeable issue, workaround exists
        P3: Minor UX annoyance

        Args:
            root_cause: Classified root cause
            signals: Diagnostic signals
            stuck_reason: Reason for stuck detection

        Returns:
            Severity level: P0, P1, P2, or P3
        """
        # P0: Hard failures that block completion
        if signals.has_http_errors():
            network_failures = signals.get_network_failures()
            for failure in network_failures:
                status = failure.get('status', 0)
                if status >= 500:  # Server errors
                    return "P0"

        if "max_steps" in stuck_reason or "hard_timeout" in stuck_reason:
            # Completely stuck, blocking
            return "P0"

        # P1: Major friction
        if signals.has_timeout() and root_cause == "Performance":
            return "P1"

        if signals.has_repeated_failures():
            return "P1"

        # P2: Noticeable but possibly recoverable
        if signals.has_element_not_found():
            return "P2"

        if signals.has_console_errors():
            return "P2"

        # P3: Minor issues
        return "P3"

    def _build_evidence(
        self,
        signals: DiagnosisSignals,
        observations: list[Observation],
        action_results: list[ActionResult],
    ) -> dict[str, Any]:
        """Build evidence bundle for diagnosis.

        Args:
            signals: Diagnostic signals
            observations: All observations
            action_results: All action results

        Returns:
            Evidence dictionary
        """
        evidence = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_observations": len(observations),
            "total_actions": len(action_results),
            "failed_actions": len([r for r in action_results if not r.success]),
        }

        # Add final observation details
        if signals.final_observation:
            evidence["final_url"] = signals.final_observation.url
            evidence["final_screenshot"] = signals.final_observation.screenshotPath
            evidence["console_errors"] = signals.final_observation.consoleErrors
            evidence["network_events"] = signals.final_observation.networkEvents

        # Add error messages
        evidence["error_messages"] = signals.get_error_messages()

        # Add network failures
        evidence["network_failures"] = signals.get_network_failures()

        # Add timing metrics
        if signals.final_observation:
            evidence["timing"] = signals.final_observation.timing

        # Add last 3 action results for context
        evidence["recent_actions"] = [
            {
                "action": r.action,
                "success": r.success,
                "status": r.status,
                "target": r.target,
                "error": r.error,
            }
            for r in action_results[-3:]
        ]

        return evidence

    def _generate_repro_steps(
        self,
        observations: list[Observation],
        action_results: list[ActionResult],
        run_goal: str,
    ) -> list[str]:
        """Generate reproduction steps.

        Args:
            observations: All observations
            action_results: All action results
            run_goal: Original run goal

        Returns:
            List of reproduction steps
        """
        steps = [
            f"Goal: {run_goal}",
            f"1. Navigate to {observations[0].url if observations else 'starting URL'}",
        ]

        # Add key action steps (successful ones)
        step_num = 2
        for result in action_results:
            if result.success:
                step_desc = f"{step_num}. {result.action.upper()}"
                if result.target:
                    step_desc += f" on '{result.target}'"
                steps.append(step_desc)
                step_num += 1

            # Stop at first major failure
            if not result.success and result.status in ["timeout", "element_not_found"]:
                steps.append(f"{step_num}. FAILED: {result.action.upper()} - {result.error}")
                break

        return steps

    def _suggest_fix(
        self,
        root_cause: str,
        signals: DiagnosisSignals,
        stuck_reason: str,
    ) -> str:
        """Suggest fix based on root cause.

        Args:
            root_cause: Classified root cause
            signals: Diagnostic signals
            stuck_reason: Reason for stuck detection

        Returns:
            Suggested fix description
        """
        if root_cause == "Backend":
            if signals.has_http_errors():
                failures = signals.get_network_failures()
                if failures:
                    status = failures[0].get('status', 0)
                    return f"Fix server error (HTTP {status}). Check backend logs for root cause."
            return "Investigate backend errors and API failures."

        elif root_cause == "Performance":
            if signals.has_timeout():
                return "Optimize slow endpoints and database queries. Consider CDN for static assets."
            return "Improve page load times and response latency."

        elif root_cause == "Integration":
            return "Debug integration failure (document upload, third-party API). Check service health and credentials."

        elif root_cause == "UX/Content":
            if signals.has_element_not_found():
                return "Improve element visibility and labeling. Consider adding clearer instructions or help text."
            return "Clarify UX flow and copy. Add better signposting for next steps."

        return "Review run evidence and screenshots to identify specific issue."


def create_default_classifier() -> DiagnosisClassifier:
    """Create diagnosis classifier with default configuration.

    Returns:
        Configured DiagnosisClassifier instance
    """
    return DiagnosisClassifier()
