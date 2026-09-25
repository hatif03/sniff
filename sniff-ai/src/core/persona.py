"""Persona system for Sherlock.

Defines user behavior profiles that shape agent exploration patterns:
- confused_first_time_user - explores more, hesitates, may misinterpret copy
- impatient_user - low tolerance for delays, early abandonment
- careful_user - reads labels thoroughly, validates before submit
"""

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PersonaProfile(BaseModel):
    """Behavioral profile for agent simulation.

    Personas shape how the agent interprets and navigates interfaces.
    """

    name: str = Field(..., description="Unique persona identifier (e.g., 'confused_first_time_user')")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Detailed persona description")

    # Behavioral parameters
    patience_level: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="0=very impatient, 1=very patient"
    )
    technical_proficiency: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="0=non-technical, 1=expert"
    )
    exploration_tendency: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="0=focused/direct, 1=exploratory/curious"
    )
    attention_to_detail: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="0=skims quickly, 1=reads everything"
    )

    # Optional goal template
    default_goal_template: Optional[str] = Field(
        default=None,
        description="Optional default goal template for this persona"
    )

    # Behavioral guidelines (used in agent prompts)
    behavioral_guidelines: list[str] = Field(
        default_factory=list,
        description="Specific behavioral instructions for this persona"
    )

    # Metadata
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")

    @classmethod
    def load(cls, name: str, personas_dir: Path = Path('./src/personas')) -> 'PersonaProfile':
        """Load persona from JSON file.

        Args:
            name: Persona name (without .json extension)
            personas_dir: Directory containing persona files

        Returns:
            PersonaProfile instance

        Raises:
            FileNotFoundError: If persona file doesn't exist
        """
        persona_path = personas_dir / f"{name}.json"
        if not persona_path.exists():
            raise FileNotFoundError(f"Persona '{name}' not found at {persona_path}")

        with open(persona_path, 'r') as f:
            data = json.load(f)
            return cls(**data)

    def save(self, personas_dir: Path = Path('./src/personas')) -> None:
        """Save persona to JSON file.

        Args:
            personas_dir: Directory to save persona file
        """
        personas_dir.mkdir(parents=True, exist_ok=True)
        persona_path = personas_dir / f"{self.name}.json"

        with open(persona_path, 'w') as f:
            json.dump(self.model_dump(), f, indent=2)

    @classmethod
    def list_available(cls, personas_dir: Path = Path('./src/personas')) -> list[str]:
        """List all available persona names.

        Args:
            personas_dir: Directory containing persona files

        Returns:
            List of persona names (without .json extension)
        """
        if not personas_dir.exists():
            return []

        return [
            p.stem for p in personas_dir.glob('*.json')
            if p.is_file()
        ]

    def to_prompt_context(self) -> str:
        """Convert persona to context string for agent prompts.

        Returns:
            Formatted string describing persona for LLM context
        """
        context_parts = [
            f"🎭 PERSONA: {self.display_name}",
            f"{self.description}",
            "",
            "📊 BEHAVIORAL PARAMETERS:",
            f"- Patience: {self._level_label(self.patience_level)} ({self.patience_level:.1f}/1.0)",
            f"- Technical Proficiency: {self._level_label(self.technical_proficiency)} ({self.technical_proficiency:.1f}/1.0)",
            f"- Exploration Tendency: {self._level_label(self.exploration_tendency)} ({self.exploration_tendency:.1f}/1.0)",
            f"- Attention to Detail: {self._level_label(self.attention_to_detail)} ({self.attention_to_detail:.1f}/1.0)",
        ]

        if self.behavioral_guidelines:
            context_parts.append("")
            context_parts.append("🎯 BEHAVIORAL GUIDELINES - Apply these behaviors to your decision-making:")
            for guideline in self.behavioral_guidelines:
                context_parts.append(f"  • {guideline}")

        # Add persona-specific decision modifiers
        context_parts.append("")
        context_parts.append("🧠 DECISION-MAKING IMPLICATIONS:")
        context_parts.extend(self._generate_decision_modifiers())

        return "\n".join(context_parts)

    def _generate_decision_modifiers(self) -> list[str]:
        """Generate decision-making guidance based on persona traits.

        Returns:
            List of decision modifier strings
        """
        modifiers = []

        # Patience-based modifiers
        if self.patience_level < 0.3:
            modifiers.append("  • Give up quickly if stuck (2-3 attempts max before aborting)")
            modifiers.append("  • Prefer obvious, immediate actions over complex exploration")
            modifiers.append("  • Low tolerance for slow page loads or unclear progress")
        elif self.patience_level > 0.7:
            modifiers.append("  • Persist through difficulties (5+ attempts before considering abort)")
            modifiers.append("  • Willing to explore and try multiple approaches")
            modifiers.append("  • Tolerant of delays and complex multi-step flows")

        # Technical proficiency modifiers
        if self.technical_proficiency < 0.3:
            modifiers.append("  • May misinterpret technical terms or unclear labels")
            modifiers.append("  • Prefer simple, obvious CTAs over complex UI patterns")
            modifiers.append("  • Easily confused by unexpected errors or validation messages")
        elif self.technical_proficiency > 0.7:
            modifiers.append("  • Comfortable with technical UI patterns and terminology")
            modifiers.append("  • Can navigate complex forms and multi-step processes")
            modifiers.append("  • Understand technical error messages and validation requirements")

        # Exploration modifiers
        if self.exploration_tendency < 0.3:
            modifiers.append("  • Focus on direct path to goal, minimal exploration")
            modifiers.append("  • Skip optional fields and secondary actions")
            modifiers.append("  • Prefer 'Next' buttons over exploring page content")
        elif self.exploration_tendency > 0.7:
            modifiers.append("  • Take time to explore page content and available options")
            modifiers.append("  • May investigate secondary paths before main goal")
            modifiers.append("  • Notice and interact with optional UI elements")

        # Attention to detail modifiers
        if self.attention_to_detail < 0.3:
            modifiers.append("  • Skim text quickly, may miss important details")
            modifiers.append("  • May overlook error messages or validation hints")
            modifiers.append("  • Focus on big, obvious elements (buttons) over fine print")
        elif self.attention_to_detail > 0.7:
            modifiers.append("  • Read all text, labels, and error messages carefully")
            modifiers.append("  • Notice validation requirements and formatting hints")
            modifiers.append("  • Pay attention to all visible UI elements and their states")

        return modifiers if modifiers else ["  • Balanced, moderate approach to navigation"]

    def to_llm_expanded_prompt(self, bedrock_client=None) -> str:
        """Generate LLM-expanded behavioral prompt using Bedrock.

        Uses an LLM to create a rich, detailed behavioral prompt based on persona traits.
        Falls back to to_prompt_context() if bedrock_client is not provided.

        Args:
            bedrock_client: Optional BedrockClient instance for LLM expansion

        Returns:
            Expanded persona prompt with detailed behavioral instructions
        """
        if not bedrock_client:
            logger.debug("No Bedrock client provided, using basic prompt context")
            return self.to_prompt_context()

        try:
            # Build expansion prompt
            expansion_prompt = f"""You are a behavioral psychology expert helping create detailed agent personas for UX testing.

Given this persona profile:
{self.to_prompt_context()}

Generate a rich, detailed behavioral prompt that an AI agent should follow to simulate this user's behavior during a signup flow test. The prompt should:

1. Translate personality traits into specific decision-making patterns
2. Explain how this persona would react to common UX situations:
   - Slow page loads
   - Unclear error messages
   - Complex multi-step forms
   - Optional vs required fields
   - Social login vs email signup options
3. Specify when this persona would likely abandon vs persist
4. Describe how they read and interpret UI text
5. Guide element selection preferences (big obvious buttons vs subtle links)

Format as a clear, actionable behavioral guide that directly influences agent decisions.
Keep it concise but comprehensive (200-300 words)."""

            # Call Bedrock for expansion
            response = bedrock_client.invoke(
                system_prompt="You are a behavioral psychology expert specializing in UX research personas.",
                user_message=expansion_prompt,
                max_tokens=1000
            )

            expanded_prompt = f"🎭 PERSONA: {self.display_name}\n\n{response}\n\n---\nOriginal Profile:\n{self.to_prompt_context()}"
            logger.info(f"Generated LLM-expanded persona prompt for {self.name}")
            return expanded_prompt

        except Exception as e:
            logger.warning(f"Failed to generate LLM-expanded persona: {e}. Falling back to basic context.")
            return self.to_prompt_context()

    @staticmethod
    def _level_label(value: float) -> str:
        """Convert 0-1 value to descriptive label."""
        if value < 0.3:
            return "Low"
        elif value < 0.7:
            return "Medium"
        else:
            return "High"


