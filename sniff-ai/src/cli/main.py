"""Main CLI entry point for sniff.

Provides commands:
- sniff init - Interactive configuration setup
- sniff personas - Manage user personas
- sniff run - Execute autonomous test run
- sniff report - Display run results
- sniff alert test - Test Slack integration
- sniff demo - Deterministic demo mode
"""

import typer
from rich.console import Console
from typing import Optional

from .commands import init, personas, run, report, alert, demo, preflight, experiment

# Create Typer app
app = typer.Typer(
    name="Sniff",
    help="Autonomous mystery shopper for mobile/web signup flow testing",
    add_completion=False,
)

# Create console for rich output
console = Console()

# Register command modules
app.add_typer(preflight.app, name="preflight", help="Validate AWS/Bedrock setup")
app.command(name="init")(init.init_command)
app.add_typer(personas.app, name="personas", help="Manage user personas")
app.command(name="run")(run.run_command)
app.command(name="report")(report.report_command)
app.add_typer(alert.app, name="alert", help="Slack alerting commands")
app.command(name="demo")(demo.demo_command)
app.add_typer(experiment.app, name="experiment", help="Run experiments with multiple personas")


@app.callback()
def callback():
    """
    sniff - Autonomous Mystery Shopper

    Test mobile/web signup flows with AI-driven navigation and diagnosis.
    Detect friction, diagnose root causes, and escalate via Slack alerts.
    """
    pass


if __name__ == "__main__":
    app()
