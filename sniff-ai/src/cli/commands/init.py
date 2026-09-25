"""Sherlock init command - Interactive configuration setup."""

import os
from pathlib import Path

import questionary
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...core.config import SherlockConfig
from ...core.persona import create_default_personas

console = Console()


def init_command(
    config_path: str = typer.Option(
        "./data/sherlock.json",
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
    """Initialize Sherlock configuration interactively.

    Sets up:
    - Configuration file (sherlock.json)
    - Default personas
    - Directory structure
    - .env validation
    """
    console.print(Panel.fit(
        "[bold cyan]Sherlock Initialization[/bold cyan]\n"
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
        config = SherlockConfig.from_env()
    except Exception as e:
        console.print(f"[red]Error loading configuration from environment:[/red] {e}")
        raise typer.Exit(1)

    # Interactive configuration
    console.print("\n[bold]AWS Credentials Configuration[/bold]")

    # Check for existing credentials
    env_file = Path(".env")
    existing_creds = {
        'AWS_ACCESS_KEY_ID': os.getenv('AWS_ACCESS_KEY_ID'),
        'AWS_SECRET_ACCESS_KEY': os.getenv('AWS_SECRET_ACCESS_KEY'),
        'AWS_SESSION_TOKEN': os.getenv('AWS_SESSION_TOKEN'),
        'AWS_REGION': os.getenv('AWS_REGION'),
    }

    has_existing = any(existing_creds.values())

    if has_existing:
        console.print("[green]✓[/green] Found existing AWS credentials in environment")
        use_existing = questionary.confirm(
            "Use existing AWS credentials?",
            default=True
        ).ask()
    else:
        console.print("[yellow]![/yellow] No AWS credentials found in environment")
        use_existing = False

    env_updates = {}

    if not use_existing:
        cred_method = questionary.select(
            "How would you like to provide AWS credentials?",
            choices=[
                "Enter credentials manually",
                "Use AWS CLI profile (credentials file)",
                "Use IAM role (for EC2/Lambda)",
                "Configure later (skip for now)",
            ]
        ).ask()

        if cred_method == "Enter credentials manually":
            console.print("\n[cyan]Enter your AWS credentials:[/cyan]")
            console.print("[dim]These will be saved to .env file[/dim]")

            access_key = questionary.password(
                "AWS Access Key ID:",
                validate=lambda x: len(x) > 0 or "Access Key ID is required"
            ).ask()

            secret_key = questionary.password(
                "AWS Secret Access Key:",
                validate=lambda x: len(x) > 0 or "Secret Access Key is required"
            ).ask()

            use_session_token = questionary.confirm(
                "Do you have a session token? (for temporary credentials)",
                default=False
            ).ask()

            session_token = None
            if use_session_token:
                session_token = questionary.password(
                    "AWS Session Token:",
                ).ask()

            env_updates['AWS_ACCESS_KEY_ID'] = access_key
            env_updates['AWS_SECRET_ACCESS_KEY'] = secret_key
            if session_token:
                env_updates['AWS_SESSION_TOKEN'] = session_token

        elif cred_method == "Use AWS CLI profile (credentials file)":
            profile_name = questionary.text(
                "AWS profile name:",
                default="default"
            ).ask()
            env_updates['AWS_PROFILE'] = profile_name
            console.print(f"[green]✓[/green] Will use AWS profile: {profile_name}")
            console.print("[dim]Make sure your ~/.aws/credentials file is configured[/dim]")

        elif cred_method == "Use IAM role (for EC2/Lambda)":
            console.print("[green]✓[/green] Will use IAM role from instance metadata")
            console.print("[dim]Ensure your EC2 instance or Lambda function has appropriate IAM role attached[/dim]")

        else:  # Configure later
            console.print("[yellow]![/yellow] AWS credentials not configured")
            console.print("[dim]You'll need to set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env before running[/dim]")

    console.print("\n[bold]Bedrock Configuration[/bold]")

    # Bedrock configuration
    model_id = questionary.text(
        "Bedrock model ID:",
        default=config.bedrock.model_id
    ).ask()

    config.bedrock.model_id = model_id
    env_updates['BEDROCK_MODEL_ID'] = model_id

    region = questionary.text(
        "AWS region:",
        default=config.bedrock.region
    ).ask()

    config.bedrock.region = region
    env_updates['AWS_REGION'] = region

    # Optional: Configure fallback model
    configure_fallback = questionary.confirm(
        "Configure fallback model? (optional, for redundancy)",
        default=False
    ).ask()

    if configure_fallback:
        fallback_model = questionary.text(
            "Fallback Bedrock model ID:",
            default=config.bedrock.fallback_model_id or "anthropic.claude-3-5-sonnet-20241022-v2:0"
        ).ask()
        config.bedrock.fallback_model_id = fallback_model
        env_updates['BEDROCK_MODEL_FALLBACK'] = fallback_model

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
                default=config.slack.bot_name or "Sherlock Alert Bot"
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
        console.print(f"\n[bold]Updating .env file...[/bold]")
        env_file = Path(".env")

        # Read existing .env if it exists
        existing_env = {}
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        existing_env[key.strip()] = value.strip()

        # Merge updates
        existing_env.update(env_updates)

        # Write back to .env
        with open(env_file, 'w') as f:
            f.write("# Sherlock Configuration\n")
            f.write("# Generated by sherlock init\n\n")
            for key, value in sorted(existing_env.items()):
                f.write(f"{key}={value}\n")

        console.print(f"  ✓ Updated {env_file}")
        console.print(f"  ✓ Saved {len(env_updates)} environment variable(s)")

        # IMPORTANT: Load the new .env file into current environment
        # This ensures validation can see the newly configured credentials
        from dotenv import load_dotenv
        load_dotenv(env_file, override=True)
        console.print(f"  ✓ Loaded credentials into environment")

    # Validate configuration (AFTER loading credentials)
    console.print("\n[bold]Validating Configuration...[/bold]")
    validation_errors = config.validate_required()

    if validation_errors:
        console.print("\n[yellow]Warning: Configuration validation found issues:[/yellow]")
        for error in validation_errors:
            console.print(f"  - {error}")
        console.print("\n[dim]You can fix these issues later by:")
        console.print("  1. Running [cyan]sherlock init[/cyan] again")
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

    # AWS Credentials status
    if env_updates:
        if 'AWS_ACCESS_KEY_ID' in env_updates:
            summary.add_row("AWS Credentials", "✓ Manual credentials configured")
        elif 'AWS_PROFILE' in env_updates:
            summary.add_row("AWS Credentials", f"✓ Using profile: {env_updates['AWS_PROFILE']}")
        else:
            summary.add_row("AWS Credentials", "✓ Using IAM role")
    elif has_existing:
        summary.add_row("AWS Credentials", "✓ Using existing credentials")
    else:
        summary.add_row("AWS Credentials", "✗ Not configured")

    summary.add_row("Bedrock model", config.bedrock.model_id)
    summary.add_row("AWS region", config.bedrock.region)
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
    if env_updates or has_existing:
        console.print("  1. Validate AWS setup: [cyan]sherlock preflight[/cyan]")
        console.print("  2. Review/edit personas: [cyan]sherlock personas list[/cyan]")
        console.print("  3. Test Slack alerts (if configured): [cyan]sherlock alert test[/cyan]")
        console.print("  4. Run your first test: [cyan]sherlock run --goal 'Complete signup'[/cyan]")
    else:
        console.print("  [yellow]![/yellow] Configure AWS credentials first:")
        console.print("     - Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
        console.print("     - Or configure AWS CLI with [cyan]aws configure[/cyan]")
        console.print("  1. Validate AWS setup: [cyan]sherlock preflight[/cyan]")
        console.print("  2. Review/edit personas: [cyan]sherlock personas list[/cyan]")
        console.print("  3. Run your first test: [cyan]sherlock run --goal 'Complete signup'[/cyan]")