# Predefined persona templates
CONFUSED_FIRST_TIME_USER = PersonaProfile(
    name="confused_first_time_user",
    display_name="Confused First-Time User",
    description="A user who is new to online forms and easily confused by unclear instructions or technical jargon.",
    patience_level=0.4,
    technical_proficiency=0.2,
    exploration_tendency=0.7,
    attention_to_detail=0.6,
    behavioral_guidelines=[
        "Hesitate when instructions are unclear",
        "May misinterpret ambiguous copy or button labels",
        "Take time to explore and understand each field before filling it",
        "Likely to get stuck on unexpected errors or missing guidance",
        "May abandon if process seems too complex"
    ],
    tags=["beginner", "cautious", "exploratory"]
)

IMPATIENT_USER = PersonaProfile(
    name="impatient_user",
    display_name="Impatient User",
    description="A time-sensitive user with low tolerance for delays, unclear steps, or friction.",
    patience_level=0.1,
    technical_proficiency=0.6,
    exploration_tendency=0.2,
    attention_to_detail=0.3,
    behavioral_guidelines=[
        "Expect fast page loads and instant feedback",
        "Abandon quickly if progress is blocked or unclear",
        "Skim labels and instructions rather than reading carefully",
        "Prefer obvious, large buttons and clear next steps",
        "Sensitive to performance issues and loading times"
    ],
    tags=["advanced", "fast-paced", "goal-oriented"]
)

CAREFUL_USER = PersonaProfile(
    name="careful_user",
    display_name="Careful User",
    description="A methodical user who reads all instructions, validates inputs, and proceeds cautiously.",
    patience_level=0.9,
    technical_proficiency=0.5,
    exploration_tendency=0.5,
    attention_to_detail=0.9,
    behavioral_guidelines=[
        "Read all labels, help text, and error messages thoroughly",
        "Validate input before submitting each form",
        "Take time to understand requirements and constraints",
        "Notice small details like formatting requirements or optional fields",
        "Unlikely to abandon unless genuinely blocked"
    ],
    tags=["methodical", "detail-oriented", "patient"]
)


def create_default_personas(personas_dir: Path = Path('./src/personas')) -> None:
    """Create default persona files if they don't exist.

    Args:
        personas_dir: Directory to save persona files
    """
    default_personas = [
        CONFUSED_FIRST_TIME_USER,
        IMPATIENT_USER,
        CAREFUL_USER,
    ]

    personas_dir.mkdir(parents=True, exist_ok=True)

    for persona in default_personas:
        persona_path = personas_dir / f"{persona.name}.json"
        if not persona_path.exists():
            persona.save(personas_dir)
