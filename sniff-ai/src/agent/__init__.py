"""Agent Service module for Sherlock.

Provides AI-driven decisioning using AWS Bedrock.
Agent returns decisions only - never controls browser directly.
"""

from .bedrock_client import BedrockClient
from .decision_service import DecisionService

__all__ = ["BedrockClient", "DecisionService"]
