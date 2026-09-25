"""sniff demo command - Deterministic demo mode for presentations."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner
import questionary

from ...core.config import get_config
from ...core.persona import PersonaProfile

console = Console()


def demo_command(
    scenario: str = typer.Option(
        "signup_success",
        "--scenario",
        "-s",
        help="Demo scenario: signup_success|signup_failure|diagnosis_showcase"
    ),
    headless: bool = typer.Option(
        False,
        "--headless/--headed",
        help="Run browser in headless mode"
    ),
    slow: bool = typer.Option(
        False,
        "--slow",
        help="Enable slow motion for visibility"
    ),
):
    """Run deterministic demo mode for judge presentations.

    Provides reliable, repeatable test scenarios:
    - signup_success: Complete signup flow successfully
    - signup_failure: Trigger known failure for diagnosis demo
    - diagnosis_showcase: Show diagnosis and alerting capabilities

    Examples:

        sniff demo

        sniff demo --scenario signup_failure --headed

        sniff demo --scenario diagnosis_showcase --slow
    """

    console.print(Panel.fit(
        "[bold cyan]sniff Demo Mode[/bold cyan]\n"
        "Deterministic presentation mode",
        border_style="cyan"
    ))

    # Load config
    config = get_config()

    # Enable demo mode
    config.demo_mode = True

    # Apply slow motion if requested
    if slow:
        config.playwright.slow_mo = 500  # 500ms delay between actions

    # Define demo scenarios
    scenarios = {
        "signup_success": {
            "goal": "Complete signup flow successfully",
            "persona": "careful_user",
            "description": "Demonstrates successful navigation through signup with careful persona",
            "expected_outcome": "success"
        },
        "signup_failure": {
            "goal": "Complete signup with document upload",
            "persona": "impatient_user",
            "description": "Triggers failure scenario to showcase diagnosis engine",
            "expected_outcome": "failure"
        },
        "diagnosis_showcase": {
            "goal": "Complete problematic signup flow",
            "persona": "confused_first_time_user",
            "description": "Demonstrates full diagnosis, evidence collection, and Slack alerting",
            "expected_outcome": "failure"
        }
    }

    if scenario not in scenarios:
        console.print(f"[red]Error:[/red] Unknown scenario '{scenario}'")
        console.print("\nAvailable scenarios:")
        for name, details in scenarios.items():
            console.print(f"  [cyan]{name}[/cyan]: {details['description']}")
        raise typer.Exit(1)

    demo_config = scenarios[scenario]

    # Display scenario info
    console.print("\n[bold]Demo Scenario[/bold]")
    console.print(f"  Scenario: [cyan]{scenario}[/cyan]")
    console.print(f"  Description: {demo_config['description']}")
    console.print(f"  Goal: [yellow]{demo_config['goal']}[/yellow]")
    console.print(f"  Persona: [cyan]{demo_config['persona']}[/cyan]")
    console.print(f"  Expected outcome: [{'green' if demo_config['expected_outcome'] == 'success' else 'yellow'}]{demo_config['expected_outcome']}[/{'green' if demo_config['expected_outcome'] == 'success' else 'yellow'}]")
    console.print(f"  Browser mode: {'Headless' if headless else 'Headed (visible)'}")
    console.print(f"  Slow motion: {'Enabled (500ms)' if slow else 'Disabled'}")

    # Confirm execution
    console.print("\n[dim]This demo uses a deterministic path for reliable presentation.[/dim]")

    if not questionary.confirm("\nStart demo?", default=True).ask():
        console.print("[yellow]Cancelled.[/yellow]")
        raise typer.Exit(0)

    console.print("\n[bold green]Starting demo run...[/bold green]")

    # Import and run demo
    try:
        from ...core.orchestrator import Orchestrator
        from ...core.persona import PersonaProfile

        personas_dir = Path(config.personas_path)

        # Load persona
        try:
            persona = PersonaProfile.load(demo_config['persona'], personas_dir)
        except FileNotFoundError:
            console.print(f"[yellow]Persona not found, creating defaults...[/yellow]")
            from ...core.persona import create_default_personas
            create_default_personas(personas_dir)
            persona = PersonaProfile.load(demo_config['persona'], personas_dir)

        # Demo-specific URL (using first allowed domain or demo URL)
        if config.security.allowed_domains:
            demo_url = f"https://{config.security.allowed_domains[0]}"
        else:
            demo_url = "https://demo.sniff.example.com"

        # Generate demo run ID
        from datetime import datetime
        import uuid
        run_id = f"demo_{scenario}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        # Create orchestrator with demo mode
        orchestrator = Orchestrator(
            config=config,
            run_id=run_id,
            goal=demo_config['goal'],
            persona=persona,
            starting_url=demo_url,
            device=config.defaults.device,
            network=config.defaults.network,
            headless=headless,
            max_steps=config.guardrails.max_steps,
        )

        # Execute with live spinner
        with Live(Spinner("dots", text="Running demo..."), console=console):
            result = orchestrator.execute()

        # Display result
        console.print("\n" + "="*60)

        if result.get("success"):
            console.print("[bold green]✓ Demo completed successfully[/bold green]")
        else:
            console.print("[bold yellow]Demo completed with expected failure[/bold yellow]")

        console.print(f"\nRun ID: [cyan]{run_id}[/cyan]")
        console.print(f"Steps executed: {result.get('steps_executed', 0)}")
        console.print(f"Duration: {result.get('duration_seconds', 0):.1f}s")

        # Show diagnosis for failure scenarios
        if demo_config['expected_outcome'] == 'failure' and result.get('diagnosis'):
            console.print("\n[bold]Diagnosis Demo:[/bold]")
            diag = result['diagnosis']
            console.print(f"  Root cause: {diag.get('rootCause', 'Unknown')}")
            console.print(f"  Severity: {diag.get('severity', 'Unknown')}")
            console.print(f"  Likely owner: {diag.get('likelyOwner', 'Unknown')}")

            if config.slack.webhook_url:
                console.print("\n[bold green]✓[/bold green] Slack alert sent (check your channel)")
            else:
                console.print("\n[yellow]Note:[/yellow] Slack alerts not configured")

        # Show artifacts
        artifact_path = Path(config.artifacts_path) / run_id
        if artifact_path.exists():
            console.print(f"\nArtifacts: [cyan]{artifact_path}[/cyan]")

        console.print("\n[bold green]Demo presentation ready![/bold green]")
        console.print("\nView full report: [cyan]sniff report {run_id}[/cyan]")

    except ImportError as e:
        console.print(f"[red]Error:[/red] Orchestrator not yet implemented.")
        console.print("[yellow]Demo mode requires the orchestrator module.[/yellow]")
        console.print(f"Details: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error during demo:[/red] {e}")
        import traceback
        if questionary.confirm("\nShow full traceback?", default=False).ask():
            console.print(traceback.format_exc())
        raise typer.Exit(1)
