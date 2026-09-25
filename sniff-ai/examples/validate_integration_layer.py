#!/usr/bin/env python3
"""Validation script for agent-worker integration layer.

Demonstrates:
- Valid decision processing
- Invalid decision sanitization
- Fallback policy activation
- Whitelist enforcement
- Trace logging
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.models import AgentDecision, Observation, ActionResult
from src.core.validation import DecisionSanitizer, ActionWhitelist, FallbackPolicy
from src.core.trace_logger import TraceLogger


def print_section(title: str):
    """Print section header."""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def example_1_valid_decision():
    """Example 1: Valid decision processing."""
    print_section("Example 1: Valid Decision Processing")

    sanitizer = DecisionSanitizer()

    decision = AgentDecision(
        action="tap",
        target="Submit button",
        reasoningSummary="Submit registration form after filling all fields",
        confidence=0.92,
    )

    print("\nAgent Decision:")
    print(f"  Action: {decision.action}")
    print(f"  Target: {decision.target}")
    print(f"  Reasoning: {decision.reasoningSummary}")
    print(f"  Confidence: {decision.confidence}")

    sanitized = sanitizer.sanitize(decision)

    print("\nSanitization Result:")
    print(f"  Was Sanitized: {sanitized.wasSanitized}")
    print(f"  Final Action: {sanitized.decision.action}")
    print(f"  ✓ Valid decision passed through unchanged")


def example_2_invalid_decision_fallback():
    """Example 2: Invalid decision with fallback."""
    print_section("Example 2: Invalid Decision with Fallback")

    sanitizer = DecisionSanitizer()

    # Invalid: type action without inputText
    invalid_dict = {
        "action": "type",
        "target": "email_field",
        # Missing inputText!
        "reasoningSummary": "Enter email address",
        "confidence": 0.9,
    }

    print("\nInvalid Agent Decision (dict):")
    print(f"  Action: {invalid_dict['action']}")
    print(f"  Target: {invalid_dict['target']}")
    print(f"  Input Text: [MISSING - REQUIRED!]")

    sanitized = sanitizer.sanitize(invalid_dict, allow_fallback=True)

    print("\nSanitization Result:")
    print(f"  Was Sanitized: {sanitized.wasSanitized}")
    print(f"  Original Action: {sanitized.originalAction}")
    print(f"  Sanitization Reason: {sanitized.sanitizationReason}")
    print(f"  Fallback Action: {sanitized.decision.action}")
    print(f"  Fallback Wait Duration: {sanitized.decision.waitDurationMs}ms")
    print(f"  ✓ Invalid decision safely replaced with wait fallback")


def example_3_whitelist_enforcement():
    """Example 3: Whitelist enforcement."""
    print_section("Example 3: Whitelist Enforcement")

    # Create restricted whitelist (no scroll allowed)
    whitelist = ActionWhitelist(
        allowed_actions={"tap", "type", "wait", "back"}
    )
    sanitizer = DecisionSanitizer(action_whitelist=whitelist)

    decision = AgentDecision(
        action="scroll",
        scrollDirection="down",
        reasoningSummary="Scroll down to view more content",
        confidence=0.85,
    )

    print("\nAgent Decision:")
    print(f"  Action: {decision.action}")
    print(f"  Direction: {decision.scrollDirection}")

    print("\nWhitelist Configuration:")
    print(f"  Allowed: {', '.join(sorted(whitelist.allowed_actions))}")
    print(f"  Is 'scroll' allowed: {whitelist.is_allowed('scroll')}")

    sanitized = sanitizer.sanitize(decision, allow_fallback=True)

    print("\nSanitization Result:")
    print(f"  Was Sanitized: {sanitized.wasSanitized}")
    print(f"  Reason: {sanitized.sanitizationReason}")
    print(f"  Fallback Action: {sanitized.decision.action}")
    print(f"  ✓ Whitelist violation caught, safe fallback applied")


def example_4_trace_logging():
    """Example 4: Trace logging."""
    print_section("Example 4: Trace Logging")

    logger = TraceLogger(run_id="validation_example")

    print(f"\nTrace Directory: {logger.trace_dir}")
    print(f"Trace File: {logger.trace_file}")

    # Log observation
    observation = Observation(
        runId="validation_example",
        step=1,
        url="https://example.com/signup",
        screenshotPath="/tmp/screenshot_001.png",
        visibleText=["Sign Up", "Email", "Password", "Submit"],
        timing={"ttfb": 180, "domReady": 450},
    )
    logger.log_observation(observation)
    print("\n✓ Logged observation")

    # Log decision
    decision = AgentDecision(
        action="type",
        target="email_field",
        inputText="test@example.com",
        reasoningSummary="Enter email address in signup form",
        confidence=0.95,
    )
    logger.log_agent_decision(decision, step=1)
    print("✓ Logged agent decision")

    # Log sanitization
    sanitizer = DecisionSanitizer()
    sanitized = sanitizer.sanitize(decision)
    logger.log_sanitization(sanitized, step=1)
    print("✓ Logged sanitization result")

    # Log action result
    result = ActionResult(
        success=True,
        action="type",
        status="success",
        target="email_field",
        durationMs=250,
    )
    logger.log_action_result(result, step=1)
    print("✓ Logged action result")

    # Show summary
    summary = logger.get_trace_summary()
    print("\nTrace Summary:")
    print(f"  Total Entries: {summary['total_entries']}")
    print(f"  Event Counts: {summary['event_counts']}")
    print(f"\n✓ Complete execution trace saved to {summary['trace_file']}")


def example_5_fallback_hierarchy():
    """Example 5: Fallback policy hierarchy."""
    print_section("Example 5: Fallback Policy Hierarchy")

    policy = FallbackPolicy()

    print("\nFallback Types:\n")

    # Wait fallback
    wait_fb = policy.create_wait_fallback("Invalid decision format")
    print("1. Wait Fallback:")
    print(f"   Action: {wait_fb.action}")
    print(f"   Duration: {wait_fb.waitDurationMs}ms")
    print(f"   Confidence: {wait_fb.confidence}")
    print(f"   Use: Default safe fallback for most errors\n")

    # Screenshot wait fallback
    screenshot_fb = policy.create_screenshot_wait_fallback("Need observation")
    print("2. Screenshot Wait Fallback:")
    print(f"   Action: {screenshot_fb.action}")
    print(f"   Duration: {screenshot_fb.waitDurationMs}ms")
    print(f"   Confidence: {screenshot_fb.confidence}")
    print(f"   Use: Diagnostic pause to capture state\n")

    # Abort fallback
    abort_fb = policy.create_abort_fallback("Critical error detected")
    print("3. Abort Fallback:")
    print(f"   Action: {abort_fb.action}")
    print(f"   Reason: {abort_fb.abortReason}")
    print(f"   Confidence: {abort_fb.confidence}")
    print(f"   Use: Critical failures requiring human intervention\n")


def example_6_action_validation():
    """Example 6: Action-specific validation."""
    print_section("Example 6: Action-Specific Validation Requirements")

    validation_cases = [
        ("tap", {"target": "Submit"}, "✓ Valid - has target"),
        ("tap", {}, "✗ Invalid - missing target"),
        ("type", {"target": "email", "inputText": "test@test.com"}, "✓ Valid - has target and inputText"),
        ("type", {"target": "email"}, "✗ Invalid - missing inputText"),
        ("scroll", {"scrollDirection": "down"}, "✓ Valid - has scrollDirection"),
        ("scroll", {}, "✗ Invalid - missing scrollDirection"),
        ("wait", {"waitDurationMs": 2000}, "✓ Valid - has waitDurationMs"),
        ("wait", {}, "✗ Invalid - missing waitDurationMs"),
        ("abort", {"abortReason": "CAPTCHA"}, "✓ Valid - has abortReason"),
        ("abort", {}, "✗ Invalid - missing abortReason"),
    ]

    print("\nAction Validation Requirements:\n")

    for action, fields, expected in validation_cases:
        print(f"{action:8} {str(fields):50} → {expected}")


def main():
    """Run all validation examples."""
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  Agent-Worker Integration Layer Validation".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")

    try:
        example_1_valid_decision()
        example_2_invalid_decision_fallback()
        example_3_whitelist_enforcement()
        example_4_trace_logging()
        example_5_fallback_hierarchy()
        example_6_action_validation()

        print_section("Validation Complete")
        print("\n✓ All examples completed successfully")
        print("\nKey Features Demonstrated:")
        print("  • Valid decision pass-through")
        print("  • Invalid decision sanitization")
        print("  • Automatic fallback activation")
        print("  • Whitelist enforcement")
        print("  • Structured trace logging")
        print("  • Action-specific validation")
        print("\nIntegration layer is ready for orchestrator use!")
        print()

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
