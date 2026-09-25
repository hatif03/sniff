#!/usr/bin/env python3
"""Example orchestrator integration with Playwright Worker.

This example demonstrates how the orchestrator would use the worker
in the actual system. It shows the proper architecture boundaries:

- Orchestrator owns control flow
- Agent returns decisions only
- Worker executes tools only

This is a minimal example for illustration purposes.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.executor.playwright_worker import PlaywrightWorker
from src.core.models import AgentDecision, Observation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# Mock Agent Service (in real system, this calls Bedrock)
class MockAgentService:
    """Mock agent service that returns hardcoded decisions.

    In the real system, this would:
    1. Take observation + persona + goal
    2. Call Bedrock with structured prompt
    3. Parse and validate AgentDecision JSON
    4. Return decision to orchestrator
    """

    def __init__(self):
        self.step = 0

    async def decide(self, observation: Observation) -> AgentDecision:
        """Return next decision based on observation.

        This is a mock implementation. Real agent would use Bedrock.
        """
        self.step += 1

        logger.info(f"Agent deciding (step {self.step})...")

        # Mock decision flow for example.com
        if self.step == 1:
            # First step - click "More information" link
            return AgentDecision(
                action="tap",
                target="More information",
                reasoningSummary="Exploring the page to find relevant links",
                confidence=0.9,
            )
        elif self.step == 2:
            # Wait a bit
            return AgentDecision(
                action="wait",
                waitDurationMs=1000,
                reasoningSummary="Waiting for page to fully render",
                confidence=1.0,
            )
        elif self.step == 3:
            # Scroll down
            return AgentDecision(
                action="scroll",
                scrollDirection="down",
                reasoningSummary="Scrolling to explore more content",
                confidence=0.8,
            )
        else:
            # Complete the journey
            return AgentDecision(
                action="abort",
                abortReason="Exploration complete, no signup flow found on example.com",
                reasoningSummary="Completed exploration of example.com",
                confidence=1.0,
            )


# Orchestrator (simplified)
class SimpleOrchestrator:
    """Simplified orchestrator demonstrating architecture boundaries.

    In the real system, this would:
    - Implement full state machine (SETUP → NAVIGATE → ACTION_EXECUTION → ...)
    - Apply guardrails (max steps, timeouts, retry limits)
    - Handle STUCK_DETECTED → DIAGNOSE → ALERT → REPORT flow
    - Coordinate agent service and execution worker
    """

    def __init__(self, run_id: str, target_url: str):
        self.run_id = run_id
        self.target_url = target_url
        self.artifacts_dir = Path(f"./artifacts/{run_id}")

        # Components
        self.worker: Optional[PlaywrightWorker] = None
        self.agent = MockAgentService()

        # Guardrails
        self.MAX_STEPS = 20
        self.step_count = 0

    async def execute_decision(self, decision: AgentDecision) -> Observation:
        """Execute an agent decision using the worker.

        This method validates the decision and routes to appropriate worker method.
        """
        logger.info(
            f"Executing decision: {decision.action} "
            f"(confidence: {decision.confidence:.2f})"
        )
        logger.info(f"Reasoning: {decision.reasoningSummary}")

        if decision.action == "tap":
            return await self.worker.tap(decision.target)

        elif decision.action == "type":
            return await self.worker.type(decision.target, decision.inputText)

        elif decision.action == "scroll":
            return await self.worker.scroll(decision.scrollDirection)

        elif decision.action == "wait":
            return await self.worker.wait(decision.waitDurationMs)

        elif decision.action == "back":
            return await self.worker.back()

        elif decision.action == "abort":
            logger.info(f"Agent requested abort: {decision.abortReason}")
            # Just capture final observation
            return await self.worker.capture_observation()

        else:
            raise ValueError(f"Unknown action: {decision.action}")

    async def run(self) -> None:
        """Execute the autonomous test run.

        State flow (simplified):
        1. SETUP - Initialize worker
        2. NAVIGATE - Navigate to target URL
        3. ACTION_LOOP - Agent decides, worker executes, repeat
        4. CLEANUP - Save artifacts and close worker
        """
        logger.info("=" * 80)
        logger.info(f"Starting run: {self.run_id}")
        logger.info(f"Target URL: {self.target_url}")
        logger.info("=" * 80)

        # SETUP state
        logger.info("STATE: SETUP")
        self.worker = PlaywrightWorker(
            run_id=self.run_id,
            artifacts_dir=self.artifacts_dir,
            device_name="iPhone 13",
            headless=False,  # Set True for CI
            slow_mo=200,  # Slow down for demo visibility
        )
        await self.worker.initialize()

        try:
            # NAVIGATE state
            logger.info("STATE: NAVIGATE")
            observation = await self.worker.navigate(self.target_url)

            # ACTION_EXECUTION loop
            logger.info("STATE: ACTION_EXECUTION")

            while self.step_count < self.MAX_STEPS:
                self.step_count += 1

                # Get decision from agent
                decision = await self.agent.decide(observation)

                # Check for abort
                if decision.action == "abort":
                    logger.info("Agent aborted, completing run")
                    observation = await self.execute_decision(decision)
                    break

                # Execute decision
                observation = await self.execute_decision(decision)

                # Check if action failed
                if not observation.lastActionResult.get("success"):
                    logger.warning(
                        f"Action failed: {observation.lastActionResult.get('error')}"
                    )
                    # In real system, would trigger retry logic or diagnosis

                logger.info(f"Step {self.step_count} complete")
                logger.info("-" * 80)

            # Check guardrails
            if self.step_count >= self.MAX_STEPS:
                logger.warning("Max steps reached, ending run")

            # REPORT state
            logger.info("STATE: REPORT")
            logger.info(f"Run complete! Artifacts saved to: {self.artifacts_dir}")
            logger.info(f"Total steps: {observation.step}")
            logger.info(f"Final URL: {observation.url}")

        finally:
            # CLEANUP
            logger.info("STATE: CLEANUP")
            await self.worker.cleanup()

        logger.info("=" * 80)
        logger.info("Run finished successfully")
        logger.info("=" * 80)


async def main():
    """Run the example orchestrator."""
    orchestrator = SimpleOrchestrator(
        run_id="example_001",
        target_url="https://example.com"
    )

    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(main())
