"""
Preflight validation command for sniff's Gemini/k2-horizon/Jev setup

Validates:
- Environment variables configuration
- Google Cloud Application Default Credentials (for Gemini/Vertex AI)
- Gemini model invocation (Tier 3 vision-capable reasoning)
- k2-horizon model invocation (Tier 3 text-only reasoning)
- Jev/Typesafe invocation, if enabled (Tier 2 fast decision model)
- Network connectivity to the relevant API endpoints

Usage:
    sniff preflight
    sniff preflight --verbose
"""

import socket
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...core.config import SniffConfig

console = Console()
app = typer.Typer()


class PreflightCheck:
    """Preflight validation for sniff's LLM provider setup (Gemini, k2-horizon, Jev)"""

    def __init__(self, config: SniffConfig, verbose: bool = False):
        self.config = config
        self.checks: list[tuple[str, bool, str]] = []
        self.warnings: list[str] = []
        self.verbose = verbose

    def add_check(self, name: str, passed: bool, details: str = ""):
        """Record a check result"""
        self.checks.append((name, passed, details))
        if self.verbose:
            status = "✅ PASS" if passed else "❌ FAIL"
            console.print(f"[{'green' if passed else 'red'}]{status}[/] {name}: {details}")

    def add_warning(self, message: str):
        """Record a warning"""
        self.warnings.append(message)
        if self.verbose:
            console.print(f"[yellow]⚠️  {message}[/yellow]")

    def check_environment_variables(self) -> bool:
        """Check required configuration from config file and environment"""
        missing = []

        if not self.config.gemini.project_id:
            missing.append("GEMINI_PROJECT_ID")

        if not self.config.k2horizon.api_key:
            missing.append("IFM_API_KEY")

        if missing:
            self.add_check(
                "Environment Variables",
                False,
                f"Missing: {', '.join(missing)}"
            )
            return False

        self.add_check(
            "Environment Variables",
            True,
            f"Gemini: {self.config.gemini.model_id} ({self.config.gemini.region}), "
            f"k2-horizon: {self.config.k2horizon.model_id}"
        )
        return True

    def check_google_adc(self) -> bool:
        """Verify Google Cloud Application Default Credentials are valid"""
        try:
            import google.auth
            credentials, project = google.auth.default()
            self.add_check(
                "Google Cloud Credentials",
                True,
                f"ADC valid (project: {project or self.config.gemini.project_id})"
            )
            return True
        except Exception as e:
            self.add_check(
                "Google Cloud Credentials",
                False,
                f"ADC not available: {e}. Run 'gcloud auth application-default login'"
            )
            return False

    def check_gemini_invocation(self) -> bool:
        """Test actual Gemini (Vertex AI) invocation"""
        try:
            from ...agent.gemini_client import GeminiClient
            from ...agent.llm_errors import LLMInvocationError

            client = GeminiClient(
                project_id=self.config.gemini.project_id,
                region=self.config.gemini.region,
                model_id=self.config.gemini.model_id,
                fallback_model_id=self.config.gemini.fallback_model_id,
                timeout_seconds=15,
            )
            response = client.invoke(
                system_prompt="Reply with exactly one word.",
                user_message="Respond with 'OK' if you can read this.",
                max_tokens=10,
            )
            self.add_check(
                "Gemini Invocation",
                True,
                f"Successfully invoked {self.config.gemini.model_id} in {self.config.gemini.region}"
            )
            if self.verbose:
                console.print(f"[dim]Model response: {response[:100]}[/dim]")
            return True
        except LLMInvocationError as e:
            self.add_check("Gemini Invocation", False, f"Error: {e}")
            return False
        except Exception as e:
            self.add_check(
                "Gemini Invocation",
                False,
                f"Could not reach Gemini in {self.config.gemini.region}: {e}. "
                f"Try GEMINI_REGION=us-central1 or GEMINI_MODEL_ID={self.config.gemini.fallback_model_id}"
            )
            return False

    def check_k2horizon_invocation(self) -> bool:
        """Test actual k2-horizon invocation"""
        try:
            from ...agent.k2horizon_client import create_k2horizon_client
            from ...agent.llm_errors import LLMInvocationError

            client = create_k2horizon_client(self.config)
            response = client.invoke(
                system_prompt="Reply with exactly one word.",
                user_message="Respond with 'OK' if you can read this.",
                max_tokens=10,
            )
            self.add_check(
                "k2-horizon Invocation",
                True,
                f"Successfully invoked {self.config.k2horizon.model_id}"
            )
            if self.verbose:
                console.print(f"[dim]Model response: {response[:100]}[/dim]")
            return True
        except LLMInvocationError as e:
            self.add_check("k2-horizon Invocation", False, f"Error: {e}")
            return False
        except Exception as e:
            self.add_check("k2-horizon Invocation", False, f"Unexpected error: {e}")
            return False

    def check_jev(self) -> bool:
        """Check Jev (Typesafe AI) - optional Tier 2, only checked if enabled"""
        if not self.config.typesafe.enabled:
            self.add_warning("Jev (Tier 2) disabled - TYPESAFE_ENABLED=false. Skipping.")
            return True

        if not self.config.typesafe.api_key:
            self.add_check("Jev Invocation", False, "TYPESAFE_ENABLED=true but TYPESAFE_API_KEY not set")
            return False

        try:
            from ...agent.jev_client import JevClient, JevInvocationError

            client = JevClient(
                api_key=self.config.typesafe.api_key,
                base_url=self.config.typesafe.base_url,
                model_id=self.config.typesafe.model_id,
                timeout_seconds=10,
            )
            client.noul("Is this a test question?", context="Preflight check")
            self.add_check("Jev Invocation", True, "Successfully invoked Jev (Tier 2)")
            return True
        except JevInvocationError as e:
            self.add_check("Jev Invocation", False, f"Error: {e}")
            return False
        except Exception as e:
            self.add_check("Jev Invocation", False, f"Unexpected error: {e}")
            return False

    def check_network_connectivity(self) -> bool:
        """Check network connectivity to Gemini/k2-horizon endpoints"""
        endpoints = [
            f"{self.config.gemini.region}-aiplatform.googleapis.com",
            "api.ifm.ai",
        ]
        unresolved = []
        for endpoint in endpoints:
            try:
                socket.gethostbyname(endpoint)
            except socket.gaierror:
                unresolved.append(endpoint)

        if unresolved:
            self.add_check(
                "Network Connectivity",
                False,
                f"Cannot resolve: {', '.join(unresolved)}. Check network/DNS/firewall."
            )
            return False

        self.add_check("Network Connectivity", True, "Can resolve Gemini and k2-horizon endpoints")
        return True

    def run_all_checks(self) -> bool:
        """Run all preflight checks"""
        console.print("\n[bold blue]Running sniff Preflight Checks...[/bold blue]\n")

        checks_methods = [
            self.check_environment_variables,
            self.check_google_adc,
            self.check_network_connectivity,
            self.check_gemini_invocation,
            self.check_k2horizon_invocation,
            self.check_jev,
        ]

        for check_method in checks_methods:
            check_method()

        self.display_results()

        # Return overall success (warnings don't count as failures)
        return all(passed for _, passed, _ in self.checks)

    def display_results(self):
        """Display check results in a table"""
        if not self.verbose:
            table = Table(title="Preflight Check Results")
            table.add_column("Check", style="cyan", no_wrap=True)
            table.add_column("Status", style="magenta")
            table.add_column("Details", style="white")

            for name, passed, details in self.checks:
                status = "✅ PASS" if passed else "❌ FAIL"
                status_style = "green" if passed else "red"
                table.add_row(
                    name,
                    f"[{status_style}]{status}[/{status_style}]",
                    details
                )

            console.print(table)

        if self.warnings:
            console.print("\n[bold yellow]Warnings:[/bold yellow]")
            for warning in self.warnings:
                console.print(f"  ⚠️  {warning}")

        total = len(self.checks)
        passed = sum(1 for _, p, _ in self.checks if p)
        failed = total - passed

        console.print()
        if failed == 0:
            console.print(
                Panel(
                    f"[bold green]✅ All checks passed ({passed}/{total})[/bold green]\n"
                    "[green]System is ready for 'sniff run'[/green]",
                    title="Success",
                    border_style="green"
                )
            )
        else:
            console.print(
                Panel(
                    f"[bold red]❌ {failed} check(s) failed ({passed}/{total} passed)[/bold red]\n"
                    "[red]Fix the issues above before running sniff[/red]\n\n"
                    "[yellow]Troubleshooting:[/yellow]\n"
                    "  • Verify .env file has GEMINI_PROJECT_ID and IFM_API_KEY set\n"
                    "  • Run 'gcloud auth application-default login' for Gemini/Vertex AI\n"
                    "  • Run 'gcloud services enable aiplatform.googleapis.com' if Vertex AI isn't enabled\n"
                    "  • Verify the ifm.ai API key at https://platform.ifm.ai/api-keys",
                    title="Failed",
                    border_style="red"
                )
            )


