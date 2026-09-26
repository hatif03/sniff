"""Shared error hierarchy for Tier 3 reasoning LLM clients (Gemini, k2-horizon).

Kept provider-agnostic so DecisionService/GoalEnhancer/Planner/PersonaReviewer
can catch one pair of exceptions regardless of which concrete client backs
them - see GeminiClient and K2HorizonClient.
"""


class LLMInvocationError(Exception):
    """Raised when an LLM client invocation fails."""

    def __init__(self, message: str, details=None):
        super().__init__(message)
        self.details = details


class LLMTimeoutError(LLMInvocationError):
    """Raised when an LLM client invocation times out."""
    pass
