"""Example usage of Agent Service for decision generation.

Demonstrates:
- Service initialization
- Decision generation from observations
- Error handling
- Reasoning timeline access
"""

import json
import logging
from datetime import datetime

from src.core.models import Observation, AgentDecision
from src.agent import BedrockClient, DecisionService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_basic_decision():
    """Example: Generate basic decision from observation."""
    print("\n=== Example 1: Basic Decision Generation ===\n")

    # Initialize service
    service = DecisionService(
        max_repair_retries=2,
        decision_temperature=0.7
    )

    # Create sample observation
    observation = Observation(
        runId="run_example_001",
        step=1,
        url="https://example.com/signup",
        screenshotPath="/artifacts/run_example_001/step_1.png",
        visibleText=[
            "Sign Up",
            "Email",
            "Password",
            "Continue"
        ],
        timing={"ttfb": 250, "domReady": 450},
        consoleErrors=[],
        networkEvents=[],
        lastActionResult={}
    )

    # Define goal
    goal = "Complete email signup flow"

    try:
        # Generate decision
        decision = service.get_decision(
            observation=observation,
            goal=goal,
            persona_description="Confused first-time user who reads carefully"
        )

        print(f"Generated Decision:")
        print(f"  Action: {decision.action}")
        print(f"  Target: {decision.target}")
        print(f"  Input Text: {decision.inputText}")
        print(f"  Reasoning: {decision.reasoningSummary}")
        print(f"  Confidence: {decision.confidence:.2f}")

        # Access reasoning timeline
        timeline = service.get_reasoning_timeline()
        print(f"\nReasoning Timeline Entries: {len(timeline)}")

    except Exception as e:
        logger.error(f"Decision generation failed: {e}")


def example_with_history():
    """Example: Generate decision with recent action history."""
    print("\n=== Example 2: Decision with History ===\n")

    service = DecisionService()

    observation = Observation(
        runId="run_example_002",
        step=3,
        url="https://example.com/signup/verify",
        screenshotPath="/artifacts/run_example_002/step_3.png",
        visibleText=[
            "Verify your email",
            "We sent a code to user@example.com",
            "Enter verification code",
            "Resend code"
        ],
        timing={"ttfb": 180, "domReady": 320},
        consoleErrors=[],
        networkEvents=[],
        lastActionResult={
            "action": "type",
            "status": "success",
            "target": "Email input"
        }
    )

    # Recent history for context
    history = [
        {
            "action": "tap",
            "target": "Sign Up button",
            "result": "success"
        },
        {
            "action": "type",
            "target": "Email input",
            "result": "success"
        },
        {
            "action": "tap",
            "target": "Continue button",
            "result": "success"
        }
    ]

    try:
        decision = service.get_decision(
            observation=observation,
            goal="Complete email signup with verification",
            recent_history=history
        )

        print(f"Decision with History:")
        print(f"  Action: {decision.action}")
        print(f"  Target: {decision.target}")
        print(f"  Reasoning: {decision.reasoningSummary}")

    except Exception as e:
        logger.error(f"Decision generation failed: {e}")


def example_error_handling():
    """Example: Handling decision generation errors."""
    print("\n=== Example 3: Error Handling ===\n")

    from src.agent.decision_service import (
        DecisionGenerationError,
        DecisionValidationError,
        DecisionTimeoutError
    )

    service = DecisionService(max_repair_retries=2)

    observation = Observation(
        runId="run_example_003",
        step=5,
        url="https://example.com/error",
        screenshotPath="/artifacts/run_example_003/step_5.png",
        visibleText=["500 Internal Server Error"],
        timing={"ttfb": 5000, "domReady": 5200},
        consoleErrors=["Failed to load resource"],
        networkEvents=[{"type": "error", "url": "/api/submit"}],
        lastActionResult={
            "action": "tap",
            "status": "failed",
            "error": "Element not found"
        }
    )

    try:
        decision = service.get_decision(
            observation=observation,
            goal="Complete signup flow"
        )
        print(f"Decision: {decision.action}")

    except DecisionTimeoutError as e:
        logger.error(f"Timeout: {e}")
        # Handle timeout - maybe retry with simpler prompt

    except DecisionValidationError as e:
        logger.error(f"Validation failed: {e}")
        # This should be rare - service has internal repair logic

    except DecisionGenerationError as e:
        logger.error(f"Generation failed: {e}")
        # Handle generation failure - maybe use fallback service


