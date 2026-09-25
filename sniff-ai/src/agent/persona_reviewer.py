"""Persona Review Generator for Sherlock.

After a test run completes, generates a review from the persona's perspective
analyzing the user experience, friction points, and overall journey quality.
"""

import logging
from typing import Optional
from datetime import datetime

from ..core.models import Observation, ActionResult, DiagnosisResult
from ..core.persona import PersonaProfile
from .bedrock_client import BedrockClient

logger = logging.getLogger(__name__)


class PersonaReviewer:
    """Generates post-run reviews from the persona's perspective.

    Uses the AI agent to evaluate the test run as if the persona themselves
    were providing feedback on their experience.
    """

    def __init__(self, bedrock_client: Optional[BedrockClient] = None):
        """Initialize persona reviewer.

        Args:
            bedrock_client: Bedrock client instance (creates default if None)
        """
        self.client = bedrock_client or BedrockClient()

    def generate_review(
        self,
        persona: PersonaProfile,
        goal: str,
        observations: list[Observation],
        action_results: list[ActionResult],
        diagnosis: Optional[DiagnosisResult],
        outcome: str,
        duration_seconds: float,
    ) -> dict:
        """Generate persona review of the test run.

        Args:
            persona: Persona profile used for the run
            goal: User-defined goal
            observations: All observations from the run
            action_results: All action results from the run
            diagnosis: Diagnosis result (if failed)
            outcome: Final run outcome (success/failure/error)
            duration_seconds: Total run duration

        Returns:
            Dictionary containing persona review with fields:
            - timestamp: Review generation timestamp
            - persona_name: Name of the persona
            - overall_sentiment: positive/neutral/negative
            - experience_rating: 1-10 score
            - friction_points: List of identified friction points
            - positive_aspects: List of positive aspects
            - abandonment_likelihood: low/medium/high
            - narrative: Free-form narrative from persona perspective
            - recommendations: List of improvement recommendations
        """
        logger.info(f"Generating persona review from {persona.name}'s perspective")

        # Build review prompt
        system_prompt = self._build_system_prompt(persona)
        user_message = self._build_review_prompt(
            persona=persona,
            goal=goal,
            observations=observations,
            action_results=action_results,
            diagnosis=diagnosis,
            outcome=outcome,
            duration_seconds=duration_seconds,
        )

        try:
            # Get review from agent (with JSON response)
            response = self.client.invoke_with_json_response(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.8,  # Higher temperature for more natural review
                max_tokens=2048,
            )

            # Add metadata
            response["timestamp"] = datetime.utcnow().isoformat()
            response["persona_name"] = persona.name
            response["persona_display_name"] = persona.display_name

            logger.info(
                f"Persona review generated: {response.get('experience_rating', 'N/A')}/10, "
                f"sentiment: {response.get('overall_sentiment', 'N/A')}"
            )

            return response

        except Exception as e:
            logger.error(f"Failed to generate persona review: {e}", exc_info=True)
            # Return minimal fallback review
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "persona_name": persona.name,
                "persona_display_name": persona.display_name,
                "error": f"Failed to generate review: {str(e)}",
                "overall_sentiment": "unknown",
                "experience_rating": 0,
            }

    def _build_system_prompt(self, persona: PersonaProfile) -> str:
        """Build system prompt for persona review.

        Args:
            persona: Persona profile

        Returns:
            System prompt string
        """
        return f"""You are {persona.display_name}, a real user testing a signup flow.

Your personality and behavior:
{persona.description}

Your task is to review the signup journey you just experienced and provide honest, detailed feedback from your perspective as this persona.

Respond with a JSON object containing:
- overall_sentiment: "positive", "neutral", or "negative"
- experience_rating: number from 1-10 (1=terrible, 10=perfect)
- friction_points: array of strings describing specific issues you encountered
- positive_aspects: array of strings describing what worked well
- abandonment_likelihood: "low", "medium", or "high" - would you have given up?
- narrative: string with 2-3 paragraphs describing your experience in first person
- recommendations: array of strings with specific suggestions for improvement

Be honest, specific, and speak in character as {persona.display_name}. Reference specific moments from your journey."""

    def _build_review_prompt(
        self,
        persona: PersonaProfile,
        goal: str,
        observations: list[Observation],
        action_results: list[ActionResult],
        diagnosis: Optional[DiagnosisResult],
        outcome: str,
        duration_seconds: float,
    ) -> str:
        """Build review prompt with journey details.

        Args:
            persona: Persona profile
            goal: User-defined goal
            observations: All observations
            action_results: All action results
            diagnosis: Diagnosis result
            outcome: Final outcome
            duration_seconds: Run duration

        Returns:
            User message prompt
        """
        # Summarize journey
        total_steps = len(action_results)
        successful_actions = len([r for r in action_results if r.success])
        failed_actions = total_steps - successful_actions

        # Get starting and ending URLs
        start_url = observations[0].url if observations else "Unknown"
        end_url = observations[-1].url if observations else "Unknown"

        # Build journey summary
        journey_steps = []
        for i, (obs, result) in enumerate(zip(observations, action_results), 1):
            status = "✓" if result.success else "✗"
            journey_steps.append(
                f"Step {i}: {result.action} - {status} - {obs.url[:80]}"
            )

        journey_summary = "\n".join(journey_steps[:20])  # Limit to first 20 steps
        if len(journey_steps) > 20:
            journey_summary += f"\n... and {len(journey_steps) - 20} more steps"

        # Build diagnosis summary
        diagnosis_summary = "No issues diagnosed."
        if diagnosis:
            diagnosis_summary = f"""
Root Cause: {diagnosis.rootCause}
Severity: {diagnosis.severity}
Issue: {diagnosis.suggestedFix}
"""

        prompt = f"""Review your signup journey experience:

**Your Goal:** {goal}

**Journey Outcome:** {outcome.upper()}
**Duration:** {duration_seconds:.1f} seconds
**Total Steps:** {total_steps}
**Successful Actions:** {successful_actions}
**Failed Actions:** {failed_actions}

**Journey Path:**
Started at: {start_url}
Ended at: {end_url}

**Step-by-Step Journey:**
{journey_summary}

**Technical Diagnosis:**
{diagnosis_summary}

As {persona.display_name}, reflect on this experience:
- How did it feel to go through this signup process?
- What frustrated you or made you hesitate?
- What worked well and felt smooth?
- Would you have completed this in real life, or abandoned it?
- What specific changes would improve the experience for someone like you?

Provide your review in the specified JSON format, speaking authentically as {persona.display_name}."""

        return prompt


def create_persona_reviewer(config) -> PersonaReviewer:
    """Create persona reviewer instance from configuration.

    Args:
        config: SherlockConfig instance

    Returns:
        PersonaReviewer instance
    """
    from .bedrock_client import BedrockClient

    bedrock_client = BedrockClient(
        model_id=config.bedrock.model_id,
        region=config.bedrock.region,
        timeout_seconds=config.bedrock.timeout_seconds,
        max_retries=config.bedrock.max_retries,
    )

    return PersonaReviewer(bedrock_client=bedrock_client)
