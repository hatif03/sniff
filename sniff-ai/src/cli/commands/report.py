"""Sherlock report command - Display run results and artifacts."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from ...core.config import get_config

console = Console()


def report_command(
    run_id: Optional[str] = typer.Argument(
        None,
        help="Run ID to display (latest if not specified)"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed report"
    ),
    format: str = typer.Option(
        "pretty",
        "--format",
        "-f",
        help="Output format: pretty|json"
    ),
):
    """Display test run results and artifacts.

    Shows run summary, diagnosis, steps executed, and artifact paths.

    Examples:

        sherlock report

        sherlock report run_20260207_123456_abc123

        sherlock report --verbose

        sherlock report --format json
    """

    config = get_config()
    artifacts_path = Path(config.artifacts_path)

    # If no run_id specified, find latest
    if not run_id:
        # Look for both new format (run_*) and old format (UUID) directories
        run_dirs = sorted(
            [d for d in artifacts_path.iterdir() if d.is_dir()],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        if not run_dirs:
            console.print("[yellow]No test runs found.[/yellow]")
            console.print("Run a test with: [cyan]sherlock run --goal 'Complete signup'[/cyan]")
            raise typer.Exit(0)

        run_id = run_dirs[0].name
        console.print(f"[dim]Using latest run: {run_id}[/dim]\n")

    # Load run artifacts
    run_dir = artifacts_path / run_id

    if not run_dir.exists():
        console.print(f"[red]Error:[/red] Run '{run_id}' not found.")
        console.print(f"Artifacts directory: {artifacts_path}")
        raise typer.Exit(1)

    # Load run report (try report.json first, fall back to summary.json for backward compatibility)
    report_file = run_dir / "report.json"
    summary_file = run_dir / "summary.json"

    if report_file.exists():
        with open(report_file, 'r') as f:
            summary = json.load(f)
    elif summary_file.exists():
        with open(summary_file, 'r') as f:
            summary = json.load(f)
    else:
        console.print(f"[yellow]Warning:[/yellow] No report.json or summary.json found for run '{run_id}'")
        console.print(f"Run may be incomplete or corrupted.")
        raise typer.Exit(1)

    # JSON output format
    if format == "json":
        console.print(json.dumps(summary, indent=2))
        return

    # Pretty output format
    console.print(Panel.fit(
        f"[bold cyan]Test Run Report[/bold cyan]\n"
        f"Run ID: {run_id}",
        border_style="cyan"
    ))

    # Basic information
    console.print("\n[bold]Run Information[/bold]")
    info_table = Table(show_header=False, box=None)
    info_table.add_column("Field", style="cyan")
    info_table.add_column("Value", style="white")

    info_table.add_row("Run ID", run_id)
    info_table.add_row("Goal", summary.get('goal', 'N/A'))
    info_table.add_row("Persona", summary.get('persona', 'N/A'))
    info_table.add_row("Starting URL", summary.get('starting_url', 'N/A'))
    info_table.add_row("Status", "[green]Success[/green]" if summary.get('success') else "[red]Failed[/red]")
    info_table.add_row("Steps executed", str(summary.get('steps_executed', 0)))
    info_table.add_row("Duration", f"{summary.get('duration_seconds', 0):.1f}s")
    info_table.add_row("Timestamp", summary.get('timestamp', 'N/A'))

    console.print(info_table)

    # Diagnosis (if failed)
    if not summary.get('success') and summary.get('diagnosis'):
        console.print("\n[bold]Diagnosis[/bold]")
        diagnosis = summary['diagnosis']

        diag_table = Table(show_header=False, box=None)
        diag_table.add_column("Field", style="cyan")
        diag_table.add_column("Value", style="white")

        severity = diagnosis.get('severity', 'Unknown')
        severity_color = {
            'P0': 'red',
            'P1': 'yellow',
            'P2': 'blue',
            'P3': 'green'
        }.get(severity, 'white')

        diag_table.add_row("Root cause", diagnosis.get('rootCause', 'Unknown'))
        diag_table.add_row("Severity", f"[{severity_color}]{severity}[/{severity_color}]")
        diag_table.add_row("Likely owner", diagnosis.get('likelyOwner', 'Unknown'))
        diag_table.add_row("Suggested fix", diagnosis.get('suggestedFix', 'N/A'))

        console.print(diag_table)

        # Reproduction steps
        if diagnosis.get('reproSteps'):
            console.print("\n[bold]Reproduction Steps:[/bold]")
            for i, step in enumerate(diagnosis['reproSteps'], 1):
                console.print(f"  {i}. {step}")

    # Step trace (verbose)
    if verbose and summary.get('steps'):
        console.print("\n[bold]Step Trace[/bold]")

        steps_table = Table(show_header=True)
        steps_table.add_column("#", style="cyan", justify="right")
        steps_table.add_column("Action", style="yellow")
        steps_table.add_column("Target", style="white")
        steps_table.add_column("Status", justify="center")
        steps_table.add_column("Duration", justify="right")

        for step in summary['steps']:
            status_icon = "✓" if step.get('success') else "✗"
            status_color = "green" if step.get('success') else "red"

            steps_table.add_row(
                str(step.get('step', '')),
                step.get('action', ''),
                step.get('target', '')[:30] if step.get('target') else '',
                f"[{status_color}]{status_icon}[/{status_color}]",
                f"{step.get('duration_ms', 0)}ms"
            )

        console.print(steps_table)

    # Persona Review (if exists)
    persona_review_file = run_dir / "persona_review.json"
    if persona_review_file.exists():
        console.print("\n[bold]Persona Review[/bold]")
        with open(persona_review_file, 'r') as f:
            review = json.load(f)

            review_table = Table(show_header=False, box=None)
            review_table.add_column("Field", style="cyan")
            review_table.add_column("Value", style="white")

            review_table.add_row("Persona", review.get('persona_display_name', 'N/A'))
            review_table.add_row("Sentiment", review.get('overall_sentiment', 'N/A'))
            review_table.add_row("Experience Rating", f"{review.get('experience_rating', 'N/A')}/10")
            review_table.add_row("Abandonment Risk", review.get('abandonment_likelihood', 'N/A'))

            console.print(review_table)

            if review.get('narrative'):
                console.print(f"\n[italic]{review['narrative']}[/italic]")

            if verbose and review.get('friction_points'):
                console.print("\n[bold]Friction Points:[/bold]")
                for i, point in enumerate(review['friction_points'], 1):
                    console.print(f"  {i}. {point}")

            if verbose and review.get('recommendations'):
                console.print("\n[bold]Recommendations:[/bold]")
                for i, rec in enumerate(review['recommendations'], 1):
                    console.print(f"  {i}. {rec}")

    # Artifacts
    console.print("\n[bold]Artifacts[/bold]")

    artifact_files = list(run_dir.glob('*'))
    if artifact_files:
        artifact_table = Table(show_header=True, box=None)
        artifact_table.add_column("File", style="cyan")
        artifact_table.add_column("Size", justify="right", style="dim")
        artifact_table.add_column("Description", style="dim")

        # Add descriptions for known artifacts
        artifact_descriptions = {
            "report.json": "Run summary and metadata",
            "observations.json": "Browser state observations",
            "actions.json": "Action execution results",
            "diagnosis.json": "Failure root cause analysis",
            "agent_reasoning.json": "Agent decision-making timeline",
            "persona_review.json": "Persona experience review",
            "trace.zip": "Playwright trace file",
        }

        for artifact in sorted(artifact_files):
            if artifact.is_file():
                size = artifact.stat().st_size
                size_str = f"{size:,} bytes" if size < 1024 else f"{size/1024:.1f} KB"
                description = artifact_descriptions.get(artifact.name, "")
                artifact_table.add_row(artifact.name, size_str, description)

        console.print(artifact_table)

        console.print(f"\nArtifact directory: [cyan]{run_dir}[/cyan]")
    else:
        console.print("[dim]No artifacts found[/dim]")

    # Evidence (if exists)
    evidence_file = run_dir / "evidence.json"
    if evidence_file.exists() and verbose:
        console.print("\n[bold]Evidence[/bold]")
        with open(evidence_file, 'r') as f:
            evidence = json.load(f)
            syntax = Syntax(json.dumps(evidence, indent=2), "json", theme="monokai")
            console.print(syntax)

    # Next steps
    if not summary.get('success'):
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("  1. Review screenshots and evidence in artifact directory")
        console.print("  2. Check Slack alerts (if configured)")
        console.print("  3. Address the diagnosed issue")
        console.print("  4. Re-run test to verify fix")
