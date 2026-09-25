"""Main CLI entry point for Sherlock.

Provides commands:
- sherlock init - Interactive configuration setup
- sherlock personas - Manage user personas
- sherlock run - Execute autonomous test run
- sherlock report - Display run results
- sherlock alert test - Test Slack integration
- sherlock demo - Deterministic demo mode
"""

import typer
from rich.console import Console
from typing import Optional

from .commands import init, personas, run, report, alert, demo, preflight, experiment

# Create Typer app
app = typer.Typer(
    name="sherlock",
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
    Sherlock - Autonomous Mystery Shopper

    Test mobile/web signup flows with AI-driven navigation and diagnosis.
    Detect friction, diagnose root causes, and escalate via Slack alerts.
    """
    pass


if __name__ == "__main__":
    app()
