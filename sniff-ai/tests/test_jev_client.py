"""Unit tests for the Jev (Typesafe AI) client.

Mocks the HTTP layer only - no real API key or network access needed.
Endpoint/shape verified live against the real API on 2026-09-26 (see
jev_client.py's module docstring) - these tests pin down that real shape.
"""

from unittest.mock import Mock, patch

import httpx
import pytest

from src.agent.jev_client import (
    ChoiceQuestion,
    ChoiceResult,
    JevClient,
    JevInvocationError,
    JevTimeoutError,
    NoulQuestion,
    ScoreQuestion,
    ScoreResult,
)


@pytest.fixture
def client():
    return JevClient(api_key="test-key", base_url="https://api.typesafe.ai/v1", model_id="jev-latest")


def _mock_response(json_data, status_code=200):
    response = Mock(spec=httpx.Response)
    response.json.return_value = json_data
    response.status_code = status_code
    response.raise_for_status = Mock()
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=Mock(), response=response
        )
    return response


def test_system_one_posts_to_real_endpoint(client):
    with patch.object(client._client, "post", return_value=_mock_response(
        {"model": "jev-1.13.0", "answers": {"is_urgent": {"type": "noul", "noul": 0.95}}, "usage": {}}
    )) as mock_post:
        client.system_one("some state", is_urgent=NoulQuestion(instructions="Is this urgent?"))

    args, kwargs = mock_post.call_args
    assert args[0] == "/systemone"
    assert kwargs["json"]["state"] == "some state"
    assert kwargs["json"]["questions"]["is_urgent"] == {"type": "noul", "instructions": "Is this urgent?"}


def test_system_one_batches_mixed_question_types(client):
    with patch.object(client._client, "post", return_value=_mock_response({
        "model": "jev-1.13.0",
        "answers": {
            "department": {
                "type": "choice", "choice": "billing",
                "probabilities": {"billing": 0.88, "technical": 0.12}, "confidence": 0.81,
            },
            "frustration": {
                "type": "score", "score": 1.05,
                "legend": {"0": "Calm", "1": "Frustrated"},
                "probabilities": {"0": 0.0, "1": 0.95}, "confidence": 0.92,
            },
            "is_urgent": {"type": "noul", "noul": 0.95},
        },
        "usage": {"input_tokens": 296, "output_tokens": 20},
    })):
        results = client.system_one(
            "customer message",
            department=ChoiceQuestion(instructions="Which team?", criteria={"billing": "...", "technical": "..."}),
            frustration=ScoreQuestion(instructions="How frustrated?", criteria=["Calm", "Frustrated"]),
            is_urgent=NoulQuestion(instructions="Urgent?"),
        )

    assert results["department"] == ChoiceResult(choice="billing", probabilities={"billing": 0.88, "technical": 0.12}, confidence=0.81)
    assert results["frustration"] == ScoreResult(score=1.05, legend={"0": "Calm", "1": "Frustrated"}, probabilities={"0": 0.0, "1": 0.95}, confidence=0.92)
    assert results["is_urgent"] == pytest.approx(0.95)


def test_choice_convenience_wrapper(client):
    with patch.object(client._client, "post", return_value=_mock_response(
        {"answers": {"_q": {"type": "choice", "choice": "form", "probabilities": {"form": 0.9}, "confidence": 0.9}}}
    )):
        result = client.choice("what kind of screen is this?", ["form", "error"], context="Goal: signup")

    assert isinstance(result, ChoiceResult)
    assert result.choice == "form"


def test_score_convenience_wrapper(client):
    with patch.object(client._client, "post", return_value=_mock_response(
        {"answers": {"_q": {"type": "score", "score": 3.0, "legend": None, "probabilities": {}, "confidence": 0.8}}}
    )):
        result = client.score("how cluttered is this screen?", rubric=["simple", "cluttered"])

    assert isinstance(result, ScoreResult)
    assert result.score == 3.0


def test_noul_convenience_wrapper(client):
    with patch.object(client._client, "post", return_value=_mock_response(
        {"answers": {"_q": {"type": "noul", "noul": 0.87}}}
    )):
        probability = client.noul("has the goal been achieved?", context="Goal: signup")

    assert probability == pytest.approx(0.87)


def test_timeout_raises_jev_timeout_error(client):
    with patch.object(client._client, "post", side_effect=httpx.TimeoutException("timed out")):
        with pytest.raises(JevTimeoutError):
            client.noul("question")


def test_http_error_raises_jev_invocation_error(client):
    with patch.object(client._client, "post", return_value=_mock_response({}, status_code=500)):
        with pytest.raises(JevInvocationError):
            client.noul("question")


def test_unexpected_response_shape_raises_jev_invocation_error(client):
    with patch.object(client._client, "post", return_value=_mock_response({"unexpected": True})):
        with pytest.raises(JevInvocationError):
            client.noul("question")


def test_missing_answer_for_question_raises_jev_invocation_error(client):
    with patch.object(client._client, "post", return_value=_mock_response({"answers": {}})):
        with pytest.raises(JevInvocationError):
            client.noul("question")