@app.command()
def main(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output during checks"
    ),
    config_path: str = typer.Option(
        "./data/sniff.json",
        "--config",
        "-c",
        help="Path to configuration file"
    ),
):
    """
    Run preflight checks to validate the Gemini/k2-horizon/Jev setup.

    Verifies:
    - Configuration from sniff.json and .env
    - Google Cloud Application Default Credentials (for Gemini/Vertex AI)
    - Gemini model invocation (Tier 3 vision-capable reasoning, end-to-end test)
    - k2-horizon model invocation (Tier 3 text-only reasoning, end-to-end test)
    - Jev/Typesafe invocation, if enabled (Tier 2 fast decision model)
    - Network connectivity to the relevant API endpoints

    Examples:
        sniff preflight
        sniff preflight --verbose
    """

    try:
        config = SniffConfig.load(Path(config_path))
        if verbose:
            console.print(f"[dim]Loaded config from {config_path}[/dim]")
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load config file: {e}[/yellow]")
        console.print("[yellow]Using environment variables and defaults...[/yellow]\n")
        try:
            config = SniffConfig.from_env()
        except Exception as e2:
            console.print(f"[red]Error: Could not load configuration: {e2}[/red]")
            console.print("\n[yellow]Try running:[/yellow] sniff init")
            sys.exit(1)

    checker = PreflightCheck(config=config, verbose=verbose)
    success = checker.run_all_checks()

    if not success:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    app()
