"""Shared JSON parsing helpers for LLM clients.

Reasoning models can truncate mid-object, wrap JSON in fences, or prefix
chain-of-thought before the object — used by both k2-horizon and Gemini
invoke_with_json_response() paths.
"""

import json
from typing import Any


def strip_markdown_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:]
    return stripped.strip()


def extract_json_object(text: str) -> str | None:
    """Best-effort: find the outermost {...} span in a noisy response."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from model text, with fence stripping and substring fallback."""
    candidates = [text, strip_markdown_json_fence(text)]
    extracted = extract_json_object(candidates[-1])
    if extracted:
        candidates.append(extracted)

    last_error: json.JSONDecodeError | None = None
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as e:
            last_error = e
            continue
        if not isinstance(parsed, dict):
            raise json.JSONDecodeError("Expected a JSON object at the top level", candidate, 0)
        return parsed

    assert last_error is not None
    raise last_error
