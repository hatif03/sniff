"""Example of how Orchestrator integrates with Agent Service.

This demonstrates the clean interface between Orchestrator and Agent Service,
respecting the critical architecture boundary:
- Agent returns decisions ONLY
- Orchestrator owns execution authority
- Worker executes actions
"""

import asyncio
import logging
from typing import Optional

from src.core.models import Observation, AgentDecision, ActionResult
from src.agent import DecisionService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrchestatorAgentIntegration:
    """Example orchestrator integration with Agent Service.

    This is a simplified demonstration of the orchestration loop.
    The full orchestrator (src/core/orchestrator.py) will include:
    - State machine transitions
    - Guardrails enforcement
    - Stuck detection
    - Diagnosis triggers
    """

    def __init__(self):
        # Initialize agent service
        self.decision_service = DecisionService(
            max_repair_retries=2,
            decision_temperature=0.7
        )

        # Run context
        self.run_id: Optional[str] = None
        self.goal: Optional[str] = None
        self.persona_description: Optional[str] = None

        # Execution history
        self.action_history: list[dict] = []

    async def execute_step(
        self,
        observation: Observation
    ) -> tuple[AgentDecision, ActionResult]:
        """Execute one step of the orchestration loop.

        1. Get decision from Agent Service (Observation -> AgentDecision)
        2. Execute action via Worker
        3. Capture new observation
        4. Return decision and result

        Args:
            observation: Current observation from worker

        Returns:
            Tuple of (decision, action_result)
        """
        logger.info(f"Step {observation.step}: Getting decision from agent...")

        # 1. Get decision from Agent Service
        # Agent NEVER controls browser - only returns decision
        try:
            decision = self.decision_service.get_decision(
                observation=observation,
                goal=self.goal,
                persona_description=self.persona_description,
                recent_history=self.action_history[-5:]  # Last 5 actions
            )

            logger.info(
                f"Agent decision: {decision.action} on '{decision.target}' "
                f"(confidence: {decision.confidence:.2f})"
            )

        except Exception as e:
            logger.error(f"Decision generation failed: {e}")
            # In full orchestrator, this would trigger diagnosis
            raise

        # 2. Validate decision (in full orchestrator, would use DecisionSanitizer)
        # For this example, we trust the decision

        # 3. Execute action via Worker
        # This is where Orchestrator would call PlaywrightWorker
        logger.info(f"Orchestrator executing: {decision.action}")

        # Simulated execution (real orchestrator calls worker methods)
        action_result = ActionResult(
            success=True,
            action=decision.action,
            status="success",
            target=decision.target,
            error=None,
            screenshotPath=f"/artifacts/{observation.runId}/step_{observation.step}_result.png",
            durationMs=250,
            details={}
        )

        # 4. Record action in history
        self.action_history.append({
            "action": decision.action,
            "target": decision.target,
            "result": action_result.status,
            "step": observation.step
        })

        return decision, action_result

    async def run_orchestration_loop(
        self,
        run_id: str,
        goal: str,
        persona_description: str,
        initial_observation: Observation,
        max_steps: int = 20
    ):
        """Simplified orchestration loop demonstrating agent integration.

        Args:
            run_id: Unique run identifier
            goal: User-defined goal for the run
            persona_description: Persona behavior profile
            initial_observation: Starting observation
            max_steps: Maximum steps (guardrail)
        """
        self.run_id = run_id
        self.goal = goal
        self.persona_description = persona_description
        self.decision_service.clear_timeline()

        logger.info(f"Starting run {run_id}")
        logger.info(f"Goal: {goal}")
        logger.info(f"Persona: {persona_description[:50]}...")

        current_observation = initial_observation

        for step in range(max_steps):
            try:
                # Execute step: Observation -> Decision -> Action -> Result
                decision, result = await self.execute_step(current_observation)

                # Check for completion conditions
                if decision.action == "abort":
                    logger.info(f"Agent aborted: {decision.abortReason}")
                    break

                # In real orchestrator, this would:
                # 1. Capture new observation from worker
                # 2. Check stuck detection
                # 3. Evaluate progress toward goal
                # 4. Transition state machine

                # For this example, we'll stop after a few steps
                if step >= 3:
                    logger.info("Example complete (real run would continue)")
                    break

            except Exception as e:
                logger.error(f"Step {step} failed: {e}")
                # In real orchestrator, this would trigger diagnosis
                break

        # Access reasoning timeline for evidence
        timeline = self.decision_service.get_reasoning_timeline()
        logger.info(f"\nReasoning Timeline ({len(timeline)} entries):")
        for entry in timeline:
            logger.info(
                f"  Step {entry['step']}: {entry['action']} on '{entry['target']}' "
                f"(confidence: {entry['confidence']:.2f}, attempt: {entry['attempt']})"
            )


async def example_orchestrator_integration():
    """Example of orchestrator using agent service."""
    print("\n" + "=" * 60)
    print("Orchestrator-Agent Integration Example")
    print("=" * 60 + "\n")

    # Create orchestrator
    orchestrator = OrchestatorAgentIntegration()

    # Create initial observation (would come from worker in real scenario)
    initial_obs = Observation(
        runId="example_run_001",
        step=1,
        url="https://example.com/signup",
        screenshotPath="/artifacts/example_run_001/step_1.png",
        visibleText=["Sign Up", "Email", "Password", "Continue"],
        timing={"ttfb": 200, "domReady": 400},
        consoleErrors=[],
        networkEvents=[],
        lastActionResult={}
    )

    # Run orchestration loop
    await orchestrator.run_orchestration_loop(
        run_id="example_run_001",
        goal="Complete email signup flow with verification",
        persona_description="Confused first-time user who reads carefully before clicking",
        initial_observation=initial_obs,
        max_steps=5
    )

    print("\n" + "=" * 60)
    print("Integration Example Complete")
    print("=" * 60 + "\n")

    print("Key Takeaways:")
    print("1. Agent Service returns decisions ONLY (never executes)")
    print("2. Orchestrator maintains execution authority")
    print("3. Clean interface: get_decision(observation, goal, persona, history)")
    print("4. Reasoning timeline available for evidence collection")
    print("5. Bounded retries and fallback safety built-in")


if __name__ == "__main__":
    print("\nNOTE: This example requires AWS credentials and Bedrock access.")
    print("It will fail without proper AWS setup.\n")

    try:
        asyncio.run(example_orchestrator_integration())
    except Exception as e:
        logger.error(f"Example failed (expected without AWS setup): {e}")
        print("\nTo run this example:")
        print("1. Configure AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)")
        print("2. Ensure Bedrock access is enabled in your AWS account")
        print("3. Verify the model is available in your region")