def example_reasoning_timeline():
    """Example: Accessing and using reasoning timeline."""
    print("\n=== Example 4: Reasoning Timeline ===\n")

    service = DecisionService()
    service.clear_timeline()

    # Generate multiple decisions
    for step in range(1, 4):
        observation = Observation(
            runId="run_example_004",
            step=step,
            url=f"https://example.com/step{step}",
            screenshotPath=f"/artifacts/run_example_004/step_{step}.png",
            visibleText=[f"Step {step} content"],
            timing={"ttfb": 200, "domReady": 400},
            consoleErrors=[],
            networkEvents=[],
            lastActionResult={}
        )

        try:
            decision = service.get_decision(
                observation=observation,
                goal="Complete multi-step signup"
            )
            print(f"Step {step}: {decision.action} on {decision.target}")

        except Exception as e:
            logger.error(f"Step {step} failed: {e}")

    # Access complete timeline
    timeline = service.get_reasoning_timeline()

    print(f"\nComplete Reasoning Timeline:")
    for entry in timeline:
        print(f"  Step {entry['step']}: {entry['action']} "
              f"(confidence: {entry['confidence']:.2f})")
        print(f"    Reasoning: {entry['reasoning']}")
        print(f"    Repaired: {entry['repaired']}, Fallback: {entry['is_fallback']}")

    # Save timeline for evidence
    with open("/tmp/reasoning_timeline.json", "w") as f:
        json.dump(timeline, f, indent=2)
    print(f"\nTimeline saved to /tmp/reasoning_timeline.json")


def example_fallback_behavior():
    """Example: Service fallback on repeated failures."""
    print("\n=== Example 5: Fallback Decision ===\n")

    # Note: This example demonstrates the fallback mechanism
    # In practice, fallbacks only occur when Bedrock consistently
    # returns malformed JSON that can't be repaired

    service = DecisionService(max_repair_retries=1)

    observation = Observation(
        runId="run_example_005",
        step=10,
        url="https://example.com/stuck",
        screenshotPath="/artifacts/run_example_005/step_10.png",
        visibleText=["Unexpected state"],
        timing={"ttfb": 1000, "domReady": 1500},
        consoleErrors=["Multiple console errors"],
        networkEvents=[],
        lastActionResult={
            "action": "tap",
            "status": "failed",
            "error": "Element not clickable"
        }
    )

    print("Attempting decision generation...")
    print("(In real scenarios, service would return 'abort' fallback")
    print(" if Bedrock consistently returns invalid JSON)\n")

    print("Fallback decision structure:")
    fallback = {
        "action": "abort",
        "abortReason": "Decision generation failed after max attempts",
        "reasoningSummary": "System fallback: Unable to generate valid decision",
        "confidence": 0.0
    }
    print(json.dumps(fallback, indent=2))


if __name__ == "__main__":
    print("=" * 60)
    print("Agent Service Example Usage")
    print("=" * 60)

    # Note: These examples require valid AWS credentials
    # and Bedrock access. They will fail without proper setup.

    print("\nWARNING: Examples require AWS credentials and Bedrock access.")
    print("Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")
    print("\nRunning conceptual examples...\n")

    # Run examples (will fail if AWS not configured)
    try:
        example_basic_decision()
    except Exception as e:
        logger.error(f"Example 1 failed: {e}")

    try:
        example_with_history()
    except Exception as e:
        logger.error(f"Example 2 failed: {e}")

    example_error_handling()  # Demonstrates error handling patterns
    example_reasoning_timeline()  # Demonstrates timeline usage
    example_fallback_behavior()  # Demonstrates fallback mechanism

    print("\n" + "=" * 60)
    print("Examples completed (some may have failed without AWS setup)")
    print("=" * 60)
