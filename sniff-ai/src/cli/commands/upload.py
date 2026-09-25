"""Sherlock upload command - Upload run artifacts to Supabase."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...core.config import get_config
from ...core.models import Observation, ActionResult, DiagnosisResult

console = Console()

# Import Supabase uploader (optional)
try:
    from ...integrations.supabase_client import SupabaseUploader
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False


def upload_command(
    run_id: Optional[str] = typer.Argument(
        None,
        help="Run ID to upload (latest if not specified)"
    ),
    all_runs: bool = typer.Option(
        False,
        "--all",
        help="Upload all runs"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force re-upload even if already uploaded"
    ),
):
    """Upload test run artifacts to Supabase.

    Uploads screenshots, videos, traces to Supabase Storage and
    structured data (observations, actions, reasoning, reviews) to Supabase Database.

    Examples:

        sherlock upload

        sherlock upload run_20260207_123456_abc123

        sherlock upload --all
    """

    if not HAS_SUPABASE:
        console.print("[red]Error:[/red] Supabase integration not available.")
        console.print("Install with: [cyan]pip install supabase[/cyan]")
        raise typer.Exit(1)

    config = get_config()
    artifacts_path = Path(config.artifacts_path)

    # Check if Supabase is configured
    supabase_url = config.supabase.url if hasattr(config, 'supabase') else None
    supabase_key = config.supabase.key if hasattr(config, 'supabase') else None

    if not supabase_url or not supabase_key:
        console.print("[red]Error:[/red] Supabase not configured.")
        console.print("Set SUPABASE_URL and SUPABASE_KEY in .env or run [cyan]sherlock init[/cyan]")
        raise typer.Exit(1)

    # Initialize uploader
    try:
        uploader = SupabaseUploader(supabase_url=supabase_url, supabase_key=supabase_key)
        console.print("[green]✓[/green] Connected to Supabase")

        # Ensure buckets exist
        if not uploader.ensure_buckets_exist():
            console.print("[yellow]Warning:[/yellow] Failed to create storage buckets")

    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to initialize Supabase: {e}")
        raise typer.Exit(1)

    # Determine which runs to upload
    if all_runs:
        run_dirs = [d for d in artifacts_path.iterdir() if d.is_dir() and (d / "report.json").exists()]
        console.print(f"Found {len(run_dirs)} runs to upload")
    else:
        if not run_id:
            # Find latest run
            run_dirs = sorted(
                [d for d in artifacts_path.iterdir() if d.is_dir() and (d / "report.json").exists()],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )

            if not run_dirs:
                console.print("[yellow]No test runs found.[/yellow]")
                raise typer.Exit(0)

            run_dirs = [run_dirs[0]]
            console.print(f"Uploading latest run: {run_dirs[0].name}")
        else:
            run_dir = artifacts_path / run_id
            if not run_dir.exists():
                console.print(f"[red]Error:[/red] Run '{run_id}' not found.")
                raise typer.Exit(1)
            run_dirs = [run_dir]

    # Upload each run
    success_count = 0
    fail_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        for run_dir in run_dirs:
            task = progress.add_task(f"Uploading {run_dir.name}...", total=None)

            try:
                # Load run data
                report = _load_json(run_dir / "report.json")
                observations = _load_observations(run_dir / "observations.json")
                actions = _load_actions(run_dir / "actions.json")
                diagnosis = _load_diagnosis(run_dir / "diagnosis.json")
                reasoning = _load_json(run_dir / "agent_reasoning.json")
                persona_review = _load_json(run_dir / "persona_review.json")

                if not report:
                    console.print(f"[yellow]Skipping {run_dir.name}: No report found[/yellow]")
                    fail_count += 1
                    continue

                # Parse timestamps
                from datetime import datetime
                start_time = datetime.fromisoformat(report['start_time'])
                end_time = datetime.fromisoformat(report['end_time'])

                # Upload to Supabase
                result = uploader.upload_run(
                    run_id=run_dir.name,
                    artifacts_dir=run_dir,
                    goal=report['goal'],
                    persona_name=report['persona'],
                    outcome=report['outcome'],
                    start_time=start_time,
                    end_time=end_time,
                    observations=observations,
                    action_results=actions,
                    diagnosis=diagnosis,
                    reasoning_timeline=reasoning,
                    persona_review=persona_review,
                )

                if result.get('success'):
                    console.print(f"[green]✓[/green] Uploaded {run_dir.name}")
                    if result.get('public_url'):
                        console.print(f"  View at: [cyan]{result['public_url']}[/cyan]")
                    success_count += 1
                else:
                    console.print(f"[red]✗[/red] Failed to upload {run_dir.name}: {result.get('error')}")
                    fail_count += 1

                progress.remove_task(task)

            except Exception as e:
                console.print(f"[red]✗[/red] Error uploading {run_dir.name}: {e}")
                fail_count += 1
                progress.remove_task(task)

    # Summary
    console.print()
    console.print(f"Upload complete: [green]{success_count} succeeded[/green], [red]{fail_count} failed[/red]")


def _load_json(path: Path) -> Optional[dict]:
    """Load JSON file if it exists."""
    if not path.exists():
        return None
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return None


def _load_observations(path: Path) -> list[Observation]:
    """Load observations from JSON file."""
    data = _load_json(path)
    if not data:
        return []
    try:
        return [Observation.model_validate(obs) for obs in data]
    except Exception:
        return []


def _load_actions(path: Path) -> list[ActionResult]:
    """Load action results from JSON file."""
    data = _load_json(path)
    if not data:
        return []
    try:
        return [ActionResult.model_validate(act) for act in data]
    except Exception:
        return []


def _load_diagnosis(path: Path) -> Optional[DiagnosisResult]:
    """Load diagnosis from JSON file."""
    data = _load_json(path)
    if not data:
        return None
    try:
        return DiagnosisResult.model_validate(data)
    except Exception:
        return None
