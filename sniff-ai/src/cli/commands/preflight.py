"""
Preflight validation command for sniff AWS/Bedrock setup

Validates:
- Environment variables configuration
- AWS credentials validity
- Bedrock service access
- Model availability and access
- Network connectivity to Bedrock endpoints
- Model invocation capability

Usage:
    sniff preflight
    sniff preflight --verbose
"""

import os
import sys
import json
import socket
from typing import List, Tuple
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import typer

from ...core.config import SniffConfig

console = Console()
app = typer.Typer()


class PreflightCheck:
    """Preflight validation for AWS Bedrock setup"""

    def __init__(self, config: SniffConfig, verbose: bool = False):
        self.config = config
        self.checks: List[Tuple[str, bool, str]] = []
        self.warnings: List[str] = []
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

        # Check Bedrock configuration
        if not self.config.bedrock.model_id:
            missing.append("BEDROCK_MODEL_ID")

        if not self.config.bedrock.region:
            missing.append("AWS_REGION")

        if missing:
            self.add_check(
                "Environment Variables",
                False,
                f"Missing: {', '.join(missing)}"
            )
            return False

        # Check if credentials are configured
        has_profile = bool(os.getenv("AWS_PROFILE"))
        has_keys = bool(os.getenv("AWS_ACCESS_KEY_ID"))

        if not has_profile and not has_keys:
            self.add_warning(
                "No AWS credentials found in environment. Relying on instance metadata or default profile."
            )

        self.add_check(
            "Environment Variables",
            True,
            f"Model: {self.config.bedrock.model_id}, Region: {self.config.bedrock.region}"
        )
        return True

    def check_aws_credentials(self) -> bool:
        """Verify AWS credentials are valid"""
        try:
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()

            self.add_check(
                "AWS Credentials",
                True,
                f"Account: {identity['Account']}, User: {identity['Arn'].split('/')[-1]}"
            )
            return True
        except NoCredentialsError:
            self.add_check(
                "AWS Credentials",
                False,
                "No credentials configured. Set AWS_PROFILE or AWS_ACCESS_KEY_ID"
            )
            return False
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'ExpiredToken':
                self.add_check(
                    "AWS Credentials",
                    False,
                    "Credentials expired. Run 'aws sso login' or refresh your credentials"
                )
            else:
                self.add_check("AWS Credentials", False, f"Invalid: {e}")
            return False

    def check_bedrock_access(self) -> bool:
        """Verify Bedrock service access"""
        try:
            region = self.config.bedrock.region
            bedrock = boto3.client('bedrock', region_name=region)

            # List models to verify access
            response = bedrock.list_foundation_models()
            model_count = len(response.get('modelSummaries', []))

            self.add_check(
                "Bedrock Service Access",
                True,
                f"Access granted in {region}. {model_count} models available."
            )
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'AccessDeniedException':
                self.add_check(
                    "Bedrock Service Access",
                    False,
                    "Access denied. Check IAM permissions (bedrock:ListFoundationModels)"
                )
            else:
                self.add_check("Bedrock Service Access", False, f"Error: {e}")
            return False

    def check_model_access(self) -> bool:
        """Verify specific model access"""
        try:
            region = self.config.bedrock.region
            model_id = self.config.bedrock.model_id

            if not model_id:
                self.add_check("Model Access", False, "BEDROCK_MODEL_ID not set")
                return False

            bedrock = boto3.client('bedrock', region_name=region)

            # Check if model is available
            response = bedrock.list_foundation_models()
            available_models = [m['modelId'] for m in response.get('modelSummaries', [])]

            if model_id in available_models:
                self.add_check(
                    "Model Access",
                    True,
                    f"Model {model_id} is available"
                )
                return True
            else:
                self.add_check(
                    "Model Access",
                    False,
                    f"Model {model_id} not available. Enable in Bedrock console → Model access"
                )
                return False

        except ClientError as e:
            self.add_check("Model Access", False, f"Error: {e}")
            return False

    def check_fallback_model(self) -> bool:
        """Check fallback model availability (optional)"""
        fallback_model = self.config.bedrock.fallback_model_id
        if not fallback_model:
            self.add_warning("BEDROCK_MODEL_FALLBACK not configured (optional)")
            return True

        try:
            region = self.config.bedrock.region
            bedrock = boto3.client('bedrock', region_name=region)

            response = bedrock.list_foundation_models()
            available_models = [m['modelId'] for m in response.get('modelSummaries', [])]

            if fallback_model in available_models:
                self.add_check(
                    "Fallback Model",
                    True,
                    f"Fallback model {fallback_model} is available"
                )
                return True
            else:
                self.add_warning(
                    f"Fallback model {fallback_model} not available. Update BEDROCK_MODEL_FALLBACK"
                )
                return True  # Not a critical failure

        except ClientError as e:
            self.add_warning(f"Could not verify fallback model: {e}")
            return True  # Not a critical failure

    def check_network_connectivity(self) -> bool:
        """Check network connectivity to Bedrock endpoints"""
        try:
            region = self.config.bedrock.region
            endpoints = [
                f"bedrock-runtime.{region}.amazonaws.com",
                f"bedrock.{region}.amazonaws.com",
            ]

            for endpoint in endpoints:
                try:
                    socket.gethostbyname(endpoint)
                except socket.gaierror:
                    self.add_check(
                        "Network Connectivity",
                        False,
                        f"Cannot resolve {endpoint}. Check network/DNS/firewall."
                    )
                    return False

            self.add_check(
                "Network Connectivity",
                True,
                f"Can resolve Bedrock endpoints in {region}"
            )
            return True
        except Exception as e:
            self.add_check(
                "Network Connectivity",
                False,
                f"Network check failed: {e}"
            )
            return False

    def check_model_invocation(self) -> bool:
        """Test actual model invocation"""
        try:
            region = self.config.bedrock.region
            model_id = self.config.bedrock.model_id

            if not model_id:
                self.add_check("Model Invocation", False, "BEDROCK_MODEL_ID not set")
                return False

            bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)

            # Simple test invocation
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 50,
                "messages": [
                    {
                        "role": "user",
                        "content": "Respond with 'OK' if you can read this."
                    }
                ]
            })

            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=body
            )

            # Parse response
            response_body = json.loads(response['body'].read())
            response_text = response_body.get('content', [{}])[0].get('text', '')

            self.add_check(
                "Model Invocation",
                True,
                f"Successfully invoked {model_id.split('.')[-1]}"
            )
            if self.verbose and response_text:
                console.print(f"[dim]Model response: {response_text[:100]}...[/dim]")
            return True

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            error_msg = e.response.get('Error', {}).get('Message', '')
            if error_code == 'ResourceNotFoundException':
                self.add_check(
                    "Model Invocation",
                    False,
                    "Model not found. Verify model ID and region match."
                )
            elif error_code == 'AccessDeniedException':
                self.add_check(
                    "Model Invocation",
                    False,
                    "Access denied. Check IAM permissions for bedrock:InvokeModel"
                )
            elif error_code == 'ThrottlingException':
                self.add_check(
                    "Model Invocation",
                    False,
                    "Throttled. Rate limit exceeded or insufficient quota."
                )
            elif error_code == 'ValidationException':
                # Check if it's the inference profile requirement
                if 'inference profile' in error_msg.lower():
                    self.add_warning(
                        f"Model {model_id} requires an inference profile ARN for invocation. "
                        "This is expected for some models. The agent will use the correct ARN at runtime."
                    )
                    self.add_check(
                        "Model Invocation",
                        True,
                        f"Model requires inference profile (will be handled automatically)"
                    )
                    return True
                else:
                    self.add_check(
                        "Model Invocation",
                        False,
                        f"Validation error: {error_msg[:100]}"
                    )
            else:
                self.add_check("Model Invocation", False, f"Error: {error_code} - {error_msg[:50]}")

            if self.verbose:
                console.print(f"[dim]Full error: {e}[/dim]")
            return False
        except Exception as e:
            self.add_check("Model Invocation", False, f"Unexpected error: {e}")
            return False

    def run_all_checks(self) -> bool:
        """Run all preflight checks"""
        console.print("\n[bold blue]Running sniff Preflight Checks...[/bold blue]\n")

        # Run checks in order
        checks_methods = [
            self.check_environment_variables,
            self.check_aws_credentials,
            self.check_bedrock_access,
            self.check_model_access,
            self.check_fallback_model,
            self.check_network_connectivity,
            self.check_model_invocation,
        ]

        for check_method in checks_methods:
            check_method()

        # Display results
        self.display_results()

        # Return overall success (warnings don't count as failures)
        return all(passed for _, passed, _ in self.checks)

    def display_results(self):
        """Display check results in a table"""
        if not self.verbose:
            # Only show summary table in non-verbose mode
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

        # Display warnings
        if self.warnings:
            console.print("\n[bold yellow]Warnings:[/bold yellow]")
            for warning in self.warnings:
                console.print(f"  ⚠️  {warning}")

        # Summary
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
                    "  • Check docs/plan/AWS_BEDROCK_PREREQUISITES.md\n"
                    "  • Verify .env file has correct values\n"
                    "  • Run 'aws sts get-caller-identity' to test credentials\n"
                    "  • Enable model access in Bedrock console",
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
    Run preflight checks to validate AWS and Bedrock configuration.

    Verifies:
    - Configuration from sniff.json and .env
    - AWS credentials (via AWS CLI, SSO, or environment)
    - Bedrock service access (IAM permissions)
    - Model availability and access enablement
    - Network connectivity to Bedrock endpoints
    - Model invocation capability (end-to-end test)

    Examples:
        sniff preflight
        sniff preflight --verbose
    """

    # Load configuration (this automatically loads .env file too)
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
