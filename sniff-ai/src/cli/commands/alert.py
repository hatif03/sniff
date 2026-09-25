"""Sherlock alert command - Test and manage Slack alerting."""

from typing import Optional
from datetime import datetime

import typer
from rich.console import Console
from rich.panel import Panel

from ...core.config import get_config

console = Console()
app = typer.Typer()


@app.command("test")
def test_alert(
    webhook_url: Optional[str] = typer.Option(
        None,
        "--webhook",
        "-w",
        help="Override webhook URL from config"
    ),
):
    """Test Slack webhook integration with a sample alert.

    Sends a test alert to verify:
    - Webhook URL is valid
    - Network connectivity
    - Message formatting

    Examples:

        sherlock alert test

        sherlock alert test --webhook https://hooks.slack.com/services/...
    """

    console.print(Panel.fit(
        "[bold cyan]Slack Alert Test[/bold cyan]\n"
        "Sending test notification",
        border_style="cyan"
    ))

    # Load config
    config = get_config()

    # Use provided webhook or config
    webhook = webhook_url or config.slack.webhook_url

    if not webhook:
        console.print("[red]Error:[/red] No Slack webhook URL configured.")
        console.print("\nConfigure webhook in one of these ways:")
        console.print("  1. Run [cyan]sherlock init[/cyan] and configure Slack")
        console.print("  2. Set SLACK_WEBHOOK_URL in .env")
        console.print("  3. Use --webhook flag: [cyan]sherlock alert test --webhook URL[/cyan]")
        raise typer.Exit(1)

    console.print(f"\n[dim]Webhook: {webhook[:50]}...[/dim]")

    # Create test alert payload
    test_payload = {
        "runId": "test_run_12345",
        "goal": "Test Slack integration",
        "persona": "test_user",
        "diagnosis": {
            "rootCause": "Integration",
            "severity": "P2",
            "likelyOwner": "DevOps",
            "suggestedFix": "This is a test alert - no action needed",
            "reproSteps": [
                "Run 'sherlock alert test'",
                "Check your Slack channel",
                "Verify message appears correctly"
            ]
        },
        "evidence": {
            "screenshots": ["test_screenshot_1.png", "test_screenshot_2.png"],
            "errorMessages": ["Test error message"],
            "url": "https://example.com/test"
        },
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Import and use Slack service
    try:
        from ...alerts.slack import SlackAlert

        slack_service = SlackAlert(webhook_url=webhook, bot_name=config.slack.bot_name)

        console.print("\n[bold]Sending test alert...[/bold]")

        success = slack_service.send_test_alert()

        if success:
            console.print("\n[bold green]✓ Test alert sent successfully![/bold green]")
            console.print("\nCheck your Slack channel for the test message.")
            console.print("The alert should show:")
            console.print("  - Test message from Sherlock")
            console.print("  - Confirmation that webhook is configured correctly")
        else:
            console.print(f"\n[bold red]✗ Failed to send alert[/bold red]")
            console.print("Check the logs above for error details.")

            # Troubleshooting tips
            console.print("\n[bold]Troubleshooting:[/bold]")
            console.print("  1. Verify webhook URL is correct")
            console.print("  2. Check network connectivity")
            console.print("  3. Ensure webhook has not been revoked")
            console.print("  4. Check Slack workspace settings")

            raise typer.Exit(1)

    except ImportError as e:
        console.print(f"[red]Error:[/red] Slack alert service not yet implemented.")
        console.print("[yellow]The alert module is still being developed.[/yellow]")
        console.print(f"Details: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error sending alert:[/red] {e}")
        raise typer.Exit(1)


@app.command("configure")
def configure_alert():
    """Reconfigure Slack webhook settings interactively."""

    import questionary

    console.print(Panel.fit(
        "[bold cyan]Configure Slack Alerts[/bold cyan]",
        border_style="cyan"
    ))

    config = get_config()

    # Get webhook URL
    webhook_url = questionary.text(
        "Slack webhook URL:",
        default=config.slack.webhook_url or ""
    ).ask()

    if not webhook_url:
        console.print("[yellow]No webhook URL provided. Slack alerts will be disabled.[/yellow]")
        config.slack.webhook_url = None
    else:
        config.slack.webhook_url = webhook_url

        # Get optional settings
        channel = questionary.text(
            "Slack channel (optional, leave empty for webhook default):",
            default=config.slack.channel or ""
        ).ask()

        config.slack.channel = channel if channel else None

        bot_name = questionary.text(
            "Bot display name:",
            default=config.slack.bot_name or "Sherlock Alert Bot"
        ).ask()

        config.slack.bot_name = bot_name

    # Save configuration
    config.save()
    console.print("\n[green]✓[/green] Slack configuration saved")

    # Offer to test
    if config.slack.webhook_url:
        test_now = questionary.confirm(
            "\nTest Slack integration now?",
            default=True
        ).ask()

        if test_now:
            test_alert(webhook_url=config.slack.webhook_url)
