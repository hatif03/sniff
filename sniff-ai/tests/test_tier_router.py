"""Unit tests for TierRouter - the Tier 2 (Jev) routing policy.

The core property under test: every role degrades to today's
deterministic/Tier-3-only behavior the moment Jev is disabled or errors, so
nothing changes for anyone without a Typesafe API key (the default).
"""

from unittest.mock import Mock

import pytest

from src.agent.jev_client import ChoiceResult, JevClient, JevInvocationError, ScoreResult
from src.agent.tier_router import TierRouter, create_tier_router
from src.core.config import SniffConfig, TypesafeConfig


@pytest.fixture
def mock_jev():
    return Mock(spec=JevClient)


# --- Role D: goal-reached (ReAct Observation interpreter) ---------------

def test_goal_reached_trusts_keyword_hit_without_calling_jev(mock_jev):
    router = TierRouter(jev_client=mock_jev, enabled=True)
    result = router.check_goal_reached(goal="Sign up", visible_text=["Welcome!"], keyword_hit=True)

    assert result.reached is True
    assert result.source == "keyword"
    mock_jev.noul.assert_not_called()


def test_goal_reached_disabled_falls_back_to_keyword_result(mock_jev):
    router = TierRouter(jev_client=mock_jev, enabled=False)
    result = router.check_goal_reached(goal="Sign up", visible_text=["Account created"], keyword_hit=False)

    assert result.reached is False
    assert result.source == "keyword_fallback"
    mock_jev.noul.assert_not_called()


def test_goal_reached_confident_jev_yes(mock_jev):
    mock_jev.noul.return_value = 0.92
    router = TierRouter(jev_client=mock_jev, enabled=True)
    result = router.check_goal_reached(goal="Sign up", visible_text=["Account created"], keyword_hit=False)

    assert result.reached is True
    assert result.source == "jev"


def test_goal_reached_low_confidence_falls_back(mock_jev):
    mock_jev.noul.return_value = 0.5
    router = TierRouter(jev_client=mock_jev, enabled=True)
    result = router.check_goal_reached(goal="Sign up", visible_text=["Loading..."], keyword_hit=False)

    assert result.reached is False
    assert result.source == "keyword_fallback"


def test_goal_reached_jev_error_falls_back(mock_jev):
    mock_jev.noul.side_effect = JevInvocationError("boom")
    router = TierRouter(jev_client=mock_jev, enabled=True)
    result = router.check_goal_reached(goal="Sign up", visible_text=["..."], keyword_hit=False)

    assert result.reached is False
    assert result.source == "keyword_fallback"


# --- Role B: context enrichment ------------------------------------------

def test_enrich_context_disabled_returns_none(mock_jev):
    router = TierRouter(jev_client=mock_jev, enabled=False)
    assert router.enrich_context(goal="Sign up", visible_text=["Email"]) is None
    mock_jev.system_one.assert_not_called()


def test_enrich_context_returns_signals_when_enabled(mock_jev):
    mock_jev.system_one.return_value = {
        "screen_type": ChoiceResult(choice="form", probabilities={}, confidence=0.8),
        "has_error": 0.1,
        "clutter": ScoreResult(score=2.0, legend=None, probabilities={}, confidence=0.7),
    }
    router = TierRouter(jev_client=mock_jev, enabled=True)

    signals = router.enrich_context(goal="Sign up", visible_text=["Email", "Password"])

    # One batched call (Speculative Fan-Out), not three separate requests.
    mock_jev.system_one.assert_called_once()
    assert signals == {
        "screen_type": "form",
        "screen_type_confidence": 0.8,
        "has_error": False,
        "clutter_score": 2.0,
    }


def test_enrich_context_returns_none_on_jev_error(mock_jev):
    mock_jev.system_one.side_effect = JevInvocationError("boom")
    router = TierRouter(jev_client=mock_jev, enabled=True)

    assert router.enrich_context(goal="Sign up", visible_text=["Email"]) is None


# --- Role C: decision critique --------------------------------------------

def test_critique_disabled_never_flags(mock_jev):
    router = TierRouter(jev_client=mock_jev, enabled=False)
    flagged = router.critique_decision(
        goal="Sign up", reasoning_summary="tapping button", action="tap", target="Sign Up", recent_history=None
    )
    assert flagged is False
    mock_jev.noul.assert_not_called()


def test_critique_flags_implausible_decision(mock_jev):
    mock_jev.noul.return_value = 0.1  # Jev thinks this is NOT plausible
    router = TierRouter(jev_client=mock_jev, enabled=True)

    flagged = router.critique_decision(
        goal="Sign up", reasoning_summary="tapping the same failed button again",
        action="tap", target="Sign Up", recent_history=[{"action": "tap", "target": "Sign Up"}],
    )
    assert flagged is True


def test_critique_accepts_plausible_decision(mock_jev):
    mock_jev.noul.return_value = 0.9
    router = TierRouter(jev_client=mock_jev, enabled=True)

    flagged = router.critique_decision(
        goal="Sign up", reasoning_summary="entering email", action="type", target="Email", recent_history=None
    )
    assert flagged is False


def test_critique_accepts_on_jev_error(mock_jev):
    mock_jev.noul.side_effect = JevInvocationError("boom")
    router = TierRouter(jev_client=mock_jev, enabled=True)

    flagged = router.critique_decision(
        goal="Sign up", reasoning_summary="entering email", action="type", target="Email", recent_history=None
    )
    assert flagged is False


# --- Factory ---------------------------------------------------------------

def test_create_tier_router_disabled_by_default():
    config = SniffConfig()
    router = create_tier_router(config)

    assert router.enabled is False
    assert router.jev is None


def test_create_tier_router_enabled_builds_client():
    config = SniffConfig(typesafe=TypesafeConfig(enabled=True, api_key="key", model_id="jev-1"))
    router = create_tier_router(config)

    assert router.enabled is True
    assert isinstance(router.jev, JevClient)
