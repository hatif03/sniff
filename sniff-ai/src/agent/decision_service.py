"""Agent Decision Service for Sherlock.

Converts observations into validated agent decisions using Bedrock.
Implements strict schema validation with bounded retries for malformed outputs.

Architecture boundary:
- Agent Service returns decisions ONLY
- Never controls browser directly
- Orchestrator owns execution authority
"""

import json
import logging
import base64
from pathlib import Path
from typing import Optional
from datetime import datetime
from io import BytesIO
from pydantic import ValidationError

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from src.core.models import Observation, AgentDecision
from .bedrock_client import BedrockClient, BedrockInvocationError, BedrockTimeoutError
from .prompts import build_system_prompt, build_user_message, build_user_message_with_vision, build_repair_prompt

logger = logging.getLogger(__name__)


class DecisionService:
    """Service for generating validated agent decisions from observations.

    Responsibilities:
    - Construct decision prompts from observations + persona + goal
    - Invoke Bedrock with proper system/user messages
    - Validate response against AgentDecision schema
    - Retry with repair prompts for malformed outputs (bounded)
    - Log reasoning summaries for evidence timeline
    """

    def __init__(
        self,
        bedrock_client: Optional[BedrockClient] = None,
        max_repair_retries: int = 2,
        decision_temperature: float = 0.7
    ):
        """Initialize decision service.

        Args:
            bedrock_client: Bedrock client instance (creates default if None)
            max_repair_retries: Maximum attempts to repair malformed outputs
            decision_temperature: Temperature for decision generation (0-1)
        """
        self.client = bedrock_client or BedrockClient()
        self.max_repair_retries = max_repair_retries
        self.decision_temperature = decision_temperature

        # Store reasoning timeline for evidence collection
        self.reasoning_timeline: list[dict] = []

    def get_decision(
        self,
        observation: Observation,
        goal: str,
        persona_description: Optional[str] = None,
        recent_history: Optional[list[dict]] = None
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
            DecisionTimeoutError: If Bedrock request times out
        """
        # Build prompts
        system_prompt = build_system_prompt(persona_description)

        # Load and encode screenshot for vision
        screenshot_base64 = None
        screenshot_path = observation.screenshotPath
        if screenshot_path and Path(screenshot_path).exists():
            try:
                screenshot_base64 = self._load_and_compress_screenshot(screenshot_path)
                logger.info(f"Loaded and compressed screenshot: {len(screenshot_base64)} bytes (base64)")
            except Exception as e:
                logger.warning(f"Failed to load screenshot from {screenshot_path}: {e}")

        # Build user message with vision if screenshot available
        if screenshot_base64:
            # Determine vision format based on model type
            model_id = self.client.model_id.lower()
            if "nvidia" in model_id or "deepseek" in model_id:
                format_style = "openai"
            else:
                format_style = "anthropic"

            user_message = build_user_message_with_vision(
                goal=goal,
                observation=observation.model_dump(),
                screenshot_base64=screenshot_base64,
                recent_history=recent_history,
                format_style=format_style
            )
        else:
            # Fallback to text-only if no screenshot
            user_message = build_user_message(
                goal=goal,
                observation=observation.model_dump(),
                recent_history=recent_history
            )

        # Log decision request
        logger.info(
            f"Generating decision for step {observation.step} at {observation.url}"
        )

        # Primary decision attempt
        try:
            decision = self._attempt_decision(system_prompt, user_message)
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
                            f"All repair attempts exhausted. "
                            f"Returning safe fallback decision."
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

        except BedrockTimeoutError as e:
            logger.error(f"Bedrock timeout: {e}")
            raise DecisionTimeoutError(
                f"Decision generation timed out: {e}"
            ) from e

        except BedrockInvocationError as e:
            logger.error(f"Bedrock invocation failed: {e}")
            raise DecisionGenerationError(
                f"Failed to generate decision: {e}"
            ) from e

    def _attempt_decision(self, system_prompt: str, user_message: str) -> AgentDecision:
        """Attempt to generate and validate a decision.

        Args:
            system_prompt: System prompt for Bedrock
            user_message: User message with observation

        Returns:
            Validated AgentDecision

        Raises:
            DecisionValidationError: If validation fails
        """
        try:
            # Invoke Bedrock
            response = self.client.invoke_with_json_response(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=self.decision_temperature,
                max_tokens=2048
            )

            # Validate against schema
            decision = AgentDecision.model_validate(response)
            return decision

        except ValidationError as e:
            raise DecisionValidationError(
                validation_error=e,
                malformed_output=json.dumps(response, indent=2)
            ) from e

        except BedrockInvocationError as e:
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
            "timestamp": datetime.utcnow().isoformat(),
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
        config: SherlockConfig instance

    Returns:
        DecisionService instance configured with Bedrock client
    """
    from .bedrock_client import BedrockClient

    bedrock_client = BedrockClient(
        model_id=config.bedrock.model_id,
        region=config.bedrock.region,
        timeout_seconds=config.bedrock.timeout_seconds,
        max_retries=config.bedrock.max_retries,
    )

    return DecisionService(
        bedrock_client=bedrock_client,
        max_repair_retries=2,
        decision_temperature=config.bedrock.temperature,
    )
