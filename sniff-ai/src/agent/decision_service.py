"""Agent Decision Service for sniff.

Converts observations into validated agent decisions using a vision-capable
Tier 3 reasoning LLM (Gemini by default - see gemini_client.py).
Implements strict schema validation with bounded retries for malformed outputs.

Architecture boundary:
- Agent Service returns decisions ONLY
- Never controls browser directly
- Orchestrator owns execution authority
"""

import base64
import json
import logging
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from pydantic import ValidationError

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from src.core.models import AgentDecision, Observation

from .llm_errors import LLMInvocationError, LLMTimeoutError
from .prompts import (
    build_repair_prompt,
    build_system_prompt,
    build_user_message,
    build_user_message_with_vision,
)
from .tier_router import TierRouter

logger = logging.getLogger(__name__)


class DecisionService:
    """Service for generating validated agent decisions from observations.

    Responsibilities:
    - Construct decision prompts from observations + persona + goal
    - Invoke the Tier 3 reasoning LLM with proper system/user messages
    - Validate response against AgentDecision schema
    - Retry with repair prompts for malformed outputs (bounded)
    - Log reasoning summaries for evidence timeline
    """

    def __init__(
        self,
        llm_client: Any,
        max_repair_retries: int = 2,
        decision_temperature: float = 0.7,
        tier_router: TierRouter | None = None,
    ):
        """Initialize decision service.

        Args:
            llm_client: Tier 3 reasoning client (GeminiClient by default -
                must expose invoke()/invoke_with_json_response() and a
                `model_id` attribute; see gemini_client.py).
            max_repair_retries: Maximum attempts to repair malformed outputs
            decision_temperature: Temperature for decision generation (0-1)
            tier_router: Optional Tier 2 (Jev) router. When None or disabled,
                behavior is identical to before Jev existed - context
                enrichment is skipped and the decision critic never fires.
        """
        self.client = llm_client
        self.max_repair_retries = max_repair_retries
        self.decision_temperature = decision_temperature
        self.tier_router = tier_router

        # Store reasoning timeline for evidence collection
        self.reasoning_timeline: list[dict] = []

    def get_decision(
        self,
        observation: Observation,
        goal: str,
        persona_description: str | None = None,
        recent_history: list[dict] | None = None
    ) -> AgentDecision:
        """Generate validated agent decision from observation.

        Args:
            observation: Current observation from execution worker
            goal: User-defined goal for the run
            persona_description: Optional persona behavior profile
            recent_history: Optional recent action history for context

        Returns:
            Validated AgentDecision

        Raises:
            DecisionGenerationError: If decision generation fails after retries
            DecisionValidationError: If decision validation fails after repair attempts
            DecisionTimeoutError: If the reasoning LLM request times out
        """
        # Build prompts
        system_prompt = build_system_prompt(persona_description)

        # Tier 2 (Jev): parallel context enrichment, computed before the
        # expensive Tier 3 call so the reasoning model gets a pre-digested
        # screen classification instead of re-deriving it every step.
        # Returns None (no annotation) whenever Jev is disabled/unavailable.
        jev_signals = None
        if self.tier_router:
            jev_signals = self.tier_router.enrich_context(goal=goal, visible_text=observation.visibleText)

        # Load and encode screenshot for vision
        screenshot_base64 = None
        screenshot_path = observation.screenshotPath
        if screenshot_path and Path(screenshot_path).exists():
            try:
                screenshot_base64 = self._load_and_compress_screenshot(screenshot_path)
                logger.info(f"Loaded and compressed screenshot: {len(screenshot_base64)} bytes (base64)")
            except Exception as e:
                logger.warning(f"Failed to load screenshot from {screenshot_path}: {e}")

        # Build user message with vision if screenshot available.
        # "anthropic"-style content blocks (image+source, text) are the
        # canonical shape GeminiClient._build_contents() understands.
        if screenshot_base64:
            user_message = build_user_message_with_vision(
                goal=goal,
                observation=observation.model_dump(),
                screenshot_base64=screenshot_base64,
                recent_history=recent_history,
                format_style="anthropic",
                jev_signals=jev_signals,
            )
        else:
            # Fallback to text-only if no screenshot
            user_message = build_user_message(
                goal=goal,
                observation=observation.model_dump(),
                recent_history=recent_history,
                jev_signals=jev_signals,
            )

        # Log decision request
        logger.info(
            f"Generating decision for step {observation.step} at {observation.url}"
        )

        # Primary decision attempt
        try:
            decision = self._attempt_decision(system_prompt, user_message, goal, recent_history)
            self._log_reasoning(observation, decision, attempt=1, repaired=False)
            return decision

        except DecisionValidationError as e:
            logger.warning(f"Initial decision validation failed: {e}")
            malformed_output = e.malformed_output
            validation_error = str(e.validation_error)

            # Attempt repair with bounded retries
            for attempt in range(1, self.max_repair_retries + 1):
                try:
                    logger.info(f"Attempting repair {attempt}/{self.max_repair_retries}")
                    decision = self._attempt_repair(
                        malformed_output,
                        validation_error,
                        system_prompt
                    )
                    self._log_reasoning(observation, decision, attempt=attempt + 1, repaired=True)
                    logger.info(f"Successfully repaired decision on attempt {attempt}")
                    return decision

                except DecisionValidationError as repair_error:
                    logger.warning(f"Repair attempt {attempt} failed: {repair_error}")
                    malformed_output = repair_error.malformed_output
                    validation_error = str(repair_error.validation_error)

                    if attempt == self.max_repair_retries:
                        # Final attempt failed - use fallback
                        logger.error(
                            "All repair attempts exhausted. "
                            "Returning safe fallback decision."
                        )
                        fallback = self._create_fallback_decision(observation, str(e))
                        self._log_reasoning(
                            observation,
                            fallback,
                            attempt=attempt + 1,
                            repaired=False,
                            is_fallback=True
                        )
                        return fallback

        except LLMTimeoutError as e:
            logger.error(f"LLM timeout: {e}")
            raise DecisionTimeoutError(
                f"Decision generation timed out: {e}"
            ) from e

        except LLMInvocationError as e:
            logger.error(f"LLM invocation failed: {e}")
            raise DecisionGenerationError(
                f"Failed to generate decision: {e}"
            ) from e

    def _attempt_decision(
        self,
        system_prompt: str,
        user_message: str,
        goal: str,
        recent_history: list[dict] | None = None,
    ) -> AgentDecision:
        """Attempt to generate and validate a decision.

        Args:
            system_prompt: System prompt for the reasoning LLM
            user_message: User message with observation
            goal: Run goal, used only for the Tier 2 (Jev) critic gate below
            recent_history: Recent action history, used only for the critic gate

        Returns:
            Validated AgentDecision

        Raises:
            DecisionValidationError: If validation fails, or if the Tier 2
                (Jev) critic flags the decision as implausible - routed
                through the same bounded repair loop as a schema failure.
        """
        try:
            # Invoke the Tier 3 reasoning LLM
            response = self.client.invoke_with_json_response(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=self.decision_temperature,
                max_tokens=2048
            )

            # Validate against schema
            decision = AgentDecision.model_validate(response)

            # Tier 2 (Jev) Generator-Critic gate: a cheap sanity check on the
            # Tier 3 decision before it's executed. A low-confidence critique
            # is treated exactly like a validation failure so it flows
            # through the existing repair-retry mechanism rather than a new
            # parallel retry path. No-op whenever Jev is disabled.
            if self.tier_router and self.tier_router.critique_decision(
                goal=goal,
                reasoning_summary=decision.reasoningSummary,
                action=decision.action,
                target=decision.target,
                recent_history=recent_history,
            ):
                raise DecisionValidationError(
                    validation_error=(
                        "Jev critic (Tier 2): this action was flagged as unlikely to "
                        "progress toward the goal given the reasoning and recent history."
                    ),
                    malformed_output=decision.model_dump_json(),
                )

            return decision

        except ValidationError as e:
            raise DecisionValidationError(
                validation_error=e,
                malformed_output=json.dumps(response, indent=2)
            ) from e

        except LLMInvocationError as e:
            # If response isn't JSON, treat as malformed
            if hasattr(e, 'details') and isinstance(e.details, str):
                raise DecisionValidationError(
                    validation_error=str(e),
                    malformed_output=e.details
                ) from e
            raise

    def _attempt_repair(
        self,
        malformed_output: str,
        validation_error: str,
        original_system_prompt: str
    ) -> AgentDecision:
        """Attempt to repair malformed decision output.

        Args:
            malformed_output: The invalid JSON from previous attempt
            validation_error: Validation error message
            original_system_prompt: Original system prompt for context

        Returns:
            Validated AgentDecision

        Raises:
            DecisionValidationError: If repair validation fails
        """
        repair_message = build_repair_prompt(malformed_output, validation_error)

        try:
            response = self.client.invoke_with_json_response(
                system_prompt=original_system_prompt,
                user_message=repair_message,
                temperature=0.3,  # Lower temperature for repair
                max_tokens=2048
            )

            decision = AgentDecision.model_validate(response)
            return decision

        except ValidationError as e:
            raise DecisionValidationError(
                validation_error=e,
                malformed_output=json.dumps(response, indent=2)
            ) from e

    def _create_fallback_decision(
        self,
        observation: Observation,
        error_context: str
    ) -> AgentDecision:
        """Create safe fallback decision when all attempts fail.

        Returns an 'abort' decision with error context.

        Args:
            observation: Current observation
            error_context: Context about why fallback is needed

        Returns:
            Safe abort decision
        """
        return AgentDecision(
            action="abort",
            target=None,
            abortReason=(
                f"Decision generation failed after {self.max_repair_retries + 1} attempts. "
                f"Error context: {error_context[:200]}"
            ),
            reasoningSummary="System fallback: Unable to generate valid decision",
            confidence=0.0,
            fallbackAction=None
        )

    def _log_reasoning(
        self,
        observation: Observation,
        decision: AgentDecision,
        attempt: int,
        repaired: bool,
        is_fallback: bool = False
    ):
        """Log decision reasoning to timeline for evidence collection.

        Args:
            observation: Current observation
            decision: Generated decision
            attempt: Attempt number
            repaired: Whether this was a repair attempt
            is_fallback: Whether this is a fallback decision
        """
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "runId": observation.runId,
            "step": observation.step,
            "url": observation.url,
            "action": decision.action,
            "target": decision.target,
            "reasoning": decision.reasoningSummary,
            "confidence": decision.confidence,
            "attempt": attempt,
            "repaired": repaired,
            "is_fallback": is_fallback
        }

        self.reasoning_timeline.append(entry)

        logger.info(
            f"Decision logged - Step {observation.step}: "
            f"{decision.action} on '{decision.target}' "
            f"(confidence: {decision.confidence:.2f}, attempt: {attempt}, "
            f"repaired: {repaired}, fallback: {is_fallback})"
        )

    def get_reasoning_timeline(self) -> list[dict]:
        """Get complete reasoning timeline for current run.

        Returns:
            List of reasoning entries with timestamps and decisions
        """
        return self.reasoning_timeline.copy()

    def clear_timeline(self):
        """Clear reasoning timeline (call at start of new run)."""
        self.reasoning_timeline.clear()

    def _load_and_compress_screenshot(self, screenshot_path: str, max_size_kb: int = 500) -> str:
        """Load and compress screenshot to reduce request size.

        Args:
            screenshot_path: Path to screenshot file
            max_size_kb: Maximum size in KB for compressed image

        Returns:
            Base64-encoded compressed image
        """
        if not HAS_PIL:
            # Fallback: just load and encode without compression
            with open(screenshot_path, 'rb') as f:
                screenshot_bytes = f.read()
            return base64.b64encode(screenshot_bytes).decode('utf-8')

        # Load image
        img = Image.open(screenshot_path)

        # Resize if too large (maintain aspect ratio)
        max_dimension = 1024  # Max width or height
        if max(img.width, img.height) > max_dimension:
            ratio = max_dimension / max(img.width, img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"Resized screenshot from original to {new_size}")

        # Convert to JPEG with compression
        buffer = BytesIO()

        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background

        # Start with high quality and reduce until size is acceptable
        quality = 85
        while quality > 20:
            buffer.seek(0)
            buffer.truncate()
            img.save(buffer, format='JPEG', quality=quality, optimize=True)
            size_kb = len(buffer.getvalue()) / 1024

            if size_kb <= max_size_kb:
                break
            quality -= 10

        # Encode to base64
        screenshot_bytes = buffer.getvalue()
        logger.info(f"Compressed screenshot: {len(screenshot_bytes) / 1024:.1f}KB at quality {quality}")
        return base64.b64encode(screenshot_bytes).decode('utf-8')


