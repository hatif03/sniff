"""sniff init command - Interactive configuration setup."""

import os
from pathlib import Path

import questionary
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...core.config import SniffConfig
from ...core.persona import create_default_personas

console = Console()


def init_command(
    config_path: str = typer.Option(
        "./data/sniff.json",
        "--config",
        "-c",
        help="Path to save configuration"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing configuration"
    )
):
    """Initialize sniff configuration interactively.

    Sets up:
    - Configuration file (sniff.json)
    - Default personas
    - Directory structure
    - .env validation
    """
    console.print(Panel.fit(
        "[bold cyan]sniff Initialization[/bold cyan]\n"
        "Let's set up your autonomous mystery shopper system.",
        border_style="cyan"
    ))

    config_file = Path(config_path)

    # Check if config already exists
    if config_file.exists() and not force:
        console.print(f"\n[yellow]Warning:[/yellow] Configuration already exists at {config_path}")
        overwrite = questionary.confirm(
            "Do you want to overwrite it?",
            default=False
        ).ask()

        if not overwrite:
            console.print("[yellow]Initialization cancelled.[/yellow]")
            raise typer.Exit(0)

    # Load existing config or create new from environment
    try:
        config = SniffConfig.from_env()
    except Exception as e:
        console.print(f"[red]Error loading configuration from environment:[/red] {e}")
        raise typer.Exit(1)

    # Interactive configuration
    console.print("\n[bold]Gemini (Vertex AI) Configuration[/bold]")
    console.print(
        "[dim]Auth is via Application Default Credentials, not an API key. "
        "Run `gcloud auth application-default login` first if you haven't.[/dim]"
    )

    env_file = Path(".env")
    env_updates = {}

    has_adc = False
    try:
        import google.auth
        google.auth.default()
        has_adc = True
    except Exception:
        pass

    if has_adc:
        console.print("[green]✓[/green] Found valid Google Cloud Application Default Credentials")
    else:
        console.print("[yellow]![/yellow] No Google Cloud ADC found")
        console.print("[dim]Run `gcloud auth application-default login` in another terminal, then continue.[/dim]")

    project_id = questionary.text(
        "GCP project ID (for Vertex AI):",
        default=config.gemini.project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    ).ask()
    config.gemini.project_id = project_id
    env_updates['GEMINI_PROJECT_ID'] = project_id

    region = questionary.text(
        "Vertex AI region:",
        default=config.gemini.region
    ).ask()
    config.gemini.region = region
    env_updates['GEMINI_REGION'] = region

    model_id = questionary.text(
        "Gemini model ID:",
        default=config.gemini.model_id
    ).ask()
    config.gemini.model_id = model_id
    env_updates['GEMINI_MODEL_ID'] = model_id

    fallback_model = questionary.text(
        "Fallback Gemini model ID (used if the primary isn't available in this region):",
        default=config.gemini.fallback_model_id
    ).ask()
    config.gemini.fallback_model_id = fallback_model
    env_updates['GEMINI_FALLBACK_MODEL_ID'] = fallback_model

    console.print("\n[bold]k2-horizon (ifm.ai) Configuration[/bold]")
    console.print("[dim]Text-only reasoning model, used for goal enhancement, planning, and persona reviews.[/dim]")

    api_key = questionary.password(
        "ifm.ai API key:",
        validate=lambda x: len(x) > 0 or "API key is required"
    ).ask()
    config.k2horizon.api_key = api_key
    env_updates['IFM_API_KEY'] = api_key

    k2_model_id = questionary.text(
        "k2-horizon model ID:",
        default=config.k2horizon.model_id
    ).ask()
    config.k2horizon.model_id = k2_model_id
    env_updates['IFM_MODEL_ID'] = k2_model_id

    # Security configuration
    console.print("\n[bold]Security Configuration[/bold]")

    domains_str = questionary.text(
        "Allowed domains (comma-separated):",
        default=",".join(config.security.allowed_domains) if config.security.allowed_domains else ""
    ).ask()

    if domains_str:
        config.security.allowed_domains = [d.strip() for d in domains_str.split(',')]

    config.security.enforce_domain_allowlist = questionary.confirm(
        "Enforce domain allowlist?",
        default=config.security.enforce_domain_allowlist
    ).ask()

    # Slack configuration
    console.print("\n[bold]Slack Integration (Optional)[/bold]")

    configure_slack = questionary.confirm(
        "Configure Slack alerts?",
        default=bool(config.slack.webhook_url)
    ).ask()

    if configure_slack:
        config.slack.webhook_url = questionary.text(
            "Slack webhook URL:",
            default=config.slack.webhook_url or ""
        ).ask()

        if config.slack.webhook_url:
            config.slack.channel = questionary.text(
                "Slack channel (optional, leave empty for webhook default):",
                default=config.slack.channel or ""
            ).ask() or None

            config.slack.bot_name = questionary.text(
                "Bot display name:",
                default=config.slack.bot_name or "Sniff Alert Bot"
            ).ask()

    # Guardrails
    console.print("\n[bold]Guardrails and Limits[/bold]")

    config.guardrails.max_steps = int(questionary.text(
        "Maximum steps per run:",
        default=str(config.guardrails.max_steps),
        validate=lambda x: x.isdigit() and int(x) > 0
    ).ask())

    config.guardrails.hard_timeout = int(questionary.text(
        "Hard timeout (seconds):",
        default=str(config.guardrails.hard_timeout),
        validate=lambda x: x.isdigit() and int(x) > 0
    ).ask())

    # Defaults
    console.print("\n[bold]Default Settings[/bold]")

    config.defaults.device = questionary.select(
        "Default device profile:",
        choices=["iPhone 13", "iPhone 14", "iPhone 14 Pro", "Pixel 5", "Galaxy S21"],
        default=config.defaults.device
    ).ask()

    config.defaults.network = questionary.select(
        "Default network profile:",
        choices=["4g", "3g", "slow3g"],
        default=config.defaults.network
    ).ask()

    # Create directories
    console.print("\n[bold]Creating Directory Structure...[/bold]")

    dirs_to_create = [
        Path(config.db_path).parent,
        Path(config.artifacts_path),
        Path(config.personas_path),
    ]

    for directory in dirs_to_create:
        directory.mkdir(parents=True, exist_ok=True)
        console.print(f"  ✓ Created {directory}")

    # Create default personas
    console.print("\n[bold]Creating Default Personas...[/bold]")
    create_default_personas(Path(config.personas_path))
    console.print(f"  ✓ Created default personas in {config.personas_path}")

    # Save configuration
    console.print("\n[bold]Saving Configuration...[/bold]")
    config.save(config_file)
    console.print(f"  ✓ Saved configuration to {config_file}")

    # Save environment variables to .env
    if env_updates:
        console.print("\n[bold]Updating .env file...[/bold]")
        env_file = Path(".env")

        # Read existing .env if it exists
        existing_env = {}
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        existing_env[key.strip()] = value.strip()

        # Merge updates
        existing_env.update(env_updates)

        # Write back to .env
        with open(env_file, 'w') as f:
            f.write("# sniff Configuration\n")
            f.write("# Generated by sniff init\n\n")
            for key, value in sorted(existing_env.items()):
                f.write(f"{key}={value}\n")

        console.print(f"  ✓ Updated {env_file}")
        console.print(f"  ✓ Saved {len(env_updates)} environment variable(s)")

        # IMPORTANT: Load the new .env file into current environment
        # This ensures validation can see the newly configured credentials
        from dotenv import load_dotenv
        load_dotenv(env_file, override=True)
        console.print("  ✓ Loaded credentials into environment")

    # Validate configuration (AFTER loading credentials)
    console.print("\n[bold]Validating Configuration...[/bold]")
    validation_errors = config.validate_required()

    if validation_errors:
        console.print("\n[yellow]Warning: Configuration validation found issues:[/yellow]")
        for error in validation_errors:
            console.print(f"  - {error}")
        console.print("\n[dim]You can fix these issues later by:")
        console.print("  1. Running [cyan]sniff init[/cyan] again")
        console.print("  2. Editing the .env file directly")
        console.print("  3. Setting environment variables[/dim]\n")
    else:
        console.print("  ✓ All required configuration present")

    # Display summary
    console.print("\n[bold green]Initialization Complete![/bold green]")

    summary = Table(title="Configuration Summary", show_header=False, box=None)
    summary.add_column("Setting", style="cyan")
    summary.add_column("Value", style="white")

    summary.add_row("Config file", str(config_file))
    summary.add_row("Google Cloud ADC", "✓ Valid" if has_adc else "✗ Not configured - run `gcloud auth application-default login`")
    summary.add_row("Gemini model", f"{config.gemini.model_id} ({config.gemini.region})")
    summary.add_row("k2-horizon model", config.k2horizon.model_id)
    summary.add_row("Personas path", config.personas_path)
    summary.add_row("Artifacts path", config.artifacts_path)
    summary.add_row("Max steps", str(config.guardrails.max_steps))
    summary.add_row("Default device", config.defaults.device)

    if config.slack.webhook_url:
        summary.add_row("Slack alerts", "✓ Configured")
    else:
        summary.add_row("Slack alerts", "✗ Not configured")

    console.print(summary)

    # Next steps
    console.print("\n[bold]Next Steps:[/bold]")
    if has_adc and config.k2horizon.api_key:
        console.print("  1. Validate setup: [cyan]sniff preflight[/cyan]")
        console.print("  2. Review/edit personas: [cyan]sniff personas list[/cyan]")
        console.print("  3. Test Slack alerts (if configured): [cyan]sniff alert test[/cyan]")
        console.print("  4. Run your first test: [cyan]sniff run --goal 'Complete signup'[/cyan]")
    else:
        console.print("  [yellow]![/yellow] Finish provider setup first:")
        if not has_adc:
            console.print("     - Run [cyan]gcloud auth application-default login[/cyan] for Gemini/Vertex AI")
        if not config.k2horizon.api_key:
            console.print("     - Set IFM_API_KEY in .env for k2-horizon")
        console.print("  1. Validate setup: [cyan]sniff preflight[/cyan]")
        console.print("  2. Review/edit personas: [cyan]sniff personas list[/cyan]")
        console.print("  3. Run your first test: [cyan]sniff run --goal 'Complete signup'[/cyan]")
