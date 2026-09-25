"""Goal enhancer that creates detailed, context-aware execution plans.

Uses website context and persona to transform simple goals into detailed execution strategies.
"""

import logging
from typing import Optional
import json

from .website_analyzer import WebsiteContext
from ..core.persona import PersonaProfile

logger = logging.getLogger(__name__)


class GoalEnhancer:
    """Enhances user goals with website context and persona insights."""

    def __init__(self, bedrock_client):
        """Initialize goal enhancer.

        Args:
            bedrock_client: Bedrock client for LLM calls
        """
        self.bedrock_client = bedrock_client

    def enhance_goal(
        self,
        original_goal: str,
        website_context: WebsiteContext,
        persona: PersonaProfile,
    ) -> str:
        """Enhance a simple goal with website context and persona insights.

        Args:
            original_goal: User's simple goal (e.g., "Complete signup")
            website_context: Analyzed website context
            persona: Persona profile for behavior customization

        Returns:
            Enhanced goal with detailed execution strategy
        """
        logger.info(f"Enhancing goal: '{original_goal}' with website context")

        # Build enhancement prompt
        system_prompt, user_message = self._build_enhancement_prompt(
            original_goal, website_context, persona
        )

        try:
            # Call Bedrock to enhance the goal
            response = self.bedrock_client.invoke(
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=1500,
                temperature=0.3,  # Lower temperature for more focused output
            )

            enhanced_goal = response.strip()
            logger.info(f"Enhanced goal created ({len(enhanced_goal)} chars)")

            return enhanced_goal

        except Exception as e:
            logger.warning(f"Goal enhancement failed: {e}, using original goal")
            # Fallback to original goal if enhancement fails
            return self._create_fallback_enhanced_goal(
                original_goal, website_context, persona
            )

    def _build_enhancement_prompt(
        self,
        original_goal: str,
        website_context: WebsiteContext,
        persona: PersonaProfile,
    ) -> tuple[str, str]:
        """Build the LLM prompt for goal enhancement.

        Returns:
            Tuple of (system_prompt, user_message)
        """

        system_prompt = """You are a UX testing strategist helping to create detailed execution plans for testing websites.

Your task is to transform simple user goals into detailed, actionable execution plans that:
1. Break down the goal into specific, observable steps
2. Account for the actual website structure (buttons, forms, flows)
3. Adapt the approach to match the persona's behavioral profile
4. Identify potential paths and decision points
5. Define clear success criteria

Be specific about what to click/tap (use actual button/link text from the website context).
Consider persona traits (impatient users prefer fast paths, careful users validate everything).
Identify multiple paths if available (e.g., email signup vs. OAuth).
Note potential obstacles or friction points based on persona.
Keep the enhanced goal concise but actionable (aim for 8-15 steps).

Output ONLY the enhanced goal in this format:

ENHANCED GOAL: [One-line summary]

EXECUTION STRATEGY:
1. [Specific first step with actual button/element name]
2. [Next step...]

PERSONA-SPECIFIC NOTES:
- [Key behavior considerations]
- [Preferred paths or methods]

SUCCESS CRITERIA:
- [Observable condition 1]
- [Observable condition 2]

Do NOT include explanations or meta-commentary."""

        user_message = f"""**Original User Goal:**
{original_goal}

**Website Context (analyzed from initial page load):**
{website_context.to_context_string()}

**Persona Profile:**
Name: {persona.display_name}
Description: {persona.description}
Patience: {persona.patience_level:.1f}/1.0 (0=impatient, 1=patient)
Technical Proficiency: {persona.technical_proficiency:.1f}/1.0
Attention to Detail: {persona.attention_to_detail:.1f}/1.0

Behavioral Guidelines:
{chr(10).join('- ' + guideline for guideline in persona.behavioral_guidelines)}

Create the enhanced execution plan now."""

        return system_prompt, user_message

    def _create_fallback_enhanced_goal(
        self,
        original_goal: str,
        website_context: WebsiteContext,
        persona: PersonaProfile,
    ) -> str:
        """Create a basic enhanced goal without LLM (fallback)."""

        enhanced_parts = [
            f"ENHANCED GOAL: {original_goal}",
            "",
            "EXECUTION STRATEGY:",
        ]

        # Add basic strategy based on website context
        if website_context.signup_indicators:
            enhanced_parts.append(
                f"1. Look for signup options: {', '.join(website_context.signup_indicators[:3])}"
            )

        if website_context.detected_buttons:
            enhanced_parts.append(
                f"2. Click relevant buttons from: {', '.join(website_context.detected_buttons[:5])}"
            )

        if website_context.detected_form_fields:
            enhanced_parts.append(
                f"3. Fill form fields: {', '.join(website_context.detected_form_fields[:5])}"
            )

        enhanced_parts.append("4. Submit and verify completion")

        # Add persona notes
        enhanced_parts.extend([
            "",
            "PERSONA-SPECIFIC NOTES:",
            f"- Acting as: {persona.display_name}",
            f"- Patience level: {'Low' if persona.patience_level < 0.4 else 'High'}",
        ])

        # Add success criteria
        enhanced_parts.extend([
            "",
            "SUCCESS CRITERIA:",
            f"- {original_goal} is visibly completed",
            "- Reached confirmation or success page",
        ])

        return "\n".join(enhanced_parts)


def create_goal_enhancer(bedrock_client) -> GoalEnhancer:
    """Create goal enhancer instance.

    Args:
        bedrock_client: Bedrock client for LLM calls

    Returns:
        GoalEnhancer instance
    """
    return GoalEnhancer(bedrock_client)
