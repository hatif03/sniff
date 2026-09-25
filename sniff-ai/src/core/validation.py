"""Decision validation and sanitization layer.

This module implements:
- Decision sanitization (cleaning malformed agent outputs)
- Action whitelist enforcement
- Fallback policy for invalid decisions
- Contract safety between agent and worker

Architecture boundary enforcement:
- Ensures agent decisions are safe before execution
- Provides predictable fallbacks for contract violations
- Prevents flaky failures from malformed decisions
"""

import logging
from typing import Optional
from pydantic import ValidationError

from .models import AgentDecision, SanitizedDecision, ActionType

logger = logging.getLogger(__name__)


class ActionWhitelist:
    """Action whitelist manager for safety enforcement.

    Controls which actions are allowed based on context (domain, state, etc).
    """

    # Default allowed actions (can be configured per domain/context)
    DEFAULT_ALLOWED_ACTIONS = {
        ActionType.TAP,
        ActionType.TYPE,
        ActionType.SCROLL,
        ActionType.WAIT,
        ActionType.BACK,
        ActionType.ABORT,
    }

    # Risky actions that may need additional checks
    RISKY_ACTIONS = {
        ActionType.ABORT,  # Should only be used when genuinely stuck
    }

    def __init__(self, allowed_actions: Optional[set[ActionType]] = None):
        """Initialize whitelist with allowed actions.

        Args:
            allowed_actions: Set of allowed action types. If None, uses DEFAULT_ALLOWED_ACTIONS.
        """
        self.allowed_actions = allowed_actions or self.DEFAULT_ALLOWED_ACTIONS.copy()

    def is_allowed(self, action: str) -> bool:
        """Check if action is in whitelist.

        Args:
            action: Action type string to check

        Returns:
            True if action is allowed, False otherwise
        """
        try:
            action_type = ActionType(action)
            return action_type in self.allowed_actions
        except ValueError:
            return False

    def is_risky(self, action: str) -> bool:
        """Check if action is considered risky.

        Args:
            action: Action type string to check

        Returns:
            True if action is risky, False otherwise
        """
        try:
            action_type = ActionType(action)
            return action_type in self.RISKY_ACTIONS
        except ValueError:
            return False


class FallbackPolicy:
    """Fallback policy for invalid or failed decisions.

    Provides safe default actions when agent decisions are invalid or fail.
    """

    @staticmethod
    def create_wait_fallback(reason: str) -> AgentDecision:
        """Create a safe wait fallback action.

        Args:
            reason: Reason why fallback was needed

        Returns:
            AgentDecision configured for a safe wait action
        """
        return AgentDecision(
            action="wait",
            waitDurationMs=2000,
            reasoningSummary=f"Fallback wait action: {reason}",
            confidence=0.1,
        )

    @staticmethod
    def create_abort_fallback(reason: str) -> AgentDecision:
        """Create an abort fallback action.

        Args:
            reason: Reason why abort is needed

        Returns:
            AgentDecision configured for abort
        """
        return AgentDecision(
            action="abort",
            abortReason=reason,
            reasoningSummary=f"Fallback abort: {reason}",
            confidence=0.0,
        )

    @staticmethod
    def create_screenshot_wait_fallback(reason: str) -> AgentDecision:
        """Create a fallback that waits and captures state.

        Args:
            reason: Reason why fallback was needed

        Returns:
            AgentDecision configured for diagnostic wait
        """
        return AgentDecision(
            action="wait",
            waitDurationMs=1000,
            reasoningSummary=f"Diagnostic pause for observation: {reason}",
            confidence=0.2,
        )


