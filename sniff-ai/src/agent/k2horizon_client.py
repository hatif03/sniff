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

from .llm_errors import LLMInvocationError, LLMTimeoutError

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

        try:
            response = self._client.chat.completions.create(**kwargs)
        except APITimeoutError as e:
            raise LLMTimeoutError(f"k2-horizon request timed out after {self.timeout_seconds}s") from e
        except APIError as e:
            raise LLMInvocationError(f"k2-horizon invocation failed: {e}") from e

        content = response.choices[0].message.content
        if not content:
            raise LLMInvocationError("k2-horizon returned an empty response", details=response)
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
        content = self._complete(messages, max_tokens, temperature)
        try:
            return self._parse_json(content)
        except json.JSONDecodeError as e:
            continuation = messages + [
                {"role": "assistant", "content": content},
                {
                    "role": "user",
                    "content": "Continue from where you left off and output ONLY the final JSON "
                    "object now - no more reasoning, no markdown fences, nothing before or after it.",
                },
            ]
            retry_content = self._complete(continuation, max_tokens, temperature)
            try:
                return self._parse_json(retry_content)
            except json.JSONDecodeError:
                raise LLMInvocationError(
                    f"k2-horizon response is not valid JSON, even after a continuation retry: {e}\n"
                    f"Response: {content}\nContinuation response: {retry_content}"
                ) from e

    def _complete(self, messages: list[dict], max_tokens: int, temperature: float) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
        except APITimeoutError as e:
            raise LLMTimeoutError(f"k2-horizon request timed out after {self.timeout_seconds}s") from e
        except APIError as e:
            raise LLMInvocationError(f"k2-horizon invocation failed: {e}") from e

        content = response.choices[0].message.content
        if not content:
            raise LLMInvocationError("k2-horizon returned an empty response", details=response)
        return content

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        # response_format=json_object guarantees valid JSON syntax, but be
        # defensive about stray markdown fences anyway (cheap, harmless).
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)


def create_k2horizon_client(config) -> K2HorizonClient:
    """Create a K2HorizonClient from SniffConfig.k2horizon."""
    return K2HorizonClient(
        api_key=config.k2horizon.api_key,
        base_url=config.k2horizon.base_url,
        model_id=config.k2horizon.model_id,
        timeout_seconds=config.k2horizon.timeout_seconds,
    )
