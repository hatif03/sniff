"""
Simple integration test without pytest dependency.
Tests that all components can be imported and work together.
"""

import sys
from datetime import datetime
from pathlib import Path

print("=" * 70)
print("SHERLOCK INTEGRATION TEST SUITE")
print("=" * 70)

# Test 1: Import all core components
print("\n[1/10] Testing core component imports...")
try:
    from src.core.config import SherlockConfig, PlaywrightConfig, BedrockConfig, SlackConfig
    from src.core.persona import PersonaProfile
    from src.core.models import (
        Observation,
        AgentDecision,
        ActionResult,
        DiagnosisResult,
        SanitizedDecision,
    )
    from src.core.validation import DecisionSanitizer, ActionWhitelist
    from src.core.trace_logger import TraceLogger
    from src.core.state_machine import RunState, StateMachine, RunOutcome
    from src.core.orchestrator import RunOrchestrator
    print("✅ All core imports successful")
except Exception as e:
    print(f"❌ Core import failed: {e}")
    sys.exit(1)

# Test 2: Import agent service
print("\n[2/10] Testing agent service imports...")
try:
    from src.agent.decision_service import DecisionService
    from src.agent.bedrock_client import BedrockClient
    print("✅ Agent service imports successful")
except Exception as e:
    print(f"❌ Agent service import failed: {e}")
    sys.exit(1)

# Test 3: Import diagnosis and alerting
print("\n[3/10] Testing diagnosis and alerting imports...")
try:
    from src.diagnosis.classifier import DiagnosisClassifier
    from src.alerts.slack import SlackAlert
    from src.evidence.report_builder import RunReport, ReportBuilder
    print("✅ Diagnosis and alerting imports successful")
except Exception as e:
    print(f"❌ Diagnosis/alerting import failed: {e}")
    sys.exit(1)

# Test 4: Create configuration
print("\n[4/10] Testing configuration creation...")
try:
    config = SherlockConfig(
        playwright=PlaywrightConfig(
            headless=True,
            screenshot_on_action=True,
            timeout=30000,
        ),
        bedrock=BedrockConfig(
            region="us-west-2",
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            timeout_seconds=30,
        ),
        slack=SlackConfig(
            webhook_url="https://hooks.slack.com/services/TEST/TEST/TEST",
            channel="#sherlock-alerts",
        ),
    )
    assert config.playwright.headless is True
    assert config.bedrock.region == "us-west-2"
    assert config.slack.channel == "#sherlock-alerts"
    print("✅ Configuration created successfully")
except Exception as e:
    print(f"❌ Configuration creation failed: {e}")
    sys.exit(1)

# Test 5: Create persona
print("\n[5/10] Testing persona creation...")
try:
    persona = PersonaProfile(
        name="test_user",
        display_name="Test User",
        description="A test user for integration testing",
        patience_level=0.7,
        technical_proficiency=0.8,
        exploration_tendency=0.5,
    )
    assert persona.name == "test_user"
    assert persona.display_name == "Test User"
    context = persona.to_prompt_context()
    assert "test_user" in context or "Test User" in context
    print("✅ Persona created successfully")
except Exception as e:
    print(f"❌ Persona creation failed: {e}")
    sys.exit(1)

# Test 6: Test data models
print("\n[6/10] Testing data models (Observation, AgentDecision, ActionResult)...")
try:
    # Create observation
    obs = Observation(
        runId="test-integration-123",
        step=1,
        timestamp=datetime.now().isoformat(),
        url="https://example.com/signup",
        screenshotPath="/tmp/test_screenshot.png",
        visibleText=["Sign Up", "Email", "Password", "Continue"],
        timing={"ttfb": 150, "domReady": 300},
        consoleErrors=[],
        networkEvents=[],
        lastActionResult={
            "success": True,
            "action": "navigate",
            "target": "https://example.com/signup",
        },
    )
    assert obs.runId == "test-integration-123"
    assert "Sign Up" in obs.visibleText

    # Create agent decision
    decision = AgentDecision(
        action="type",
        target="email input field",
        inputText="test@example.com",
        reasoningSummary="Located email input field, entering test email address",
        confidence=0.92,
    )
    assert decision.action == "type"
    assert decision.inputText == "test@example.com"

    # Create action result
    result = ActionResult(
        success=True,
        action="type",
        status="success",
        target="email input field",
        durationMs=180,
    )
    assert result.success is True
    assert result.status == "success"

    print("✅ Data models working correctly")
except Exception as e:
    print(f"❌ Data models test failed: {e}")
    sys.exit(1)

# Test 7: Test decision validation and sanitization
print("\n[7/10] Testing decision validation and sanitization...")
try:
    from pydantic import ValidationError

    sanitizer = DecisionSanitizer()

    # Test valid decision - tap doesn't require inputText
    valid_decision = AgentDecision(
        action="tap",
        target="Sign Up button",
        reasoningSummary="Tapping the sign up button",
        confidence=0.95,
    )
    sanitized_valid = sanitizer.sanitize(valid_decision)
    assert sanitized_valid.wasSanitized is False
    assert sanitized_valid.decision.action == "tap"

    # Test valid type decision with inputText
    valid_type_decision = AgentDecision(
        action="type",
        target="email field",
        inputText="test@example.com",
        reasoningSummary="Typing email",
        confidence=0.9,
    )
    sanitized_type = sanitizer.sanitize(valid_type_decision)
    assert sanitized_type.wasSanitized is False
    assert sanitized_type.decision.inputText == "test@example.com"

    # Test that invalid decision (type without inputText) is caught at model level
    try:
        invalid_decision = AgentDecision(
            action="type",
            target="email field",
            reasoningSummary="Typing into email",
            confidence=0.8,
        )
        print("❌ Model validation should have caught missing inputText")
        sys.exit(1)
    except ValidationError:
        # This is expected - model validates before sanitizer
        pass

    print("✅ Decision validation working correctly")
