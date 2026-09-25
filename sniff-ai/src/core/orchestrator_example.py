"""Example orchestrator integration for CLI.

This file demonstrates how to use the orchestrator from CLI commands.
"""

import asyncio
import logging
from pathlib import Path

from .config import SherlockConfig
from .orchestrator import RunOrchestrator
from .persona import PersonaProfile, create_default_personas

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def example_run():
    """Example autonomous run using orchestrator.

    This demonstrates the complete flow:
    1. Load configuration
    2. Initialize orchestrator
    3. Execute run
    4. Display results
    """
    # 1. Load configuration
    config = SherlockConfig.from_env()

    # Validate required configuration
    validation_errors = config.validate_required()
    if validation_errors:
        logger.error("Configuration validation failed:")
        for error in validation_errors:
            logger.error(f"  - {error}")
        return

    # 2. Ensure default personas exist
    personas_path = Path(config.personas_path)
    create_default_personas(personas_path)

    # 3. Create orchestrator
    # Note: agent_service should be provided by agent service implementation
    # For now, we pass None which will cause orchestrator to use fallback behavior
    orchestrator = RunOrchestrator(
        config=config,
        agent_service=None,  # TODO: Replace with actual agent service
    )

    # 4. Execute run
    try:
        logger.info("Starting autonomous run...")

        report = await orchestrator.run(
            goal="Complete signup with document upload",
            start_url="https://staging.example.com/signup",
            persona_name="confused_first_time_user",
            device_name="iPhone 13",
        )

        # 5. Display results
        print("\n" + "=" * 80)
        print(report.to_terminal_summary())
        print("=" * 80 + "\n")

        # 6. Show artifacts location
        logger.info(f"Run complete. Artifacts saved to: {report.artifacts_path}")
        logger.info(f"Run ID: {report.run_id}")

        # 7. If failed, show diagnosis
        if report.diagnosis:
            logger.warning(f"Run failed with {report.diagnosis.severity} - {report.diagnosis.rootCause}")
            logger.info(f"Suggested fix: {report.diagnosis.suggestedFix}")

    except Exception as e:
        logger.error(f"Run failed with error: {e}", exc_info=True)


async def example_report_loading():
    """Example of loading and displaying a previous run report."""
    config = SherlockConfig.from_env()

    from ..evidence.report_builder import create_report_builder

    report_builder = create_report_builder(
        artifacts_base_path=Path(config.artifacts_path)
    )

    # List recent runs
    recent_runs = report_builder.list_runs(limit=5)

    if not recent_runs:
        logger.info("No runs found")
        return

    logger.info(f"Found {len(recent_runs)} recent run(s):")
    for i, run in enumerate(recent_runs, 1):
        logger.info(
            f"  {i}. {run['run_id'][:8]}... - {run['outcome']} - {run['goal'][:50]}"
        )

    # Load most recent report
    if recent_runs:
        run_id = recent_runs[0]['run_id']
        report_data = report_builder.load_report(run_id)

        if report_data:
            logger.info(f"\nLoaded report for run: {run_id}")
            logger.info(f"Outcome: {report_data['outcome']}")
            logger.info(f"Goal: {report_data['goal']}")
            logger.info(f"Duration: {report_data.get('duration_seconds', 0):.2f}s")

            if 'diagnosis' in report_data:
                diagnosis = report_data['diagnosis']
                logger.info(f"\nDiagnosis:")
                logger.info(f"  Root Cause: {diagnosis['root_cause']}")
                logger.info(f"  Severity: {diagnosis['severity']}")
                logger.info(f"  Suggested Fix: {diagnosis['suggested_fix']}")


async def example_alert_test():
    """Example of testing Slack alert configuration."""
    config = SherlockConfig.from_env()

    from ..alerts.slack import create_slack_alert

    slack_alert = create_slack_alert(
        webhook_url=config.slack.webhook_url,
        bot_name=config.slack.bot_name,
    )

    if not config.slack.webhook_url:
        logger.warning("Slack webhook URL not configured")
        logger.info("Set SLACK_WEBHOOK_URL environment variable to test alerts")
        return

    logger.info("Sending test alert to Slack...")
    success = slack_alert.send_test_alert()

    if success:
        logger.info("✓ Test alert sent successfully!")
    else:
        logger.error("✗ Test alert failed to send")


def example_cli_run_command():
    """
    Example CLI command implementation for 'sherlock run'.

    This would be called from typer/click CLI handler.
    """
    import sys

    # Parse CLI arguments (simplified example)
    goal = "Complete signup with document upload"
    start_url = "https://staging.example.com/signup"
    persona_name = "confused_first_time_user"
    device_name = "iPhone 13"

    # Run orchestrator
    try:
        asyncio.run(example_run())
    except KeyboardInterrupt:
        logger.info("Run cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Run failed: {e}")
        sys.exit(1)


def example_cli_report_command():
    """
    Example CLI command implementation for 'sherlock report'.

    This would be called from typer/click CLI handler.
    """
    try:
        asyncio.run(example_report_loading())
    except Exception as e:
        logger.error(f"Failed to load report: {e}")


def example_cli_alert_test_command():
    """
    Example CLI command implementation for 'sherlock alert test'.

    This would be called from typer/click CLI handler.
    """
    try:
        asyncio.run(example_alert_test())
    except Exception as e:
        logger.error(f"Alert test failed: {e}")


if __name__ == "__main__":
    # Run example
    print("Running orchestrator example...")
    print("Note: This will fail without agent service implementation")
    print()

    asyncio.run(example_run())
