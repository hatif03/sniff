# Session 04: Typesafe AI Jev Client Setup

**Session Type:** Agent Mode
**Status:** ✅ Complete
**Date:** 2026-09-26

---

## Objectives

Integrate Typesafe AI's Jev model as Tier 2 of the decision architecture.

---

## What Actually Happened (real API, not the originally-planned design)

The original prompt assumed a generic `invoke_skill(skill_name, inputs) -> SkillResult` method backed by three skill-definition files under `src/agent/skills/`. That design was written before anyone had read Typesafe's actual docs. Once read (and once a real API key arrived), the real API turned out to be simpler and different:

- **One unified endpoint**, not per-skill files: `POST https://api.typesafe.ai/v1/systemone`, `Authorization: Bearer <key>`, body `{"state": <text>, "model": "jev-latest", "questions": {<name>: {"type": "choice"|"score"|"noul", "instructions": ..., "criteria": ...}}}` → `{"answers": {<name>: {...}}, "usage": {...}}`. It batches any mix of the three typed primitives (Choice/Score/Noul) against a shared context in one call.
- No `src/agent/skills/*.skill` files exist or are needed — the "skill" the docs refer to is a *coding-agent* plugin (teaches Claude Code how to call the API correctly), not a runtime artifact Sniff itself loads.
- **First implementation guessed wrong and had to be corrected.** A first pass (before a real key was available) implemented three separate endpoints (`/choice`, `/score`, `/noul`) based on incomplete public docs. A live smoke-test call with the real key returned `404`, which is what surfaced the real shape from `docs.typesafe.ai/api.md`. A second live call then hit a `400 Bad Request: "Unknown model: jev-1"` — the config default model ID (`jev-1`, a guess) was wrong too; the real default is `jev-latest`. Both were fixed and re-verified live (200 OK) before calling this done. Lesson worth keeping: for a model this new, "the docs say X" isn't the same as "a live call confirms X" — do the live call.

`src/agent/jev_client.py`: `JevClient.system_one(state, **questions)` is the real primitive; `choice()`/`score()`/`noul()` are single-question convenience wrappers over it for call sites that only need one probe. Errors: `JevInvocationError`/`JevTimeoutError` (mirrors the `BedrockClient`/`GeminiClient` error-pair pattern already established in this codebase, per the original prompt's instruction to match that pattern).

`TypesafeConfig` added to `SniffConfig` (`src/core/config.py`): `enabled: bool = False` (disabled by default — every caller degrades to today's behavior with zero config), `api_key`, `base_url`, `model_id: str = "jev-latest"`, `timeout_seconds`. Env vars: `TYPESAFE_ENABLED`, `TYPESAFE_API_KEY`, `TYPESAFE_BASE_URL`, `TYPESAFE_MODEL_ID`, `TYPESAFE_TIMEOUT_SECONDS` — no `SNIFF_JEV_CONFIDENCE_THRESHOLD` env var as the original prompt assumed; the confidence threshold is a code constant in `tier_router.py` (`CONFIDENCE_THRESHOLD = 0.75`), not runtime-configurable, since it's an implementation detail of the routing policy rather than something an operator should need to tune per environment.

Unit tests (`tests/test_jev_client.py`) mock the HTTP layer at the real `/systemone` shape; a real API key is used for a one-off live verification (not committed as an automated test — no network calls to a paid third-party API in CI).

---

## Why These Specific Decisions

**Batch over per-primitive calls**: the real API's `questions` map naturally batches Choice/Score/Noul together in one request — this is Typesafe's own "Speculative Fan-Out" pattern (their docs claim adding more questions barely changes latency), so `TierRouter.enrich_context()` (Session 05) sends its three probes as one call instead of three.

**Live verification over trusting docs alone**: search results for "Jev API" are heavily polluted with what looks like programmatic SEO content confidently repeating the same endpoint shape — the real `docs.typesafe.ai` domain and a real smoke-test call were what actually confirmed correctness, not agreement among search results.

---

## Verification

- Unit tests green against the real endpoint shape.
- Live call with the real API key: `curl` and the Python client both confirmed 200 OK with the documented response shape.

---

## Next Steps

→ Session 05: wire `JevClient` into the actual decision pipeline via `TierRouter`.
