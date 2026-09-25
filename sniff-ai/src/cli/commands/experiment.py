"""CLI commands for running experiments with multiple personas."""

import asyncio
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from ...core.config import get_config
from ...core.experiment_orchestrator import ExperimentOrchestrator
from ...core.persona import PersonaProfile
from pathlib import Path

app = typer.Typer(help="Manage and run experiments with multiple personas")
console = Console()


@app.command("run")
def run_experiment(
    name: str = typer.Option(..., "--name", "-n", help="Experiment name"),
    goal: str = typer.Option(..., "--goal", "-g", help="Test goal (required)"),
    personas: List[str] = typer.Option(
        None,
        "--persona",
        "-p",
        help="Personas to test (can specify multiple times)",
    ),
    all_personas: bool = typer.Option(
        False, "--all", help="Run with all available personas"
    ),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Experiment description"
    ),
    url: Optional[str] = typer.Option(
        None, "--url", "-u", help="Starting URL (overrides config)"
    ),
    device: Optional[str] = typer.Option(
        None, "--device", help="Device profile (e.g., 'iPhone 13')"
    ),
    network: Optional[str] = typer.Option(
        None, "--network", help="Network profile (4g|3g|slow3g)"
    ),
    max_steps: Optional[int] = typer.Option(
        None, "--max-steps", help="Override max steps guardrail"
    ),
    headless: bool = typer.Option(True, "--headless/--headed", help="Browser mode"),
    parallel: bool = typer.Option(
        True,
        "--parallel/--sequential",
        help="Run personas in parallel or sequentially",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Run an experiment with multiple personas.

    An experiment runs the same test goal with different personas to compare
    how different user types experience your signup flow.

    Examples:

        # Run with specific personas
        sherlock experiment run --name "Signup Flow Test" \\
                                --goal "Complete signup" \\
                                --persona impatient_user \\
                                --persona confused_first_time_user

        # Run with all available personas
        sherlock experiment run --name "Full UX Audit" \\
                                --goal "Complete onboarding" \\
                                --all

        # Run in parallel for faster results
        sherlock experiment run --name "Quick Test" \\
                                --goal "Sign up" \\
                                --all \\
                                --parallel
    """
    try:
        # Load config
        config = get_config()

        # Determine personas to use
        if all_personas:
            personas_dir = Path(config.personas_path)
            persona_list = PersonaProfile.list_available(personas_dir)
            if not persona_list:
                console.print(
                    "[red]No personas found. Create personas first with 'sherlock personas add'[/red]"
                )
                raise typer.Exit(1)
        elif personas:
            persona_list = personas
        else:
            console.print(
                "[red]Error: Specify personas with --persona or use --all[/red]"
            )
            raise typer.Exit(1)

        # Display experiment plan
        console.print("\n[bold cyan]Experiment Configuration[/bold cyan]")
        console.print(f"  Name: {name}")
        console.print(f"  Goal: {goal}")
        console.print(f"  Personas: {', '.join(persona_list)}")
        console.print(f"  Mode: {'Parallel' if parallel else 'Sequential'}")
        if url:
            console.print(f"  URL: {url}")
        if device:
            console.print(f"  Device: {device}")
        if network:
            console.print(f"  Network: {network}")
        console.print(f"  Total runs: {len(persona_list)}")

        # Confirm
        if not yes:
            confirm = typer.confirm("\nProceed with experiment?")
            if not confirm:
                console.print("[yellow]Experiment cancelled.[/yellow]")
                raise typer.Exit(0)

        # Create orchestrator
        orchestrator = ExperimentOrchestrator(config)

        # Create experiment
        experiment = orchestrator.create_experiment(
            name=name,
            goal=goal,
            personas=persona_list,
            description=description,
            url=url,
            device=device,
            network=network,
            max_steps=max_steps,
            headless=headless,
            parallel=parallel,
        )

        console.print(f"\n[dim]Experiment ID: {experiment.experiment_id}[/dim]\n")

        # Run experiment
        result = asyncio.run(orchestrator.run_experiment(experiment))

        # Display results
        orchestrator.display_results(result)

        console.print(
            f"[green]✓ View detailed report with: sherlock experiment show {result.experiment_id}[/green]"
        )

    except KeyboardInterrupt:
        console.print("\n[yellow]Experiment interrupted by user.[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_experiments():
    """
    List all experiments.

    Shows a summary of all experiments with their results.
    """
    try:
        config = get_config()
        orchestrator = ExperimentOrchestrator(config)

        experiments = orchestrator.list_experiments()

        if not experiments:
            console.print("[yellow]No experiments found.[/yellow]")
            console.print(
                "\nRun your first experiment with: sherlock experiment run --help"
            )
            return

        # Display table
        table = Table(title="Experiments")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="white")
        table.add_column("Personas", style="yellow")
        table.add_column("Success Rate", style="green")
        table.add_column("Created", style="dim")

        for exp in experiments:
            table.add_row(
                exp.experiment_id[:16] + "...",
                exp.name,
                str(exp.total_runs),
                f"{exp.success_rate:.1f}%",
                exp.created_at.strftime("%Y-%m-%d %H:%M") if exp.created_at else "N/A",
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("show")
def show_experiment(
    experiment_id: str = typer.Argument(..., help="Experiment ID to display"),
):
    """
    Show detailed results for an experiment.

    Displays full results including persona comparisons and insights.
    """
    try:
        config = get_config()
        orchestrator = ExperimentOrchestrator(config)

        result = orchestrator.load_experiment(experiment_id)

        if not result:
            console.print(f"[red]Experiment '{experiment_id}' not found.[/red]")
            raise typer.Exit(1)

        orchestrator.display_results(result)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("compare")
def compare_personas(
    experiment_id: str = typer.Argument(..., help="Experiment ID to analyze"),
):
    """
    Compare persona results from an experiment.

    Shows detailed comparison of how different personas performed.
    """
    try:
        config = get_config()
        orchestrator = ExperimentOrchestrator(config)

        result = orchestrator.load_experiment(experiment_id)

        if not result:
            console.print(f"[red]Experiment '{experiment_id}' not found.[/red]")
            raise typer.Exit(1)

        console.print(f"\n[bold cyan]Persona Comparison: {result.name}[/bold cyan]\n")

        # Create comparison table
        table = Table(title="Persona Performance")
        table.add_column("Persona", style="cyan")
        table.add_column("Outcome", style="white")
        table.add_column("Duration", style="yellow")
        table.add_column("Steps", style="white")
        table.add_column("Status", style="white")

        for run in sorted(result.runs, key=lambda r: r.duration_seconds or 999999):
            outcome_emoji = "✓" if run.outcome == "success" else "✗"
            outcome_style = "green" if run.outcome == "success" else "red"

            table.add_row(
                run.persona,
                f"{run.outcome} {outcome_emoji}",
                f"{run.duration_seconds:.1f}s" if run.duration_seconds else "N/A",
                str(run.steps_executed) if run.steps_executed else "N/A",
                run.status,
            )

        console.print(table)

        # Key findings
        console.print("\n[bold cyan]Key Findings:[/bold cyan]")

        if result.insights:
            insights = result.insights
            if insights.get("fastest_persona"):
                console.print(f"  🏃 Fastest completion: {insights['fastest_persona']}")
            if insights.get("slowest_persona"):
                console.print(f"  🐌 Slowest completion: {insights['slowest_persona']}")

            recommendations = insights.get("recommendations", [])
            if recommendations:
                console.print("\n[bold cyan]Recommendations:[/bold cyan]")
                for rec in recommendations:
                    console.print(f"  {rec}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
