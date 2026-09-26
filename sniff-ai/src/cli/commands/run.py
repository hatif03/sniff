"""sniff run command - Execute autonomous test runs."""

import uuid
from datetime import datetime
from pathlib import Path

import questionary
import typer
from rich.console import Console
from rich.panel import Panel

from ...core.config import get_config
from ...core.persona import PersonaProfile

console = Console()


def run_command(
    goal: str | None = typer.Option(
        None,
        "--goal",
        "-g",
        help="User-defined test goal (required)"
    ),
    persona: str | None = typer.Option(
        None,
        "--persona",
        "-p",
        help="Persona to use for testing"
    ),
    url: str | None = typer.Option(
        None,
        "--url",
        "-u",
        help="Starting URL (overrides config)"
    ),
    device: str | None = typer.Option(
        None,
        "--device",
        "-d",
        help="Device profile (e.g., 'iPhone 13')"
    ),
    network: str | None = typer.Option(
        None,
        "--network",
        "-n",
        help="Network profile (4g|3g|slow3g)"
    ),
    headless: bool = typer.Option(
        True,
        "--headless/--headed",
        help="Run browser in headless mode"
    ),
    max_steps: int | None = typer.Option(
        None,
        "--max-steps",
        help="Override max steps guardrail"
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt"
    ),
):
    """Execute autonomous test run with AI-driven navigation.

    Requires a user-defined goal to drive the agent's decisions and
    determine when the test is complete.

    Examples:

        sniff run --goal "Complete signup with document upload"

        sniff run --persona confused_first_time_user \\
                     --goal "Create account and verify email"

        sniff run --goal "Complete onboarding" \\
                     --device "iPhone 14" \\
                     --network 3g
    """

    console.print(Panel.fit(
        "[bold cyan]sniff Test Run[/bold cyan]\n"
        "Autonomous mystery shopper execution",
        border_style="cyan"
    ))

    # Load configuration
    try:
        config = get_config()
    except Exception as e:
        console.print(f"[red]Error loading configuration:[/red] {e}")
        console.print("Run [cyan]sniff init[/cyan] first to set up configuration.")
        raise typer.Exit(1)

    # Validate configuration
    validation_errors = config.validate_required()
    if validation_errors:
        console.print("[red]Configuration validation failed:[/red]")
        for error in validation_errors:
            console.print(f"  - {error}")
        console.print("\nRun [cyan]sniff init[/cyan] to fix configuration.")
        raise typer.Exit(1)

    # REQUIRED: Get goal (either from flag or interactive prompt)
    if not goal:
        console.print("\n[yellow]Goal is required for test execution.[/yellow]")
        goal = questionary.text(
            "What is the goal of this test run?",
            validate=lambda x: len(x) > 0
        ).ask()

        if not goal:
            console.print("[red]Goal is required. Exiting.[/red]")
            raise typer.Exit(1)

    # Get persona (from flag, default, or interactive)
    personas_dir = Path(config.personas_path)
    available_personas = PersonaProfile.list_available(personas_dir)

    if not available_personas:
        console.print("[yellow]No personas found. Creating defaults...[/yellow]")
        from ...core.persona import create_default_personas
        create_default_personas(personas_dir)
        available_personas = PersonaProfile.list_available(personas_dir)

    if not persona:
        if config.defaults.persona and config.defaults.persona in available_personas:
            persona = config.defaults.persona
        else:
            persona = questionary.select(
                "Select persona:",
                choices=available_personas
            ).ask()

    # Load persona
    try:
        persona_profile = PersonaProfile.load(persona, personas_dir)
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] Persona '{persona}' not found.")
        console.print("Available personas:")
        for p in available_personas:
            console.print(f"  - {p}")
        raise typer.Exit(1)

    # Get URL (from flag, config, or interactive)
    if not url:
        # Check for staging URL in allowed domains
        if config.security.allowed_domains:
            url = f"https://{config.security.allowed_domains[0]}"
        else:
            url = questionary.text(
                "Starting URL:",
                validate=lambda x: x.startswith('http')
            ).ask()

    # Apply defaults
    device = device or config.defaults.device
    network = network or config.defaults.network
    max_steps_limit = max_steps or config.guardrails.max_steps

    # Generate run ID
    run_id = f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    # Display run configuration
    console.print("\n[bold]Run Configuration:[/bold]")
    console.print(f"  Run ID: [cyan]{run_id}[/cyan]")
    console.print(f"  Goal: [yellow]{goal}[/yellow]")
    console.print(f"  Persona: [cyan]{persona_profile.display_name}[/cyan]")
    console.print(f"  Starting URL: {url}")
    console.print(f"  Device: {device}")
    console.print(f"  Network: {network}")
    console.print(f"  Max steps: {max_steps_limit}")
    console.print(f"  Headless: {headless}")

    # Confirm execution
    if not yes:
        if not questionary.confirm("\nProceed with test run?", default=True).ask():
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0)

    console.print("\n[bold green]Starting test run...[/bold green]")

    # Import orchestrator here to avoid circular imports
    try:
        from ...core.orchestrator import SyncOrchestrator

        def update_progress(message: str):
            """Callback to update progress display."""
            # Print progress messages directly to console
            console.print(f"  {message}")

        # Create orchestrator with progress callback
        orchestrator = SyncOrchestrator(
            config=config,
            run_id=run_id,
            goal=goal,
            persona=persona_profile,
            starting_url=url,
            device=device,
            network=network,
            headless=headless,
            max_steps=max_steps_limit,
            progress_callback=update_progress,
        )

        # Execute run with progress updates
        console.print("\n[bold]Test Execution:[/bold]")
        result = orchestrator.execute()

        # Display result summary
        console.print("\n" + "="*60)
        if result.get("success"):
            console.print("[bold green]✓ Test run completed successfully[/bold green]")
        else:
            console.print("[bold red]✗ Test run failed[/bold red]")

        console.print(f"\nRun ID: [cyan]{run_id}[/cyan]")
        console.print(f"Steps executed: {result.get('steps_executed', 0)}")
        console.print(f"Duration: {result.get('duration_seconds', 0):.1f}s")

        if result.get('diagnosis'):
            console.print("\nDiagnosis:")
            console.print(f"  Root cause: {result['diagnosis'].get('rootCause', 'Unknown')}")
            console.print(f"  Severity: {result['diagnosis'].get('severity', 'Unknown')}")

        # Show artifact paths
        artifact_path = Path(config.artifacts_path) / run_id
        if artifact_path.exists():
            console.print(f"\nArtifacts saved to: [cyan]{artifact_path}[/cyan]")

        console.print("\nView full report with: [cyan]sniff report {run_id}[/cyan]")

    except ImportError as e:
        console.print("[red]Error:[/red] Orchestrator not yet implemented.")
        console.print("[yellow]The orchestrator module is still being developed.[/yellow]")
        console.print(f"Details: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error during test run:[/red] {e}")
        raise typer.Exit(1)