class DecisionGenerationError(Exception):
    """Raised when decision generation fails."""
    pass


class DecisionValidationError(Exception):
    """Raised when decision validation fails.

    Carries both the validation error and the malformed output
    for repair attempts.
    """

    def __init__(self, validation_error: Exception | str, malformed_output: str):
        self.validation_error = validation_error
        self.malformed_output = malformed_output
        super().__init__(f"Decision validation failed: {validation_error}")


class DecisionTimeoutError(Exception):
    """Raised when decision generation times out."""
    pass


def create_agent_service(config):
    """Create agent service instance from configuration.

    Args:
        config: SniffConfig instance

    Returns:
        DecisionService instance configured with a Gemini client (the
        vision-capable Tier 3 reasoning model) and, when
        config.typesafe.enabled, the Tier 2 (Jev) TierRouter.
    """
    from .gemini_client import GeminiClient
    from .tier_router import create_tier_router

    gemini_client = GeminiClient(
        project_id=config.gemini.project_id,
        region=config.gemini.region,
        model_id=config.gemini.model_id,
        fallback_model_id=config.gemini.fallback_model_id,
        timeout_seconds=config.gemini.timeout_seconds,
    )

    return DecisionService(
        llm_client=gemini_client,
        max_repair_retries=2,
        decision_temperature=config.gemini.temperature,
        tier_router=create_tier_router(config),
    )
