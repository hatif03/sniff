"""Unit tests for K2HorizonClient (ifm.ai, Tier 3 text-only reasoning).

Mocks the underlying `openai` client - no real API key or network access
needed. Endpoint/shape confirmed live against docs.ifm.ai (OpenAI-compatible
/v1/chat/completions).
"""

from unittest.mock import MagicMock, patch

import pytest
from openai import APIError, APITimeoutError

from src.agent.k2horizon_client import K2HorizonClient
from src.agent.llm_errors import LLMInvocationError, LLMTimeoutError


@pytest.fixture
def client():
    with patch("src.agent.k2horizon_client.OpenAI"):
        return K2HorizonClient(api_key="test-key", model_id="IFM/K2-Horizon-375B-A23B")


def _mock_completion(content: str):
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    return response


def test_invoke_returns_text(client):
    client._client.chat.completions.create.return_value = _mock_completion("Hello!")

    result = client.invoke(system_prompt="You are helpful.", user_message="Hi")

    assert result == "Hello!"
    kwargs = client._client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "IFM/K2-Horizon-375B-A23B"
    assert kwargs["messages"][0] == {"role": "system", "content": "You are helpful."}
    assert kwargs["messages"][1] == {"role": "user", "content": "Hi"}


def test_invoke_rejects_vision_content(client):
    """k2-horizon has no documented image input - fail loudly, don't silently drop the image."""
    with pytest.raises(LLMInvocationError):
        client.invoke(system_prompt="sys", user_message=[{"type": "text", "text": "hi"}])


def test_invoke_with_json_response_parses_json(client):
    client._client.chat.completions.create.return_value = _mock_completion('{"action": "tap"}')

    result = client.invoke_with_json_response(system_prompt="Return JSON", user_message="Test")

    assert result == {"action": "tap"}
    kwargs = client._client.chat.completions.create.call_args.kwargs
    assert kwargs["response_format"] == {"type": "json_object"}


def test_invoke_with_json_response_strips_markdown_fence(client):
    client._client.chat.completions.create.return_value = _mock_completion('```json\n{"action": "tap"}\n```')

    result = client.invoke_with_json_response(system_prompt="Return JSON", user_message="Test")

    assert result == {"action": "tap"}


def test_invoke_with_json_response_retries_with_continuation_on_reasoning_overrun(client):
    """k2-horizon is a reasoning model that can burn its whole max_tokens
    budget on chain-of-thought before emitting any JSON - discovered live
    against real pages. The retry must reuse that reasoning as context
    (not discard it) rather than blindly resending the original prompt."""
    client._client.chat.completions.create.side_effect = [
        _mock_completion("We need to analyze this carefully first..."),
        _mock_completion('{"action": "tap"}'),
    ]

    result = client.invoke_with_json_response(system_prompt="Return JSON", user_message="Test")

    assert result == {"action": "tap"}
    calls = client._client.chat.completions.create.call_args_list
    assert len(calls) == 2
    retry_messages = calls[1].kwargs["messages"]
    assert retry_messages[0] == {"role": "system", "content": "Return JSON"}
    assert retry_messages[1] == {"role": "user", "content": "Test"}
    assert retry_messages[2] == {
        "role": "assistant",
        "content": "We need to analyze this carefully first...",
        "thinking": "",
    }
    assert "ONLY the final JSON" in retry_messages[3]["content"]


def test_invoke_with_json_response_raises_if_continuation_also_fails(client):
    client._client.chat.completions.create.side_effect = [
        _mock_completion("still thinking..."),
        _mock_completion("still not JSON"),
    ]

    with pytest.raises(LLMInvocationError):
        client.invoke_with_json_response(system_prompt="Return JSON", user_message="Test")

    assert client._client.chat.completions.create.call_count == 2


def test_timeout_raises_llm_timeout_error(client):
    client._client.chat.completions.create.side_effect = APITimeoutError(request=MagicMock())

    with pytest.raises(LLMTimeoutError):
        client.invoke(system_prompt="sys", user_message="hi")

    assert client._client.chat.completions.create.call_count == 2


def test_timeout_retries_once_then_succeeds(client):
    client._client.chat.completions.create.side_effect = [
        APITimeoutError(request=MagicMock()),
        _mock_completion("ok"),
    ]

    assert client.invoke(system_prompt="sys", user_message="hi") == "ok"
    assert client._client.chat.completions.create.call_count == 2


def test_api_error_raises_llm_invocation_error(client):
    client._client.chat.completions.create.side_effect = APIError(
        message="boom", request=MagicMock(), body=None
    )

    with pytest.raises(LLMInvocationError):
        client.invoke(system_prompt="sys", user_message="hi")
