"""Report builder for run summaries and artifacts.

Generates:
- Run summary JSON
- Evidence bundles (screenshots, logs, traces)
- Terminal-friendly report output
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

from ..core.models import DiagnosisResult, Observation, ActionResult
from ..core.state_machine import RunOutcome

logger = logging.getLogger(__name__)


class RunReport:
    """Run report data structure."""

    def __init__(
        self,
        run_id: str,
        outcome: RunOutcome,
        goal: str,
        persona_name: str,
        start_time: datetime,
        end_time: datetime,
        total_steps: int,
        observations: list[Observation],
        action_results: list[ActionResult],
        diagnosis: Optional[DiagnosisResult] = None,
        artifacts_path: Optional[str] = None,
    ):
        """Initialize run report.

        Args:
            run_id: Unique run identifier
            outcome: Final run outcome
            goal: Run goal
            persona_name: Persona used
            start_time: Run start time
            end_time: Run end time
            total_steps: Total steps executed
            observations: All observations
            action_results: All action results
            diagnosis: Diagnosis result (if failed)
            artifacts_path: Path to artifacts directory
        """
        self.run_id = run_id
        self.outcome = outcome
        self.goal = goal
        self.persona_name = persona_name
        self.start_time = start_time
        self.end_time = end_time
        self.total_steps = total_steps
        self.observations = observations
        self.action_results = action_results
        self.diagnosis = diagnosis
        self.artifacts_path = artifacts_path

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary.

        Returns:
            Dictionary representation of report
        """
        duration_seconds = (self.end_time - self.start_time).total_seconds()

        # Determine success status from outcome
        success = self.outcome == RunOutcome.SUCCESS

        report = {
            "run_id": self.run_id,
            "outcome": self.outcome.value,
            "success": success,  # For backward compatibility with report command
            "goal": self.goal,
            "persona": self.persona_name,
            "timestamp": self.start_time.isoformat(),  # Primary timestamp field
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": duration_seconds,
            "steps_executed": self.total_steps,  # Alias for report command
            "total_steps": self.total_steps,
            "total_observations": len(self.observations),
            "total_actions": len(self.action_results),
            "successful_actions": len([r for r in self.action_results if r.success]),
            "failed_actions": len([r for r in self.action_results if not r.success]),
        }

        # Add starting URL if available from observations
        if self.observations:
            report["starting_url"] = self.observations[0].url
            report["final_url"] = self.observations[-1].url

        # Add diagnosis if present (with both camelCase and snake_case for compatibility)
        if self.diagnosis:
            report["diagnosis"] = {
                "rootCause": self.diagnosis.rootCause,
                "severity": self.diagnosis.severity,
                "likelyOwner": self.diagnosis.likelyOwner,
                "suggestedFix": self.diagnosis.suggestedFix,
                "reproSteps": self.diagnosis.reproSteps,
                # Snake_case aliases
                "root_cause": self.diagnosis.rootCause,
                "likely_owner": self.diagnosis.likelyOwner,
                "suggested_fix": self.diagnosis.suggestedFix,
                "repro_steps": self.diagnosis.reproSteps,
            }

        # Add artifacts path
        if self.artifacts_path:
            report["artifacts_path"] = self.artifacts_path

        # Add step details for verbose reporting
        if self.action_results:
            report["steps"] = [
                {
                    "step": i + 1,
                    "action": result.action,
                    "target": result.target,
                    "success": result.success,
                    "duration_ms": result.durationMs,
                    "error": result.error if not result.success else None,
                }
                for i, result in enumerate(self.action_results)
            ]

        return report

    def to_json(self) -> str:
        """Convert report to JSON string.

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2)

    def to_terminal_summary(self) -> str:
        """Generate terminal-friendly summary.

        Returns:
            Formatted string for terminal output
        """
        duration_seconds = (self.end_time - self.start_time).total_seconds()

        lines = [
            "=" * 80,
            f"sniff Run Report: {self.run_id}",
            "=" * 80,
            "",
            f"Outcome: {self.outcome.value.upper()}",
            f"Goal: {self.goal}",
            f"Persona: {self.persona_name}",
            f"Duration: {duration_seconds:.2f}s",
            f"Total Steps: {self.total_steps}",
            "",
        ]

        # Add action summary
        successful = len([r for r in self.action_results if r.success])
        failed = len([r for r in self.action_results if not r.success])

        lines.extend([
            "Action Summary:",
            f"  - Successful: {successful}",
            f"  - Failed: {failed}",
            "",
        ])

        # Add diagnosis if present
        if self.diagnosis:
            lines.extend([
                "Diagnosis:",
                f"  - Root Cause: {self.diagnosis.rootCause}",
                f"  - Severity: {self.diagnosis.severity}",
                f"  - Likely Owner: {self.diagnosis.likelyOwner}",
                f"  - Suggested Fix: {self.diagnosis.suggestedFix}",
                "",
            ])

            # Add repro steps
            if self.diagnosis.reproSteps:
                lines.append("Reproduction Steps:")
                for i, step in enumerate(self.diagnosis.reproSteps, 1):
                    lines.append(f"  {i}. {step}")
                lines.append("")

        # Add final URL
        if self.observations:
            lines.extend([
                f"Final URL: {self.observations[-1].url}",
                "",
            ])

        # Add artifacts path
        if self.artifacts_path:
            lines.extend([
                f"Artifacts: {self.artifacts_path}",
                "",
            ])

        lines.append("=" * 80)

        return "\n".join(lines)


class ReportBuilder:
    """Builder for run reports and evidence bundles."""

    def __init__(self, artifacts_base_path: Path):
        """Initialize report builder.

        Args:
            artifacts_base_path: Base path for artifacts storage
        """
        self.artifacts_base_path = Path(artifacts_base_path)

    def build_report(
        self,
        run_id: str,
        outcome: RunOutcome,
        goal: str,
        persona_name: str,
        start_time: datetime,
        end_time: datetime,
        observations: list[Observation],
        action_results: list[ActionResult],
        diagnosis: Optional[DiagnosisResult] = None,
    ) -> RunReport:
        """Build run report.

        Args:
            run_id: Unique run identifier
            outcome: Final run outcome
            goal: Run goal
            persona_name: Persona used
            start_time: Run start time
            end_time: Run end time
            observations: All observations
            action_results: All action results
            diagnosis: Diagnosis result (if failed)

        Returns:
            RunReport instance
        """
        artifacts_path = self.artifacts_base_path / run_id

        return RunReport(
            run_id=run_id,
            outcome=outcome,
            goal=goal,
            persona_name=persona_name,
            start_time=start_time,
            end_time=end_time,
            total_steps=len(action_results),
            observations=observations,
            action_results=action_results,
            diagnosis=diagnosis,
            artifacts_path=str(artifacts_path),
        )

    def save_report(self, report: RunReport) -> Path:
        """Save report to artifacts directory.

        Args:
            report: RunReport to save

        Returns:
            Path to saved report file
        """
        artifacts_path = self.artifacts_base_path / report.run_id
        artifacts_path.mkdir(parents=True, exist_ok=True)

        # Save JSON report
        report_path = artifacts_path / "report.json"
        with open(report_path, 'w') as f:
            f.write(report.to_json())

        logger.info(f"Saved report to {report_path}")

        return report_path

    def save_evidence_bundle(
        self,
        run_id: str,
        observations: list[Observation],
        action_results: list[ActionResult],
        diagnosis: Optional[DiagnosisResult] = None,
        reasoning_timeline: Optional[list[dict]] = None,
        persona_review: Optional[dict] = None,
    ) -> Path:
        """Save complete evidence bundle.

        Args:
            run_id: Unique run identifier
            observations: All observations
            action_results: All action results
            diagnosis: Diagnosis result
            reasoning_timeline: Agent decision reasoning timeline
            persona_review: Persona's review/evaluation of the run

        Returns:
            Path to evidence bundle directory
        """
        artifacts_path = self.artifacts_base_path / run_id
        artifacts_path.mkdir(parents=True, exist_ok=True)

        # Save observations
        observations_path = artifacts_path / "observations.json"
        with open(observations_path, 'w') as f:
            json.dump([obs.model_dump() for obs in observations], f, indent=2)

        # Save action results
        actions_path = artifacts_path / "actions.json"
        with open(actions_path, 'w') as f:
            json.dump([act.model_dump() for act in action_results], f, indent=2)

        # Save diagnosis if present
        if diagnosis:
            diagnosis_path = artifacts_path / "diagnosis.json"
            with open(diagnosis_path, 'w') as f:
                json.dump(diagnosis.model_dump(), f, indent=2)

        # Save agent reasoning timeline if present
        if reasoning_timeline:
            reasoning_path = artifacts_path / "agent_reasoning.json"
            with open(reasoning_path, 'w') as f:
                json.dump(reasoning_timeline, f, indent=2)
            logger.info(f"Saved agent reasoning timeline: {len(reasoning_timeline)} decisions")

        # Save persona review if present
        if persona_review:
            review_path = artifacts_path / "persona_review.json"
            with open(review_path, 'w') as f:
                json.dump(persona_review, f, indent=2)
            logger.info(f"Saved persona review")

        logger.info(f"Saved evidence bundle to {artifacts_path}")

        return artifacts_path

    def load_report(self, run_id: str) -> Optional[dict[str, Any]]:
        """Load report by run ID.

        Args:
            run_id: Unique run identifier

        Returns:
            Report dictionary or None if not found
        """
        report_path = self.artifacts_base_path / run_id / "report.json"

        if not report_path.exists():
            logger.warning(f"Report not found for run {run_id}")
            return None

        with open(report_path, 'r') as f:
            return json.load(f)

    def list_runs(self, limit: int = 10) -> list[dict[str, Any]]:
        """List recent runs with summary data.

        Args:
            limit: Maximum number of runs to return

        Returns:
            List of run summary dictionaries
        """
        runs = []

        if not self.artifacts_base_path.exists():
            return runs

        # Get all run directories
        run_dirs = [
            d for d in self.artifacts_base_path.iterdir()
            if d.is_dir() and (d / "report.json").exists()
        ]

        # Sort by modification time (newest first)
        run_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)

        # Load summary for each run
        for run_dir in run_dirs[:limit]:
            report_path = run_dir / "report.json"
            try:
                with open(report_path, 'r') as f:
                    report = json.load(f)
                    runs.append({
                        "run_id": report["run_id"],
                        "outcome": report["outcome"],
                        "goal": report["goal"],
                        "start_time": report["start_time"],
                        "duration_seconds": report.get("duration_seconds", 0),
                    })
            except Exception as e:
                logger.warning(f"Failed to load report from {report_path}: {e}")

        return runs


def create_report_builder(artifacts_base_path: Path) -> ReportBuilder:
    """Create ReportBuilder instance.

    Args:
        artifacts_base_path: Base path for artifacts storage

    Returns:
        Configured ReportBuilder instance
    """
    return ReportBuilder(artifacts_base_path)
