"""Orchestrator for running experiments with multiple personas."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .config import SniffConfig
from .experiment_models import (
    ExperimentConfig,
    ExperimentInsights,
    ExperimentResult,
    ExperimentRun,
)
from .orchestrator import RunOrchestrator

console = Console()


class ExperimentOrchestrator:
    """Orchestrates experiment runs with multiple personas."""

    def __init__(self, config: SniffConfig):
        self.config = config
        self.experiments_dir = Path("experiments")
        self.experiments_dir.mkdir(exist_ok=True)

        # Full per-persona run data (RunReport + reasoning/persona-review),
        # keyed by persona name, populated as _run_single_persona completes.
        # ExperimentRun only keeps summary fields, so callers that need the
        # full result (e.g. src/api/main.py uploading each persona's run to
        # Supabase after the experiment finishes) read it from here.
        self.reports: dict[str, dict[str, Any]] = {}

    def create_experiment(
        self,
        name: str,
        goal: str,
        personas: list[str],
        description: str | None = None,
        url: str | None = None,
        device: str | None = None,
        network: str | None = None,
        max_steps: int | None = None,
        headless: bool = True,
        parallel: bool = True,
    ) -> ExperimentConfig:
        """Create a new experiment configuration."""
        experiment_id = f"exp_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"

        experiment = ExperimentConfig(
            experiment_id=experiment_id,
            name=name,
            description=description,
            goal=goal,
            url=url,
            device=device,
            network=network,
            personas=personas,
            max_steps=max_steps,
            headless=headless,
            parallel=parallel,
        )

        # Save experiment config
        self._save_experiment_config(experiment)

        return experiment

    async def run_experiment(
        self, experiment: ExperimentConfig
    ) -> ExperimentResult:
        """Execute an experiment with all personas."""
        console.print(f"\n[bold cyan]Starting Experiment: {experiment.name}[/bold cyan]")
        console.print(f"Goal: {experiment.goal}")
        console.print(f"Personas: {', '.join(experiment.personas)}")
        console.print(f"Mode: {'Parallel' if experiment.parallel else 'Sequential'}\n")

        runs: list[ExperimentRun] = []
        start_time = datetime.utcnow()

        if experiment.parallel:
            runs = await self._run_parallel(experiment)
        else:
            runs = await self._run_sequential(experiment)

        end_time = datetime.utcnow()
        total_duration = (end_time - start_time).total_seconds()

        # Aggregate results
        result = self._aggregate_results(
            experiment, runs, start_time, end_time, total_duration
        )

        # Save results
        self._save_experiment_result(result)

        return result

    async def _run_sequential(
        self, experiment: ExperimentConfig
    ) -> list[ExperimentRun]:
        """Run personas sequentially."""
        runs = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "Running personas...", total=len(experiment.personas)
            )

            for persona in experiment.personas:
                progress.update(task, description=f"Running {persona}...")

                run = await self._run_single_persona(experiment, persona)
                runs.append(run)

                progress.advance(task)

        return runs

    async def _run_parallel(
        self, experiment: ExperimentConfig
    ) -> list[ExperimentRun]:
        """Run personas in parallel with live progress display."""
        from rich.live import Live
        from rich.table import Table

        # Track progress for each persona
        persona_status = {persona: {"status": "Starting...", "step": 0} for persona in experiment.personas}

        def create_progress_table():
            """Create a table showing parallel persona progress."""
            table = Table(title="Parallel Experiment Progress", show_header=True)
            table.add_column("Persona", style="cyan", width=30)
            table.add_column("Status", style="yellow", width=50)
            table.add_column("Step", style="green", width=10)

            for persona in experiment.personas:
                status_info = persona_status[persona]
                table.add_row(
                    persona,
                    status_info["status"],
                    str(status_info["step"])
                )

            return table

        # Create progress callback for each persona
        def make_progress_callback(persona_name):
            def callback(message: str):
                # Extract step number if present in message
                import re
                step_match = re.search(r'Step (\d+)', message)
                if step_match:
                    persona_status[persona_name]["step"] = int(step_match.group(1))
                persona_status[persona_name]["status"] = message
            return callback

        # Run with live display
        with Live(create_progress_table(), console=console, refresh_per_second=4) as live:
            tasks = [
                self._run_single_persona(
                    experiment,
                    persona,
                    progress_callback=make_progress_callback(persona)
                )
                for persona in experiment.personas
            ]

            # Update display while tasks run
            async def run_with_updates():
                gather_task = asyncio.gather(*tasks)
                done = False
                while not done:
                    try:
                        # Update display
                        live.update(create_progress_table())
                        # Check if done with a very short timeout
                        await asyncio.wait_for(asyncio.shield(gather_task), timeout=0.25)
                        done = True
                    except TimeoutError:
                        # Not done yet, continue updating
                        continue
                return await gather_task

            runs = await run_with_updates()

        return list(runs)

    async def _run_single_persona(
        self, experiment: ExperimentConfig, persona: str, progress_callback=None
    ) -> ExperimentRun:
        """Run a single persona test.

        Args:
            experiment: Experiment configuration
            persona: Persona name to run
            progress_callback: Optional callback for progress updates
        """
        run_id = f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"

        experiment_run = ExperimentRun(
            experiment_id=experiment.experiment_id,
            run_id=run_id,
            persona=persona,
            status="pending",
        )

        try:
            experiment_run.status = "running"
            experiment_run.started_at = datetime.utcnow()

            # Create agent service (required for AI-driven navigation)
            from ..agent.decision_service import create_agent_service

            logger = logging.getLogger(__name__)

            agent_service = None
            try:
                # Try to create agent service (may fail if Gemini/Vertex AI not configured)
                agent_service = create_agent_service(self.config)
            except Exception as e:
                logger.warning(f"Could not create agent service for {persona}: {e}")
                logger.warning("Run will fail without AI agent")

            # Experiment sub-runs skip their own auto Supabase upload -
            # RunOrchestrator otherwise uploads unconditionally in its `run()`
            # finally block whenever config.supabase.enabled is True, which
            # would double-upload every persona once the API/caller also
            # uploads each persona's full result explicitly (see self.reports
            # below and src/api/main.py's experiment upload step).
            run_config = self.config.model_copy(deep=True)
            run_config.supabase.enabled = False

            # Create orchestrator for this run with agent service and progress callback
            orchestrator = RunOrchestrator(
                run_config,
                agent_service=agent_service,
                progress_callback=progress_callback
            )

            # Determine start URL
            start_url = experiment.url or self.config.primary_url
            if not start_url:
                raise ValueError("No URL specified in experiment or configuration")

            # Execute run using the orchestrator's run method
            report = await orchestrator.run(
                goal=experiment.goal,
                start_url=start_url,
                persona_name=persona,
                device_name=experiment.device,
            )

            self.reports[persona] = {
                "report": report,
                "reasoning_timeline": orchestrator.reasoning_timeline,
                "persona_review": orchestrator.persona_review,
            }

            experiment_run.completed_at = datetime.utcnow()
            experiment_run.duration_seconds = (
                experiment_run.completed_at - experiment_run.started_at
            ).total_seconds()
            experiment_run.outcome = report.outcome.value if hasattr(report.outcome, 'value') else str(report.outcome)
            experiment_run.steps_executed = report.total_steps  # Use total_steps, not steps_executed
            experiment_run.status = "completed"
            experiment_run.run_id = report.run_id  # Use actual run ID from report

        except Exception as e:
            experiment_run.status = "failed"
            experiment_run.error = str(e)
            experiment_run.completed_at = datetime.utcnow()
            if experiment_run.started_at:
                experiment_run.duration_seconds = (
                    experiment_run.completed_at - experiment_run.started_at
                ).total_seconds()

        return experiment_run

    def _aggregate_results(
        self,
        experiment: ExperimentConfig,
        runs: list[ExperimentRun],
        start_time: datetime,
        end_time: datetime,
        total_duration: float,
    ) -> ExperimentResult:
        """Aggregate results from all runs."""
        successful_runs = sum(
            1 for r in runs if r.status == "completed" and r.outcome == "success"
        )
        failed_runs = len(runs) - successful_runs

        avg_duration = (
            sum(r.duration_seconds or 0 for r in runs) / len(runs) if runs else 0
        )

        result = ExperimentResult(
            experiment_id=experiment.experiment_id,
            name=experiment.name,
            goal=experiment.goal,
            total_runs=len(runs),
            successful_runs=successful_runs,
            failed_runs=failed_runs,
            total_duration_seconds=total_duration,
            average_duration_seconds=avg_duration,
            runs=runs,
            created_at=start_time,
            completed_at=end_time,
        )

        # Generate insights
        insights = self._generate_insights(experiment, runs)
        result.insights = insights.model_dump()

        return result

    def _generate_insights(
        self, experiment: ExperimentConfig, runs: list[ExperimentRun]
    ) -> ExperimentInsights:
        """Generate insights from experiment results."""
        insights = ExperimentInsights(experiment_id=experiment.experiment_id)

        # Find fastest/slowest personas
        completed_runs = [r for r in runs if r.duration_seconds is not None]
        if completed_runs:
            fastest = min(completed_runs, key=lambda r: r.duration_seconds)
            slowest = max(completed_runs, key=lambda r: r.duration_seconds)
            insights.fastest_persona = fastest.persona
            insights.slowest_persona = slowest.persona

        # Find most successful persona
        successful_runs = [r for r in runs if r.outcome == "success"]
        if successful_runs:
            # For now, use fastest successful run
            most_successful = min(successful_runs, key=lambda r: r.duration_seconds)
            insights.most_successful_persona = most_successful.persona

        # Generate recommendations
        insights.recommendations = self._generate_recommendations(runs)

        return insights

    def _generate_recommendations(self, runs: list[ExperimentRun]) -> list[str]:
        """Generate recommendations based on experiment results."""
        recommendations = []

        successful_count = sum(1 for r in runs if r.outcome == "success")
        total_count = len(runs)

        if successful_count == 0:
            recommendations.append(
                "❌ Critical: No personas completed successfully - major flow issues detected"
            )
        elif successful_count < total_count / 2:
            recommendations.append(
                "⚠️  Warning: Less than 50% success rate - significant friction points exist"
            )
        elif successful_count == total_count:
            recommendations.append(
                "✅ Excellent: All personas completed successfully"
            )

        # Check duration variance
        durations = [r.duration_seconds for r in runs if r.duration_seconds]
        if durations and len(durations) > 1:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            if max_duration > avg_duration * 2:
                recommendations.append(
                    "⚠️  Large variance in completion times - some personas struggle more"
                )

        return recommendations

    def _save_experiment_config(self, experiment: ExperimentConfig):
        """Save experiment configuration to disk."""
        exp_dir = self.experiments_dir / experiment.experiment_id
        exp_dir.mkdir(exist_ok=True, parents=True)

        config_path = exp_dir / "config.json"
        with open(config_path, "w") as f:
            json.dump(experiment.model_dump(mode="json"), f, indent=2, default=str)

    def _save_experiment_result(self, result: ExperimentResult):
        """Save experiment results to disk."""
        exp_dir = self.experiments_dir / result.experiment_id
        exp_dir.mkdir(exist_ok=True, parents=True)

        result_path = exp_dir / "result.json"
        with open(result_path, "w") as f:
            json.dump(result.model_dump(mode="json"), f, indent=2, default=str)

    def load_experiment(self, experiment_id: str) -> ExperimentResult | None:
        """Load experiment results from disk."""
        result_path = self.experiments_dir / experiment_id / "result.json"
        if not result_path.exists():
            return None

        with open(result_path) as f:
            data = json.load(f)
            return ExperimentResult(**data)

    def list_experiments(self) -> list[ExperimentResult]:
        """List all experiments."""
        experiments = []

        for exp_dir in self.experiments_dir.iterdir():
            if exp_dir.is_dir():
                result = self.load_experiment(exp_dir.name)
                if result:
                    experiments.append(result)

        return sorted(experiments, key=lambda e: e.created_at, reverse=True)

    def display_results(self, result: ExperimentResult):
        """Display experiment results in a formatted table."""
        console.print(
            f"\n[bold green]✓ Experiment Complete: {result.name}[/bold green]\n"
        )

        # Summary table
        summary = Table(title="Experiment Summary")
        summary.add_column("Metric", style="cyan")
        summary.add_column("Value", style="white")

        summary.add_row("Experiment ID", result.experiment_id)
        summary.add_row("Goal", result.goal)
        summary.add_row("Total Runs", str(result.total_runs))
        summary.add_row("Successful", f"{result.successful_runs} ✓", style="green")
        summary.add_row("Failed", f"{result.failed_runs} ✗", style="red")
        summary.add_row("Success Rate", f"{result.success_rate:.1f}%")
        summary.add_row(
            "Total Duration", f"{result.total_duration_seconds:.1f}s"
        )
        summary.add_row(
            "Avg Duration", f"{result.average_duration_seconds:.1f}s"
        )

        console.print(summary)

        # Runs table
        runs_table = Table(title="\nPersona Results")
        runs_table.add_column("Persona", style="cyan")
        runs_table.add_column("Status", style="white")
        runs_table.add_column("Outcome", style="white")
        runs_table.add_column("Duration", style="white")
        runs_table.add_column("Steps", style="white")

        for run in result.runs:
            status_style = "green" if run.status == "completed" else "red"
            outcome_emoji = "✓" if run.outcome == "success" else "✗"

            runs_table.add_row(
                run.persona,
                run.status,
                f"{run.outcome} {outcome_emoji}",
                f"{run.duration_seconds:.1f}s" if run.duration_seconds else "N/A",
                str(run.steps_executed) if run.steps_executed else "N/A",
                style=status_style,
            )

        console.print(runs_table)

        # Insights
        if result.insights:
            console.print("\n[bold cyan]Insights:[/bold cyan]")
            insights_data = result.insights

            if insights_data.get("fastest_persona"):
                console.print(
                    f"  🏃 Fastest: {insights_data['fastest_persona']}"
                )
            if insights_data.get("slowest_persona"):
                console.print(f"  🐌 Slowest: {insights_data['slowest_persona']}")
            if insights_data.get("most_successful_persona"):
                console.print(
                    f"  🏆 Most Successful: {insights_data['most_successful_persona']}"
                )

            recommendations = insights_data.get("recommendations", [])
            if recommendations:
                console.print("\n[bold cyan]Recommendations:[/bold cyan]")
                for rec in recommendations:
                    console.print(f"  {rec}")

        console.print(
            f"\n[dim]Results saved to: experiments/{result.experiment_id}/[/dim]\n"
        )
