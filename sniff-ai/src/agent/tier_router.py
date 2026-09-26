"""Tier routing policy for Sniff's three-tier decision architecture.

- Tier 1 (deterministic code): guardrail checks, keyword heuristics,
  DiagnosisClassifier/DiagnosisSignals, DecisionSanitizer. Unchanged by this
  module - already correct, no model involvement.
- Tier 2 (Jev, "System One"): this module. Jev is fast, text-only, and
  narrow, so it's used in three roles rather than as a drop-in replacement
  for the vision-based Tier 3 call:
    - goal-reached check: a ReAct-style "Observation" interpreter, backstop
      for the cheap keyword pre-filter (see check_goal_reached).
    - context enrichment: a parallel batch of cheap typed probes that
      pre-digest the screen for the expensive Tier 3 prompt, rather than
      making Tier 3 re-derive screen classification from scratch every step
      (see enrich_context; pattern: Speculative Fan-Out / Multi-Agent
      Parallel).
    - decision critique: a Generator-Critic gate that feeds into
      DecisionService's *existing* repair-retry mechanism instead of a new
      parallel retry path (see critique_decision).
- Tier 3 (Bedrock Claude): the existing vision-capable reasoning call,
  unchanged in shape, just given better inputs and one more sanity check.

Every method degrades to a documented Tier-1/Tier-3-only fallback the moment
Jev is disabled, unavailable, or errors, so the whole pipeline behaves
exactly as it did before this module existed whenever TypesafeConfig.enabled
is False (the default).

Not implemented here (see docs/product/ARCHITECTURE.md, "Phase 2"): a
Tiered Routing shortcut that skips the Tier 3 call entirely on obvious
steps. That requires Jev to name a concrete target element, which needs a
structured candidate-element list this codebase doesn't extract yet.
"""

import logging
from dataclasses import dataclass

from .jev_client import (
    ChoiceQuestion,
    ChoiceResult,
    JevClient,
    JevInvocationError,
    NoulQuestion,
    ScoreQuestion,
    ScoreResult,
)

logger = logging.getLogger(__name__)

# Below this, treat Jev's answer as inconclusive and defer to the
# deterministic fallback rather than trust a coin-flip-ish probability.
CONFIDENCE_THRESHOLD = 0.75


@dataclass
class GoalCheckResult:
    reached: bool
    source: str  # "keyword" | "jev" | "keyword_fallback"


class TierRouter:
    """Owns when Jev fires in the decision pipeline and what happens when it doesn't."""

    def __init__(self, jev_client: JevClient | None = None, enabled: bool = False):
        self.jev = jev_client
        self.enabled = enabled and jev_client is not None

    def check_goal_reached(self, goal: str, visible_text: list[str], keyword_hit: bool) -> GoalCheckResult:
        """ReAct Observation interpreter, backstop for the keyword pre-filter.

        A strong keyword match is trusted for free (no Jev call). Otherwise,
        if Jev is enabled, ask it directly; anything short of a confident
        "yes" falls back to the keyword result (today's behavior).
        """
        if keyword_hit:
            return GoalCheckResult(reached=True, source="keyword")

        if not self.enabled:
            return GoalCheckResult(reached=False, source="keyword_fallback")

        try:
            probability = self.jev.noul(
                question="Has the user's goal been achieved based on this page's visible content?",
                context=f"Goal: {goal}\nVisible text: {' | '.join(visible_text[:40])}",
            )
        except JevInvocationError as e:
            logger.warning(f"Jev goal-check unavailable, falling back to keyword result: {e}")
            return GoalCheckResult(reached=False, source="keyword_fallback")

        if probability >= CONFIDENCE_THRESHOLD:
            return GoalCheckResult(reached=True, source="jev")
        return GoalCheckResult(reached=False, source="keyword_fallback")

    def enrich_context(self, goal: str, visible_text: list[str]) -> dict | None:
        """Parallel context enrichment for the Tier 3 prompt.

        Fires one batch of cheap typed probes off visible text alone, ahead
        of the expensive vision call. Returns None (no annotation) when
        disabled or on any Jev error - the Tier 3 prompt is unaffected.
        """
        if not self.enabled:
            return None

        context = f"Goal: {goal}\nVisible text: {' | '.join(visible_text[:40])}"
        try:
            # One batched call (Typesafe's own "Speculative Fan-Out" pattern)
            # instead of three separate requests.
            answers = self.jev.system_one(
                context,
                screen_type=ChoiceQuestion(
                    instructions="What kind of screen is this?",
                    criteria={
                        "form": "a form asking the user to input information",
                        "error": "an error or blocking message is shown",
                        "loading": "a loading/transitional state, content not settled yet",
                        "confirmation": "a success/confirmation/completion state",
                        "other": "none of the above",
                    },
                ),
                has_error=NoulQuestion(instructions="Is there a visible error or blocking message on this screen?"),
                clutter=ScoreQuestion(
                    instructions="How cluttered or ambiguous is this screen for someone trying to act on it?",
                    criteria=["very simple, one obvious action", "somewhat busy", "cluttered", "very cluttered, unclear what to do"],
                ),
            )
        except JevInvocationError as e:
            logger.warning(f"Jev context enrichment unavailable, proceeding without it: {e}")
            return None

        screen_type: ChoiceResult = answers["screen_type"]
        has_error: float = answers["has_error"]
        clutter: ScoreResult = answers["clutter"]

        return {
            "screen_type": screen_type.choice,
            "screen_type_confidence": screen_type.confidence,
            "has_error": has_error >= CONFIDENCE_THRESHOLD,
            "clutter_score": clutter.score,
        }

    def critique_decision(
        self,
        goal: str,
        reasoning_summary: str,
        action: str,
        target: str | None,
        recent_history: list[dict] | None,
    ) -> bool:
        """Generator-Critic gate. Returns True if the decision should be
        routed through the existing repair path instead of executed as-is.
        """
        if not self.enabled:
            return False

        history_text = "; ".join(
            f"{h.get('action')} on {h.get('target')}" for h in (recent_history or [])[-5:]
        )
        context = (
            f"Goal: {goal}\nProposed action: {action} on {target}\n"
            f"Reasoning given: {reasoning_summary}\nRecent history: {history_text}"
        )
        try:
            plausible = self.jev.noul(
                question=(
                    "Does this proposed action plausibly make progress toward the goal, "
                    "given the reasoning and recent history?"
                ),
                context=context,
            )
        except JevInvocationError as e:
            logger.warning(f"Jev critic unavailable, accepting decision as-is: {e}")
            return False

        return plausible < (1 - CONFIDENCE_THRESHOLD)


def create_tier_router(config) -> TierRouter:
    """Build a TierRouter from SniffConfig.typesafe.

    Returns a disabled router (Jev never called) when typesafe.enabled is
    False - the default - so nothing changes for anyone without a key.
    """
    typesafe_config = getattr(config, "typesafe", None)
    if not typesafe_config or not typesafe_config.enabled:
        return TierRouter(jev_client=None, enabled=False)

    jev_client = JevClient(
        api_key=typesafe_config.api_key,
        base_url=typesafe_config.base_url,
        model_id=typesafe_config.model_id,
        timeout_seconds=typesafe_config.timeout_seconds,
    )
    return TierRouter(jev_client=jev_client, enabled=True)