except Exception as e:
    print(f"❌ Decision validation test failed: {e}")
    sys.exit(1)

# Test 8: Test state machine
print("\n[8/10] Testing state machine transitions...")
try:
    sm = StateMachine()

    # Test initial state
    assert sm.current_state == RunState.SETUP

    # Test valid transitions
    sm.transition(RunState.NAVIGATE, "Starting navigation")
    assert sm.current_state == RunState.NAVIGATE

    sm.transition(RunState.ACTION_EXECUTION, "Executing actions")
    assert sm.current_state == RunState.ACTION_EXECUTION

    sm.transition(RunState.EVALUATE_PROGRESS, "Evaluating progress")
    assert sm.current_state == RunState.EVALUATE_PROGRESS

    sm.transition(RunState.DONE, "Test completed successfully")
    assert sm.current_state == RunState.DONE

    # Test transition history
    history = sm.get_transition_history()
    assert len(history) > 0

    # Test invalid transition detection
    sm2 = StateMachine()
    try:
        sm2.transition(RunState.DIAGNOSE, "Invalid transition")  # Invalid from SETUP
        print("❌ State machine should reject invalid transitions")
        sys.exit(1)
    except ValueError:
        pass  # Expected

    print("✅ State machine working correctly")
except Exception as e:
    print(f"❌ State machine test failed: {e}")
    sys.exit(1)

# Test 9: Test action whitelist
print("\n[9/10] Testing action whitelist...")
try:
    from src.core.models import ActionType

    # Test with specific allowed actions
    whitelist = ActionWhitelist(
        allowed_actions={ActionType.TAP, ActionType.TYPE, ActionType.SCROLL, ActionType.WAIT}
    )

    assert whitelist.is_allowed(ActionType.TAP) is True
    assert whitelist.is_allowed(ActionType.TYPE) is True
    assert whitelist.is_allowed(ActionType.ABORT) is False

    # Test with default allowed actions
    whitelist_default = ActionWhitelist()
    assert whitelist_default.is_allowed(ActionType.TAP) is True
    assert whitelist_default.is_allowed(ActionType.WAIT) is True

    print("✅ Action whitelist working correctly")
except Exception as e:
    print(f"❌ Action whitelist test failed: {e}")
    sys.exit(1)

# Test 10: Test diagnosis classification
print("\n[10/10] Testing diagnosis classification...")
try:
    classifier = DiagnosisClassifier()

    # Create observation with error signals
    error_obs = Observation(
        runId="test-error-123",
        step=5,
        timestamp=datetime.now().isoformat(),
        url="https://example.com/signup",
        screenshotPath="/tmp/error.png",
        visibleText=["Error 500", "Server Error"],
        timing={"ttfb": 5000, "domReady": 6000},
        consoleErrors=["TypeError: Cannot read property 'user' of undefined"],
        networkEvents=[
            {"type": "response", "status": 500, "url": "/api/signup"}
        ],
        lastActionResult={"success": False, "error": "Request timeout"},
    )

    action_history = [
        ActionResult(
            success=False,
            action="tap",
            status="timeout",
            target="Submit button",
            durationMs=5500,
            error="Timeout waiting for server response",
        )
    ]

    # Classify the issue (requires list of observations)
    diagnosis = classifier.classify(
        observations=[error_obs],
        action_results=action_history,
        run_goal="Complete signup successfully",
        stuck_reason="Timeout waiting for server response after 5 seconds"
    )

    assert diagnosis is not None
    assert diagnosis.rootCause in ["Backend", "Performance", "Integration", "UX/Content"]
    assert diagnosis.severity in ["P0", "P1", "P2", "P3"]
    assert len(diagnosis.reproSteps) > 0

    print("✅ Diagnosis classification working correctly")
    print(f"   Detected: {diagnosis.rootCause} ({diagnosis.severity})")
except Exception as e:
    print(f"❌ Diagnosis classification test failed: {e}")
    sys.exit(1)

# Summary
print("\n" + "=" * 70)
print("INTEGRATION TEST SUMMARY")
print("=" * 70)
print("\n✅ All 10 integration tests PASSED\n")
print("Components verified:")
print("  ✓ Configuration system")
print("  ✓ Persona management")
print("  ✓ Data models (Observation, AgentDecision, ActionResult)")
print("  ✓ Decision validation and sanitization")
print("  ✓ State machine with transitions")
print("  ✓ Action whitelist")
print("  ✓ Diagnosis classification")
print("  ✓ Agent service (imports)")
print("  ✓ Alerting system (imports)")
print("  ✓ Report builder (imports)")
print("\n🎉 System ready for end-to-end testing!")
print("=" * 70)
