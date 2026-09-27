"""k2-horizon (ifm.ai) client - the Tier 3 text-only reasoning model.

Used for GoalEnhancer/Planner/PersonaReviewer - none of these need vision,
so they're routed to k2-horizon instead of Gemini (cheaper/faster, and
frees Gemini's quota for the per-step navigation call that actually needs
the screenshot).

k2-horizon is OpenAI-compatible (confirmed via docs.ifm.ai): the official
docs literally say to reuse the `openai` package with a custom base_url,
so that's what this wraps rather than hand-rolling an HTTP client.
"""

import json
from typing import Any

from openai import APIError, APITimeoutError, OpenAI

from .json_response import parse_json_object
from .llm_errors import LLMInvocationError, LLMTimeoutError

# ifm.ai reasoning models require a `thinking` field on assistant turns when
# resuming multi-turn chat (docs.ifm.ai multi-turn guide — confirmed live:
# continuation without it returns HTTP 400).
_CONTINUATION_USER_PROMPT = (
    "Continue from where you left off and output ONLY the final JSON "
    "object now - no more reasoning, no markdown fences, nothing before or after it."
)

DEFAULT_BASE_URL = "https://api.ifm.ai/v1"
DEFAULT_MODEL_ID = "IFM/K2-Horizon-375B-A23B"


class K2HorizonClient:
    """k2-horizon client, same invoke()/invoke_with_json_response() shape as
    the old BedrockClient/GeminiClient - text-only, no image support."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        model_id: str = DEFAULT_MODEL_ID,
        timeout_seconds: int = 60,
    ):
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds
        self._client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout_seconds)

    def invoke(
        self,
        system_prompt: str,
        user_message: str | list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float | None = None,
    ) -> str:
        """Invoke k2-horizon with a prompt. Text-only - a vision content-block
        list will raise, since k2-horizon has no documented image input."""
        if not isinstance(user_message, str):
            raise LLMInvocationError(
                "K2HorizonClient is text-only; k2-horizon has no documented vision/image "
                "input support. Use GeminiClient for vision-dependent calls."
            )

        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if top_p is not None:
            kwargs["top_p"] = top_p

        content = self._complete_chat(**kwargs)
        return content

    def invoke_with_json_response(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Invoke k2-horizon and parse the response as JSON, using its
        native JSON mode (guarantees syntax, not structure - the prompt
        still needs to describe the desired fields).

        k2-horizon is a reasoning model: response_format=json_object doesn't
        stop it from spending the whole max_tokens budget on chain-of-thought
        before ever emitting the JSON object - confirmed live against real
        pages, where this failed the entire page audit. On that failure, one
        continuation call reuses the truncated reasoning as context and asks
        specifically for the final JSON, rather than discarding it and
        re-reasoning from scratch (cheaper and more likely to land)."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        content, thinking = self._complete(messages, max_tokens, temperature)
        try:
            return parse_json_object(content)
        except json.JSONDecodeError as e:
            continuation = messages + [
                self._assistant_message(content, thinking),
                {"role": "user", "content": _CONTINUATION_USER_PROMPT},
            ]
            retry_content, _ = self._complete(continuation, max_tokens, temperature)
            try:
                return parse_json_object(retry_content)
            except json.JSONDecodeError:
                raise LLMInvocationError(
                    f"k2-horizon response is not valid JSON, even after a continuation retry: {e}\n"
                    f"Response: {content}\nContinuation response: {retry_content}"
                ) from e

    def _complete_chat(self, **kwargs: Any) -> str:
        response = self._request_completion(**kwargs)
        content = response.choices[0].message.content
        if not content:
            raise LLMInvocationError("k2-horizon returned an empty response", details=response)
        return content

    def _complete(
        self, messages: list[dict], max_tokens: int, temperature: float
    ) -> tuple[str, str]:
        response = self._request_completion(
            model=self.model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        message = response.choices[0].message
        content = message.content or ""
        thinking_raw = getattr(message, "thinking", None)
        thinking = thinking_raw if isinstance(thinking_raw, str) else ""
        if not content and not thinking:
            raise LLMInvocationError("k2-horizon returned an empty response", details=response)
        return content, thinking

    def _request_completion(self, **kwargs: Any):
        """One automatic retry on transient network timeouts (session 17 gap)."""
        last_timeout: APITimeoutError | None = None
        for attempt in range(2):
            try:
                return self._client.chat.completions.create(**kwargs)
            except APITimeoutError as e:
                last_timeout = e
                if attempt == 0:
                    continue
                raise LLMTimeoutError(
                    f"k2-horizon request timed out after {self.timeout_seconds}s"
                ) from e
            except APIError as e:
                raise LLMInvocationError(f"k2-horizon invocation failed: {e}") from e
        raise LLMTimeoutError(
            f"k2-horizon request timed out after {self.timeout_seconds}s"
        ) from last_timeout

    @staticmethod
    def _assistant_message(content: str, thinking: str) -> dict[str, str]:
        return {
            "role": "assistant",
            "content": content,
            "thinking": thinking,
        }


def create_k2horizon_client(config) -> K2HorizonClient:
    """Create a K2HorizonClient from SniffConfig.k2horizon."""
    return K2HorizonClient(
        api_key=config.k2horizon.api_key,
        base_url=config.k2horizon.base_url,
        model_id=config.k2horizon.model_id,
        timeout_seconds=config.k2horizon.timeout_seconds,
    )
