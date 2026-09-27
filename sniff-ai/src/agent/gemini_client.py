"""Gemini (Vertex AI) client - the Tier 3 vision-capable reasoning model.

Replaces AWS Bedrock. Uses the google-genai SDK against Vertex AI with
Application Default Credentials (no API key needed - relies on
`gcloud auth application-default login` already having been run on this
machine, which it has).

Model/region note (verified live 2026-09-26 against the real project this
was built against): Gemini 3.x is the current generation per public docs,
but its newest tiers 404'd ("not found or your project does not have
access to it") on this project/region - not yet rolled out here, distinct
from the model not existing. Gemini 2.5 models ARE reachable today but are
on a retirement countdown (~Oct 20 2026 on Vertex AI). Given that, the
primary model is the current-gen ID (upgrades automatically once your
project gets access), with a *working-today* 2.5 model as the fallback -
see the automatic 404 retry in `_generate()`. Re-check
docs.cloud.google.com/vertex-ai/generative-ai/docs/models before the
retirement date if 3.x access still hasn't landed on your project.
`us-central1` is the safe default region; both region and model are
config-overridable rather than hardcoded.
"""

import base64
import json
from typing import Any

from google import genai
from google.genai import types

from .json_response import parse_json_object
from .llm_errors import LLMInvocationError, LLMTimeoutError

_GEMINI_JSON_CONTINUATION = (
    "Continue from where you left off and output ONLY the final JSON object now - "
    "no markdown fences, no commentary before or after it."
)

DEFAULT_LOCATION = "us-central1"
DEFAULT_MODEL_ID = "gemini-3.5-flash-lite"
DEFAULT_FALLBACK_MODEL_ID = "gemini-2.5-flash-lite"


