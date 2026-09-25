"""Planning agent for adaptive goal execution.

Provides next-action planning to improve decision quality and goal alignment.
"""

import logging
from typing import Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class GoalType(Enum):
    """Types of test goals."""
    EXPLORATORY = "exploratory"  # Observe, read, understand
    ACTION = "action"  # Complete tasks, fill forms, click buttons
    UNKNOWN = "unknown"


class Planner:
    """Planning agent that provides next-action recommendations."""

    # Keywords that indicate exploratory goals
    EXPLORATORY_KEYWORDS = [
        'explore', 'check', 'see', 'read', 'understand', 'learn',
        'view', 'browse', 'discover', 'find out', 'look at',
        'examine', 'review', 'observe', 'what', 'how'
    ]

    # Keywords that indicate action-oriented goals
    ACTION_KEYWORDS = [
        'signup', 'sign up', 'complete', 'create', 'upload', 'purchase',
        'buy', 'submit', 'fill', 'register', 'login', 'log in',
        'add', 'select', 'choose', 'enter', 'click'
    ]

    def __init__(self, bedrock_client):
        """Initialize planner.

        Args:
            bedrock_client: Bedrock client for LLM calls
        """
        self.bedrock_client = bedrock_client

    def detect_goal_type(self, goal: str) -> GoalType:
        """Detect whether goal is exploratory or action-oriented.

        Args:
            goal: User's test goal

        Returns:
            GoalType indicating the goal category
        """
        goal_lower = goal.lower()

        # Count keyword matches
        exploratory_matches = sum(
            1 for keyword in self.EXPLORATORY_KEYWORDS
            if keyword in goal_lower
        )

        action_matches = sum(
            1 for keyword in self.ACTION_KEYWORDS
            if keyword in goal_lower
        )

        # Classify based on keyword counts
        if exploratory_matches > action_matches:
            return GoalType.EXPLORATORY
        elif action_matches > exploratory_matches:
            return GoalType.ACTION
        else:
            # If tied or no matches, check for question words
            question_words = ['what', 'how', 'why', 'when', 'where', 'which']
            if any(word in goal_lower for word in question_words):
                return GoalType.EXPLORATORY
            return GoalType.UNKNOWN

    def get_next_action_plan(
        self,
        goal: str,
        goal_type: GoalType,
        current_observation: dict,
        action_history: List[dict],
    ) -> str:
        """Get a plan for the next action based on current state.

        Args:
            goal: The test goal
            goal_type: Type of goal (exploratory/action)
            current_observation: Current page observation
            action_history: List of previous actions taken

        Returns:
            Planning guidance as a string
        """
        # Build context summary
        current_url = current_observation.get('url', 'unknown')
        visible_text_sample = (
            ' '.join(current_observation.get('visibleText', [])[:50])
            if current_observation.get('visibleText')
            else 'No text available'
        )

        # Summarize recent actions
        recent_actions = []
        for action in action_history[-3:]:  # Last 3 actions
            action_type = action.get('action', 'unknown')
            target = action.get('target', '')
            recent_actions.append(f"{action_type} on '{target}'")

        action_summary = '; '.join(recent_actions) if recent_actions else 'No actions yet'

        # Build planning prompt based on goal type
        system_prompt = self._build_system_prompt(goal_type)
        user_message = f"""**Goal:** {goal}

**Current State:**
- URL: {current_url}
- Page content sample: {visible_text_sample[:300]}...

**Actions taken so far:** {action_summary}

**Question:** What should the agent do NEXT to progress toward the goal?

Provide a one-sentence action recommendation."""

        try:
            # Call Bedrock for planning
            response = self.bedrock_client.invoke(
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=200,
                temperature=0.3,
            )

            plan = response.strip()
            logger.debug(f"Generated next-action plan: {plan}")
            return plan

        except Exception as e:
            logger.warning(f"Planning failed: {e}, using fallback")
            return self._create_fallback_plan(goal_type, current_observation)

    def _build_system_prompt(self, goal_type: GoalType) -> str:
        """Build system prompt based on goal type."""

        base_prompt = """You are a testing strategy advisor helping an AI agent decide what to do next during a website test.

Your job is to provide a ONE-SENTENCE recommendation for the next action that will help achieve the test goal."""

        if goal_type == GoalType.EXPLORATORY:
            return base_prompt + """

**Goal Type: EXPLORATORY**

The user wants to observe and understand the website, NOT complete actions.

**Guidelines:**
- Prioritize scrolling to see more content
- Avoid clicking signup, login, or purchase buttons
- Focus on reading, observing, and gathering information
- Only click informational links (e.g., "Learn more", "About", "Features")
- If the agent has already clicked action buttons by mistake, recommend going back

**Example recommendations:**
- "Scroll down to see what products/services are offered"
- "Read the visible content to understand the value proposition"
- "Click the 'Learn more' link to get details (informational only)"
- "Go back to the homepage - we accidentally entered a signup flow"
"""
        elif goal_type == GoalType.ACTION:
            return base_prompt + """

**Goal Type: ACTION-ORIENTED**

The user wants to complete a specific task or flow on the website.

**Guidelines:**
- Focus on actionable elements (buttons, forms, links)
- Click buttons that advance toward the goal
- Fill forms when relevant
- Prioritize the most direct path to completion
- Avoid unnecessary exploration

**Example recommendations:**
- "Click the 'Sign up' button to start the registration flow"
- "Fill the email field with a test email address"
- "Click 'Next' to proceed to the next step"
- "Submit the form to complete the goal"
"""
        else:  # UNKNOWN
            return base_prompt + """

**Goal Type: UNCLEAR**

The goal could be exploratory or action-oriented - use context to decide.

**Guidelines:**
- Consider what actions have already been taken
- Look for signals in the page content
- Default to safer, exploratory actions if uncertain
- Avoid irreversible actions (purchases, deletions) until goal is clear
"""

    def _create_fallback_plan(self, goal_type: GoalType, observation: dict) -> str:
        """Create a basic fallback plan without LLM."""

        if goal_type == GoalType.EXPLORATORY:
            return "Scroll down to view more content and understand what the site offers"
        elif goal_type == GoalType.ACTION:
            return "Look for actionable buttons or forms relevant to the goal"
        else:
            return "Observe the current page and decide whether to explore or take action"


def create_planner(bedrock_client) -> Planner:
    """Create planner instance.

    Args:
        bedrock_client: Bedrock client for LLM calls

    Returns:
        Planner instance
    """
    return Planner(bedrock_client)
