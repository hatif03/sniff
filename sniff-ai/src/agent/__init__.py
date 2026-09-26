"""Agent Service module for sniff.

Provides AI-driven decisioning across three tiers: deterministic code,
Jev (Tier 2, fast decisions), and Gemini/k2-horizon (Tier 3, reasoning).
Agent returns decisions only - never controls browser directly.
"""

from .gemini_client import GeminiClient
from .k2horizon_client import K2HorizonClient
from .decision_service import DecisionService

__all__ = ["GeminiClient", "K2HorizonClient", "DecisionService"]