class GeminiClient:
    """Vertex AI Gemini client for vision-capable agent decisions.

    Exposes the same invoke()/invoke_with_json_response() shape the old
    BedrockClient had, so DecisionService needs no interface changes -
    only which concrete client gets constructed.
    """

    def __init__(
        self,
        project_id: str | None = None,
        region: str = DEFAULT_LOCATION,
        model_id: str = DEFAULT_MODEL_ID,
        fallback_model_id: str = DEFAULT_FALLBACK_MODEL_ID,
        timeout_seconds: int = 60,
    ):
        if not project_id:
            raise RuntimeError(
                "GeminiClient requires a project_id (set GEMINI_PROJECT_ID or "
                "pass project_id explicitly)."
            )
        self.project_id = project_id
        self.region = region
        self.model_id = model_id
        self.fallback_model_id = fallback_model_id
        self.timeout_seconds = timeout_seconds

        try:
            self.client = genai.Client(vertexai=True, project=self.project_id, location=self.region)
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Vertex AI Gemini client: {e}\n"
                "Ensure `gcloud auth application-default login` has been run and "
                "the active gcloud project has the Vertex AI API enabled."
            ) from e

    def invoke(
        self,
        system_prompt: str,
        user_message: str | list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float | None = None,
    ) -> str:
        """Invoke Gemini with a prompt (text or text+image content blocks).

        `user_message` is either a plain string, or the same content-block
        list shape DecisionService already builds for vision calls:
        `[{"type": "image", "source": {"type": "base64", "media_type": ..., "data": ...}},
          {"type": "text", "text": ...}]`.
        """
        response = self._generate(system_prompt, user_message, max_tokens, temperature, top_p)
        if not response.text:
            raise LLMInvocationError("Gemini returned an empty response", details=response)
        return response.text

    def invoke_with_json_response(
        self,
        system_prompt: str,
        user_message: str | list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Invoke Gemini and parse the response as JSON.

        Uses Gemini's native JSON mode (response_mime_type) rather than
        hoping the model wraps output in markdown fences.
        """
        response = self._generate(
            system_prompt, user_message, max_tokens, temperature, top_p=None, json_mode=True
        )
        if not response.text:
            raise LLMInvocationError("Gemini returned an empty response", details=response)

        try:
            return parse_json_object(response.text)
        except json.JSONDecodeError as e:
            continuation = self._generate(
                system_prompt,
                user_message,
                max_tokens,
                temperature,
                top_p=None,
                json_mode=True,
                prior_model_text=response.text,
                continuation_user_text=_GEMINI_JSON_CONTINUATION,
            )
            if not continuation.text:
                raise LLMInvocationError(
                    f"Gemini response is not valid JSON: {e}\nResponse: {response.text}"
                ) from e
            try:
                return parse_json_object(continuation.text)
            except json.JSONDecodeError:
                raise LLMInvocationError(
                    f"Gemini response is not valid JSON, even after a continuation retry: {e}\n"
                    f"Response: {response.text}\nContinuation: {continuation.text}"
                ) from e

    def _generate(
        self,
        system_prompt: str,
        user_message: str | list[dict],
        max_tokens: int,
        temperature: float,
        top_p: float | None,
        json_mode: bool = False,
        prior_model_text: str | None = None,
        continuation_user_text: str | None = None,
    ):
        if prior_model_text is not None:
            follow_up = continuation_user_text or _GEMINI_JSON_CONTINUATION
            user_parts = self._build_parts(user_message)
            contents = [
                types.Content(role="user", parts=user_parts),
                types.Content(role="model", parts=[types.Part.from_text(text=prior_model_text)]),
                types.Content(role="user", parts=[types.Part.from_text(text=follow_up)]),
            ]
        else:
            contents = self._build_contents(user_message)
        config_kwargs = {
            "system_instruction": system_prompt,
            "max_output_tokens": max_tokens,
            "temperature": temperature,
        }
        if top_p is not None:
            config_kwargs["top_p"] = top_p
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"

        config = types.GenerateContentConfig(**config_kwargs)
        return self._generate_with_retries(contents, config)

    def _generate_with_retries(self, contents: list, config: types.GenerateContentConfig):
        def _call(model_id: str):
            for attempt in range(2):
                try:
                    return self.client.models.generate_content(
                        model=model_id, contents=contents, config=config,
                    )
                except Exception as e:
                    if self._is_timeout(e) and attempt == 0:
                        continue
                    if self._is_timeout(e):
                        raise LLMTimeoutError(
                            f"Gemini request timed out after {self.timeout_seconds}s"
                        ) from e
                    raise

        try:
            return _call(self.model_id)
        except Exception as e:
            if self._is_not_found(e) and self.model_id != self.fallback_model_id:
                try:
                    return _call(self.fallback_model_id)
                except Exception as fallback_error:
                    raise LLMInvocationError(
                        f"Gemini invocation failed for both {self.model_id} and "
                        f"fallback {self.fallback_model_id}: {fallback_error}"
                    ) from fallback_error
            if isinstance(e, LLMTimeoutError):
                raise
            raise LLMInvocationError(f"Gemini invocation failed: {e}") from e

    def _build_contents(self, user_message: str | list[dict]) -> list:
        """Convert the shared content-block shape into google-genai contents."""
        if isinstance(user_message, str):
            return [user_message]
        return [types.Content(role="user", parts=self._build_parts(user_message))]

    def _build_parts(self, user_message: str | list[dict]) -> list:
        if isinstance(user_message, str):
            return [types.Part.from_text(text=user_message)]

        parts = []
        for block in user_message:
            block_type = block.get("type")
            if block_type == "text":
                parts.append(types.Part.from_text(text=block["text"]))
            elif block_type == "image":
                source = block.get("source", {})
                image_bytes = base64.b64decode(source["data"])
                parts.append(
                    types.Part.from_bytes(data=image_bytes, mime_type=source.get("media_type", "image/jpeg"))
                )
            elif block_type == "image_url":
                # Tolerate the OpenAI-style data-URI shape too.
                url = block.get("image_url", {}).get("url", "")
                if url.startswith("data:"):
                    header, _, b64data = url.partition(",")
                    mime_type = header.removeprefix("data:").split(";")[0] or "image/jpeg"
                    parts.append(types.Part.from_bytes(data=base64.b64decode(b64data), mime_type=mime_type))
        return parts

    @staticmethod
    def _is_timeout(e: Exception) -> bool:
        message = str(e).lower()
        return "timeout" in message or "deadline" in message

    @staticmethod
    def _is_not_found(e: Exception) -> bool:
        message = str(e).lower()
        return "404" in message or "not_found" in message or "not found" in message
