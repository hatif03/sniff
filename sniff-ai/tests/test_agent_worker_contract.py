"""Integration tests for agent-worker contract edge cases.

Tests the contract safety layer between agent decisions and worker execution:
- Decision validation edge cases
- Sanitization and fallback behavior
- Action whitelist enforcement
- Missing required fields
- Malformed decisions
"""

import pytest
from pydantic import ValidationError

from src.core.models import (
    AgentDecision,
    SanitizedDecision,
    ActionResult,
    Observation,
)
from src.core.validation import (
    DecisionSanitizer,
    ActionWhitelist,
    FallbackPolicy,
)


class TestAgentDecisionValidation:
    """Test cases for AgentDecision validation."""

    def test_valid_tap_action(self):
        """Test valid tap action with all required fields."""
        decision = AgentDecision(
            action="tap",
            target="Submit button",
            reasoningSummary="User needs to submit form",
            confidence=0.9,
        )
        assert decision.action == "tap"
        assert decision.target == "Submit button"

    def test_valid_type_action(self):
        """Test valid type action with inputText."""
        decision = AgentDecision(
            action="type",
            target="Email field",
            inputText="test@example.com",
            reasoningSummary="Enter email address",
            confidence=0.95,
        )
        assert decision.action == "type"
        assert decision.inputText == "test@example.com"

    def test_type_action_missing_input_text(self):
        """Test that type action without inputText raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AgentDecision(
                action="type",
                target="Email field",
                reasoningSummary="Enter email",
                confidence=0.9,
            )
        assert "inputText is REQUIRED" in str(exc_info.value)

    def test_tap_action_missing_target(self):
        """Test that tap action without target raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AgentDecision(
                action="tap",
                reasoningSummary="Tap button",
                confidence=0.9,
            )
        assert "target is REQUIRED" in str(exc_info.value)

    def test_scroll_action_missing_direction(self):
        """Test that scroll action without direction raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AgentDecision(
                action="scroll",
                reasoningSummary="Scroll to see more content",
                confidence=0.8,
            )
        assert "scrollDirection is REQUIRED" in str(exc_info.value)

    def test_valid_scroll_action(self):
        """Test valid scroll action with direction."""
        decision = AgentDecision(
            action="scroll",
            scrollDirection="down",
            reasoningSummary="Scroll down to view more",
            confidence=0.85,
        )
        assert decision.action == "scroll"
        assert decision.scrollDirection == "down"

    def test_wait_action_missing_duration(self):
        """Test that wait action without duration raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AgentDecision(
                action="wait",
                reasoningSummary="Wait for page to load",
                confidence=0.7,
            )
        assert "waitDurationMs is REQUIRED" in str(exc_info.value)

    def test_valid_wait_action(self):
        """Test valid wait action with duration."""
        decision = AgentDecision(
            action="wait",
            waitDurationMs=3000,
            reasoningSummary="Wait for animation to complete",
            confidence=0.75,
        )
        assert decision.action == "wait"
        assert decision.waitDurationMs == 3000

    def test_abort_action_missing_reason(self):
        """Test that abort action without reason raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AgentDecision(
                action="abort",
                reasoningSummary="Cannot proceed",
                confidence=0.0,
            )
        assert "abortReason is REQUIRED" in str(exc_info.value)

    def test_valid_abort_action(self):
        """Test valid abort action with reason."""
        decision = AgentDecision(
            action="abort",
            abortReason="CAPTCHA detected, cannot proceed",
            reasoningSummary="Encountered CAPTCHA",
            confidence=0.0,
        )
        assert decision.action == "abort"
        assert decision.abortReason == "CAPTCHA detected, cannot proceed"

    def test_confidence_range_validation(self):
        """Test that confidence must be between 0 and 1."""
        # Test confidence > 1
        with pytest.raises(ValidationError):
            AgentDecision(
                action="wait",
                waitDurationMs=1000,
                reasoningSummary="Test",
                confidence=1.5,
            )

        # Test confidence < 0
        with pytest.raises(ValidationError):
            AgentDecision(
                action="wait",
                waitDurationMs=1000,
                reasoningSummary="Test",
                confidence=-0.1,
            )

    def test_fallback_action_nested(self):
        """Test that fallback action can be nested."""
        fallback = AgentDecision(
            action="wait",
            waitDurationMs=2000,
            reasoningSummary="Fallback wait",
            confidence=0.5,
        )

        decision = AgentDecision(
            action="tap",
            target="Submit",
            reasoningSummary="Primary action",
            confidence=0.8,
            fallbackAction=fallback,
        )

        assert decision.fallbackAction is not None
        assert decision.fallbackAction.action == "wait"


class TestDecisionSanitizer:
    """Test cases for DecisionSanitizer."""

    def test_sanitize_valid_decision(self):
        """Test sanitizing a valid decision."""
        sanitizer = DecisionSanitizer()

        decision = AgentDecision(
            action="tap",
            target="Submit",
            reasoningSummary="Submit form",
            confidence=0.9,
        )

        result = sanitizer.sanitize(decision)

        assert isinstance(result, SanitizedDecision)
        assert not result.wasSanitized
        assert result.sanitizationReason is None
        assert result.decision.action == "tap"

    def test_sanitize_dict_input(self):
        """Test sanitizing from dict input."""
        sanitizer = DecisionSanitizer()

        decision_dict = {
            "action": "tap",
            "target": "Submit",
            "reasoningSummary": "Submit form",
            "confidence": 0.9,
        }

        result = sanitizer.sanitize(decision_dict)

        assert isinstance(result, SanitizedDecision)
        assert not result.wasSanitized
        assert result.decision.action == "tap"

    def test_sanitize_invalid_dict_with_fallback(self):
        """Test sanitizing invalid dict creates fallback."""
        sanitizer = DecisionSanitizer()

        # Missing required field for type action
        invalid_dict = {
            "action": "type",
            "target": "Email",
            # Missing inputText
            "reasoningSummary": "Enter email",
            "confidence": 0.9,
        }

        result = sanitizer.sanitize(invalid_dict, allow_fallback=True)

        assert isinstance(result, SanitizedDecision)
        assert result.wasSanitized
        assert result.sanitizationReason is not None
        assert result.originalAction == "type"
        assert result.decision.action == "wait"  # Fallback to wait

    def test_sanitize_invalid_dict_without_fallback(self):
        """Test sanitizing invalid dict without fallback raises error."""
        sanitizer = DecisionSanitizer()

        invalid_dict = {
            "action": "type",
            "target": "Email",
            # Missing inputText
            "reasoningSummary": "Enter email",
            "confidence": 0.9,
        }

        with pytest.raises(ValidationError):
            sanitizer.sanitize(invalid_dict, allow_fallback=False)

    def test_whitelist_violation_with_fallback(self):
        """Test action whitelist violation creates fallback."""
        # Create whitelist without 'abort'
        whitelist = ActionWhitelist(allowed_actions={"tap", "type", "scroll", "wait", "back"})
        sanitizer = DecisionSanitizer(action_whitelist=whitelist)

        decision = AgentDecision(
            action="abort",
            abortReason="Test abort",
            reasoningSummary="Abort test",
            confidence=0.0,
        )

        result = sanitizer.sanitize(decision, allow_fallback=True)

        assert result.wasSanitized
        assert "not allowed" in result.sanitizationReason.lower()
        assert result.decision.action == "wait"

    def test_whitelist_violation_without_fallback(self):
        """Test whitelist violation without fallback raises error."""
        whitelist = ActionWhitelist(allowed_actions={"tap", "type"})
        sanitizer = DecisionSanitizer(action_whitelist=whitelist)

        decision = AgentDecision(
            action="scroll",
            scrollDirection="down",
            reasoningSummary="Scroll",
            confidence=0.8,
        )

        with pytest.raises(ValueError) as exc_info:
            sanitizer.sanitize(decision, allow_fallback=False)

        assert "not in whitelist" in str(exc_info.value)


class TestActionWhitelist:
    """Test cases for ActionWhitelist."""

    def test_default_whitelist_allows_all_actions(self):
        """Test that default whitelist allows all standard actions."""
        whitelist = ActionWhitelist()

        assert whitelist.is_allowed("tap")
        assert whitelist.is_allowed("type")
        assert whitelist.is_allowed("scroll")
        assert whitelist.is_allowed("wait")
        assert whitelist.is_allowed("back")
        assert whitelist.is_allowed("abort")

    def test_custom_whitelist(self):
        """Test custom whitelist configuration."""
        whitelist = ActionWhitelist(allowed_actions={"tap", "type"})

        assert whitelist.is_allowed("tap")
        assert whitelist.is_allowed("type")
        assert not whitelist.is_allowed("scroll")
        assert not whitelist.is_allowed("wait")

    def test_invalid_action_not_allowed(self):
        """Test that invalid action strings are not allowed."""
        whitelist = ActionWhitelist()

        assert not whitelist.is_allowed("invalid_action")
        assert not whitelist.is_allowed("delete")
        assert not whitelist.is_allowed("execute_code")

    def test_risky_actions_flagged(self):
        """Test that risky actions are properly flagged."""
        whitelist = ActionWhitelist()

        assert whitelist.is_risky("abort")
        assert not whitelist.is_risky("tap")
        assert not whitelist.is_risky("type")


class TestFallbackPolicy:
    """Test cases for FallbackPolicy."""

    def test_create_wait_fallback(self):
        """Test creating a wait fallback action."""
        policy = FallbackPolicy()

        fallback = policy.create_wait_fallback("Test reason")

        assert fallback.action == "wait"
        assert fallback.waitDurationMs == 2000
        assert "Test reason" in fallback.reasoningSummary
        assert fallback.confidence == 0.1

    def test_create_abort_fallback(self):
        """Test creating an abort fallback action."""
        policy = FallbackPolicy()

        fallback = policy.create_abort_fallback("Critical error")

        assert fallback.action == "abort"
        assert fallback.abortReason == "Critical error"
        assert "Critical error" in fallback.reasoningSummary
        assert fallback.confidence == 0.0

    def test_create_screenshot_wait_fallback(self):
        """Test creating a diagnostic wait fallback."""
        policy = FallbackPolicy()

        fallback = policy.create_screenshot_wait_fallback("Need observation")

        assert fallback.action == "wait"
        assert fallback.waitDurationMs == 1000
        assert "Need observation" in fallback.reasoningSummary
        assert fallback.confidence == 0.2


class TestActionResult:
    """Test cases for ActionResult model."""

    def test_successful_action_result(self):
        """Test creating a successful action result."""
        result = ActionResult(
            success=True,
            action="tap",
            status="success",
            target="Submit button",
            durationMs=150,
        )

        assert result.success
        assert result.status == "success"
        assert result.action == "tap"
        assert result.durationMs == 150

    def test_failed_action_result(self):
        """Test creating a failed action result."""
        result = ActionResult(
            success=False,
            action="tap",
            status="element_not_found",
            target="Submit button",
            error="Element not found on page",
            durationMs=500,
        )

        assert not result.success
        assert result.status == "element_not_found"
        assert result.error == "Element not found on page"

    def test_timeout_action_result(self):
        """Test creating a timeout action result."""
        result = ActionResult(
            success=False,
            action="wait",
            status="timeout",
            durationMs=5000,
            error="Operation timed out",
        )

        assert not result.success
        assert result.status == "timeout"


class TestObservation:
    """Test cases for Observation model."""

    def test_minimal_observation(self):
        """Test creating minimal observation."""
        obs = Observation(
            runId="test-run-123",
            step=1,
            url="https://example.com",
            screenshotPath="/path/to/screenshot.png",
        )

        assert obs.runId == "test-run-123"
        assert obs.step == 1
        assert obs.url == "https://example.com"
        assert obs.visibleText == []
        assert obs.consoleErrors == []
        assert obs.networkEvents == []

    def test_full_observation(self):
        """Test creating observation with all fields."""
        obs = Observation(
            runId="test-run-123",
            step=5,
            url="https://example.com/signup",
            screenshotPath="/path/to/screenshot.png",
            visibleText=["Sign Up", "Email", "Password"],
            timing={"ttfb": 200, "domReady": 500},
            consoleErrors=["Error: Failed to load resource"],
            networkEvents=[{"url": "https://api.example.com", "status": 500}],
            lastActionResult={
                "success": True,
                "action": "tap",
                "status": "success",
            },
        )

        assert len(obs.visibleText) == 3
        assert len(obs.consoleErrors) == 1
        assert len(obs.networkEvents) == 1
        assert obs.lastActionResult["success"]


class TestContractIntegration:
    """Integration tests for full agent-worker contract flow."""

    def test_valid_decision_to_action_flow(self):
        """Test valid decision flows through sanitization to action result."""
        # 1. Agent creates decision
        decision = AgentDecision(
            action="tap",
            target="Submit button",
            reasoningSummary="Submit registration form",
            confidence=0.92,
        )

        # 2. Sanitizer validates decision
        sanitizer = DecisionSanitizer()
        sanitized = sanitizer.sanitize(decision)

        assert not sanitized.wasSanitized
        assert sanitized.decision.action == "tap"

        # 3. Worker executes and returns result
        result = ActionResult(
            success=True,
            action="tap",
            status="success",
            target="Submit button",
            durationMs=120,
        )

        assert result.success

    def test_invalid_decision_fallback_flow(self):
        """Test invalid decision triggers fallback and safe execution."""
        # 1. Agent creates invalid decision (missing inputText for type)
        invalid_dict = {
            "action": "type",
            "target": "Email",
            "reasoningSummary": "Enter email",
            "confidence": 0.9,
        }

        # 2. Sanitizer creates fallback
        sanitizer = DecisionSanitizer()
        sanitized = sanitizer.sanitize(invalid_dict, allow_fallback=True)

        assert sanitized.wasSanitized
        assert sanitized.decision.action == "wait"  # Fallback to safe wait
        assert sanitized.originalAction == "type"

        # 3. Worker executes fallback (wait action)
        result = ActionResult(
            success=True,
            action="wait",
            status="success",
            durationMs=2000,
        )

        assert result.success

    def test_whitelist_violation_fallback_flow(self):
        """Test whitelist violation triggers fallback."""
        # 1. Create restricted whitelist
        whitelist = ActionWhitelist(allowed_actions={"tap", "type", "wait"})
        sanitizer = DecisionSanitizer(action_whitelist=whitelist)

        # 2. Agent creates decision with disallowed action
        decision = AgentDecision(
            action="scroll",
            scrollDirection="down",
            reasoningSummary="Scroll down",
            confidence=0.85,
        )

        # 3. Sanitizer rejects and creates fallback
        sanitized = sanitizer.sanitize(decision, allow_fallback=True)

        assert sanitized.wasSanitized
        assert "not allowed" in sanitized.sanitizationReason.lower()
        assert sanitized.decision.action == "wait"
