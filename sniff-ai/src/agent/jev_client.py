"""Typesafe AI "Jev" client - the Tier 2 "System One" decision model.

Real API, verified live 2026-09-26 (docs.typesafe.ai/api.md, confirmed with
a live smoke-test call): one unified endpoint that batches any mix of typed
questions (choice/score/noul) against a shared `state` (context) in a
single request - this is Typesafe's own "Speculative Fan-Out" pattern.

    POST https://api.typesafe.ai/v1/systemone
    Authorization: Bearer <key>
    {
      "state": "<text/context to evaluate>",
      "model": "jev-latest",
      "questions": {
        "<name>": {"type": "noul"|"choice"|"score", "instructions": "...", "criteria": ...}
      }
    }
    ->
    {
      "model": "...", "usage": {...},
      "answers": {"<name>": {"type": "...", "noul"|"choice"|"score": ..., "probabilities": ..., "confidence": ...}}
    }

Jev takes text/structured input only (no images) and never generates free
text or holds a conversation - it is purely a typed batch decision call.
"""

import os
from dataclasses import dataclass, field

import httpx

DEFAULT_BASE_URL = "https://api.typesafe.ai/v1"
DEFAULT_MODEL_ID = "jev-latest"


@dataclass
class ChoiceQuestion:
    """Pick one option from a fixed set. `criteria` maps option -> description."""
    instructions: str
    criteria: dict[str, str]
    type: str = field(default="choice", init=False)


@dataclass
class ScoreQuestion:
    """Place the input on an ordered rubric. `criteria` is 2-10 ordered level labels."""
    instructions: str
    criteria: list[str]
    type: str = field(default="score", init=False)


@dataclass
class NoulQuestion:
    """A binary yes/no question. `criteria` (optional) describes what true/false mean."""
    instructions: str
    criteria: dict[str, str] | None = None
    type: str = field(default="noul", init=False)


JevQuestion = ChoiceQuestion | ScoreQuestion | NoulQuestion


@dataclass
class ChoiceResult:
    choice: str
    probabilities: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0


@dataclass
class ScoreResult:
    score: float
    legend: dict | None = None
    probabilities: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0


class JevClient:
    """Client for Typesafe AI's Jev System One model."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model_id: str | None = None,
        timeout_seconds: int = 5,
    ):
        self.api_key = api_key or os.getenv("TYPESAFE_API_KEY")
        self.base_url = (base_url or os.getenv("TYPESAFE_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        self.model_id = model_id or os.getenv("TYPESAFE_MODEL_ID", DEFAULT_MODEL_ID)
        self.timeout_seconds = timeout_seconds
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout_seconds,
            headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
        )

    def system_one(self, state: str, **questions: JevQuestion) -> dict[str, float | ChoiceResult | ScoreResult]:
        """Batch any mix of named Choice/Score/Noul questions in one call.

        Returns a dict keyed by question name: a float (noul), ChoiceResult,
        or ScoreResult depending on that question's type.
        """
        payload_questions = {}
        for name, q in questions.items():
            entry: dict = {"type": q.type, "instructions": q.instructions}
            if q.criteria is not None:
                entry["criteria"] = q.criteria
            payload_questions[name] = entry

        data = self._post({"state": state, "model": self.model_id, "questions": payload_questions})

        try:
            answers = data["answers"]
        except KeyError as e:
            raise JevInvocationError(f"Jev systemone returned an unexpected response shape: {e}") from e

        results: dict = {}
        for name, question in questions.items():
            try:
                answer = answers[name]
                if isinstance(question, NoulQuestion):
                    results[name] = float(answer["noul"])
                elif isinstance(question, ChoiceQuestion):
                    results[name] = ChoiceResult(
                        choice=answer["choice"],
                        probabilities=answer.get("probabilities", {}),
                        confidence=answer.get("confidence", 0.0),
                    )
                elif isinstance(question, ScoreQuestion):
                    results[name] = ScoreResult(
                        score=answer["score"],
                        legend=answer.get("legend"),
                        probabilities=answer.get("probabilities", {}),
                        confidence=answer.get("confidence", 0.0),
                    )
            except (KeyError, TypeError, ValueError) as e:
                raise JevInvocationError(f"Jev systemone answer '{name}' has an unexpected shape: {e}") from e

        return results

    # Single-question convenience wrappers - used where only one probe is needed.
    def choice(self, question: str, options: list[str], context: str = "") -> ChoiceResult:
        criteria = {opt: opt for opt in options}
        result = self.system_one(context, _q=ChoiceQuestion(instructions=question, criteria=criteria))
        return result["_q"]

    def score(self, question: str, rubric: dict[str, str] | list[str], context: str = "") -> ScoreResult:
        levels = list(rubric.values()) if isinstance(rubric, dict) else list(rubric)
        result = self.system_one(context, _q=ScoreQuestion(instructions=question, criteria=levels))
        return result["_q"]

    def noul(self, question: str, context: str = "") -> float:
        result = self.system_one(context, _q=NoulQuestion(instructions=question))
        return result["_q"]

    def _post(self, payload: dict) -> dict:
        try:
            response = self._client.post("/systemone", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as e:
            raise JevTimeoutError(f"Jev systemone request timed out after {self.timeout_seconds}s") from e
        except httpx.HTTPError as e:
            raise JevInvocationError(f"Jev systemone invocation failed: {e}") from e


class JevInvocationError(Exception):
    """Raised when a Jev call fails."""
    pass


class JevTimeoutError(JevInvocationError):
    """Raised when a Jev call times out."""
    pass