class DecisionSanitizer:
    """Sanitizes and validates agent decisions before execution.

    Implements the contract safety layer between agent output and worker execution.
    """

    def __init__(
        self,
        action_whitelist: Optional[ActionWhitelist] = None,
        fallback_policy: Optional[FallbackPolicy] = None,
    ):
        """Initialize sanitizer with whitelist and fallback policy.

        Args:
            action_whitelist: Whitelist for allowed actions. If None, uses default.
            fallback_policy: Policy for generating fallback actions. If None, uses default.
        """
        self.whitelist = action_whitelist or ActionWhitelist()
        self.fallback = fallback_policy or FallbackPolicy()

    def sanitize(
        self,
        raw_decision: dict | AgentDecision,
        allow_fallback: bool = True,
    ) -> SanitizedDecision:
        """Sanitize and validate an agent decision.

        Args:
            raw_decision: Raw decision from agent (dict or AgentDecision)
            allow_fallback: Whether to use fallback on validation failure

        Returns:
            SanitizedDecision with validated decision or safe fallback

        Raises:
            ValidationError: If validation fails and allow_fallback is False
        """
        # Convert dict to AgentDecision if needed
        if isinstance(raw_decision, dict):
            try:
                decision = AgentDecision(**raw_decision)
            except ValidationError as e:
                logger.warning(f"Failed to parse agent decision: {e}")
                if allow_fallback:
                    return self._create_fallback_sanitized(
                        reason=f"Invalid decision format: {e}",
                        original_action=raw_decision.get("action"),
                    )
                raise
        else:
            decision = raw_decision

        # Check action whitelist
        if not self.whitelist.is_allowed(decision.action):
            logger.warning(f"Action '{decision.action}' not in whitelist")
            if allow_fallback:
                return self._create_fallback_sanitized(
                    reason=f"Action '{decision.action}' not allowed",
                    original_action=decision.action,
                )
            raise ValueError(f"Action '{decision.action}' not in whitelist")

        # Validate action-specific requirements (already handled by Pydantic model validator)
        # But double-check critical ones for safety
        sanitization_issues = self._check_sanitization_needs(decision)

        if sanitization_issues:
            logger.warning(f"Decision sanitization needed: {sanitization_issues}")
            if allow_fallback:
                return self._create_fallback_sanitized(
                    reason=f"Sanitization required: {sanitization_issues}",
                    original_action=decision.action,
                )
            raise ValueError(f"Decision sanitization failed: {sanitization_issues}")

        # Decision is valid
        return SanitizedDecision(
            decision=decision,
            wasSanitized=False,
        )

    def _check_sanitization_needs(self, decision: AgentDecision) -> Optional[str]:
        """Check if decision needs sanitization.

        Args:
            decision: AgentDecision to check

        Returns:
            String describing issue if sanitization needed, None otherwise
        """
        # Check type action has inputText
        if decision.action == "type" and not decision.inputText:
            return "type action missing inputText"

        # Check tap action has target
        if decision.action == "tap" and not decision.target:
            return "tap action missing target"

        # Check scroll has direction
        if decision.action == "scroll" and not decision.scrollDirection:
            return "scroll action missing scrollDirection"

        # Check wait has duration
        if decision.action == "wait" and not decision.waitDurationMs:
            return "wait action missing waitDurationMs"

        # Check abort has reason
        if decision.action == "abort" and not decision.abortReason:
            return "abort action missing abortReason"

        # Check confidence is reasonable
        if decision.confidence < 0.0 or decision.confidence > 1.0:
            return f"confidence {decision.confidence} out of range [0, 1]"

        return None

    def _create_fallback_sanitized(
        self,
        reason: str,
        original_action: Optional[str] = None,
    ) -> SanitizedDecision:
        """Create a sanitized decision with fallback action.

        Args:
            reason: Reason for fallback
            original_action: Original action that failed validation

        Returns:
            SanitizedDecision with fallback action
        """
        fallback_decision = self.fallback.create_wait_fallback(reason)

        return SanitizedDecision(
            decision=fallback_decision,
            wasSanitized=True,
            sanitizationReason=reason,
            originalAction=original_action,
        )

    def sanitize_with_retry(
        self,
        raw_decision: dict | AgentDecision,
        max_retries: int = 2,
    ) -> SanitizedDecision:
        """Sanitize decision with retry logic using fallback action.

        Args:
            raw_decision: Raw decision from agent
            max_retries: Maximum number of retries (not used in current implementation)

        Returns:
            SanitizedDecision with validated decision or fallback
        """
        # For now, just use single sanitization with fallback
        # In future, could retry with agent to get better decision
        return self.sanitize(raw_decision, allow_fallback=True)


def create_default_sanitizer() -> DecisionSanitizer:
    """Create a DecisionSanitizer with default configuration.

    Returns:
        Configured DecisionSanitizer instance
    """
    return DecisionSanitizer(
        action_whitelist=ActionWhitelist(),
        fallback_policy=FallbackPolicy(),
    )
