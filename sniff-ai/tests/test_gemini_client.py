"""Unit tests for GeminiClient (Vertex AI, Tier 3 vision-capable reasoning).

Mocks the underlying `google.genai` client - no real ADC/project or network
access needed.
"""

import base64
from unittest.mock import MagicMock, patch

import pytest

from src.agent.gemini_client import GeminiClient
from src.agent.llm_errors import LLMInvocationError, LLMTimeoutError


@pytest.fixture
def client():
    with patch("src.agent.gemini_client.genai.Client") as mock_ctor:
        instance = GeminiClient(project_id="test-project", region="us-central1", model_id="gemini-3.5-flash-lite")
        instance.client = mock_ctor.return_value
        return instance


def _mock_response(text: str):
    response = MagicMock()
    response.text = text
    return response


def test_requires_project_id():
    with pytest.raises(RuntimeError):
        GeminiClient(project_id=None)


def test_invoke_text_only(client):
    client.client.models.generate_content.return_value = _mock_response("Hello!")

    result = client.invoke(system_prompt="You are helpful.", user_message="Hi")

    assert result == "Hello!"
    kwargs = client.client.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "gemini-3.5-flash-lite"
    assert kwargs["contents"] == ["Hi"]


def test_invoke_with_vision_content_blocks(client):
    client.client.models.generate_content.return_value = _mock_response("tap the button")
    image_b64 = base64.b64encode(b"fake-image-bytes").decode("utf-8")

    user_message = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
        {"type": "text", "text": "What should I click?"},
    ]

    result = client.invoke(system_prompt="Decide the next action.", user_message=user_message)

    assert result == "tap the button"
    contents = client.client.models.generate_content.call_args.kwargs["contents"]
    assert len(contents) == 2
    assert contents[1] == "What should I click?"


def test_invoke_with_json_response_uses_json_mime_type(client):
    client.client.models.generate_content.return_value = _mock_response('{"action": "tap"}')

    result = client.invoke_with_json_response(system_prompt="Return JSON", user_message="Test")

    assert result == {"action": "tap"}
    config = client.client.models.generate_content.call_args.kwargs["config"]
    assert config.response_mime_type == "application/json"


def test_invoke_with_json_response_invalid_json_raises(client):
    client.client.models.generate_content.return_value = _mock_response("not json")

    with pytest.raises(LLMInvocationError):
        client.invoke_with_json_response(system_prompt="Return JSON", user_message="Test")


def test_empty_response_raises_invocation_error(client):
    client.client.models.generate_content.return_value = _mock_response("")

    with pytest.raises(LLMInvocationError):
        client.invoke(system_prompt="sys", user_message="hi")


def test_falls_back_to_fallback_model_on_404(client):
    """Verified in practice: a model can 404 ('not found or your project
    does not have access to it') on a given project/region even though it's
    documented as current - retry once with the fallback before failing."""
    client.model_id = "gemini-3.5-flash-lite"
    client.fallback_model_id = "gemini-2.5-flash-lite"
    not_found = Exception("404 NOT_FOUND. Publisher model ... was not found or your project does not have access to it.")
    client.client.models.generate_content.side_effect = [not_found, _mock_response("OK")]

    result = client.invoke(system_prompt="sys", user_message="hi")

    assert result == "OK"
    calls = client.client.models.generate_content.call_args_list
    assert calls[0].kwargs["model"] == "gemini-3.5-flash-lite"
    assert calls[1].kwargs["model"] == "gemini-2.5-flash-lite"


def test_404_on_both_primary_and_fallback_raises(client):
    client.model_id = "gemini-3.5-flash-lite"
    client.fallback_model_id = "gemini-2.5-flash-lite"
    not_found = Exception("404 NOT_FOUND")
    client.client.models.generate_content.side_effect = [not_found, not_found]

    with pytest.raises(LLMInvocationError):
        client.invoke(system_prompt="sys", user_message="hi")


def test_timeout_error_raises_llm_timeout_error(client):
    client.client.models.generate_content.side_effect = Exception("Deadline exceeded")

    with pytest.raises(LLMTimeoutError):
        client.invoke(system_prompt="sys", user_message="hi")


def test_other_error_raises_llm_invocation_error(client):
    client.client.models.generate_content.side_effect = Exception("something else broke")

    with pytest.raises(LLMInvocationError):
        client.invoke(system_prompt="sys", user_message="hi")
