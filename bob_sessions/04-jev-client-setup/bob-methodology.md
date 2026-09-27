# Session 04: Bob Methodology — Typesafe AI Jev Client Setup

## Bob Mode Used

**Agent Mode**

This session had a critical lesson embedded in it: **Bob's initial implementation was wrong, and it was only discovered by making a real live API call**. The session summary documents this honestly, and it is the single most important Bob methodology note for this session.

---

## Bob Tools and Techniques

### Reading Real Documentation (Not Assumed API Shape)
Before writing any code, Bob read the actual Typesafe AI documentation at `docs.typesafe.ai`. This reading revealed that the real API shape was different from what the original planning prompt assumed:
- The original prompt: three separate endpoints (`navigation_decision.skill`, `stuck_detector.skill`, `element_selector.skill`) loaded from files
- The real API: one unified endpoint `POST /v1/systemone` that batches any mix of typed primitives (Choice/Score/Noul) against shared context in one call

There are no `*.skill` runtime files. The "skill" in Typesafe's docs is a coding-agent plugin (teaches agents how to call the API), not a runtime artifact Sniff loads.

### Live API Call as Correctness Proof
Bob made a real live API call with the real API key before calling the implementation done. This was not optional — it was necessary.

Two bugs were only discovered via live calls:
1. **Wrong endpoint shape**: A first implementation based on incomplete public docs used three separate endpoints (`/choice`, `/score`, `/noul`). A live smoke-test returned `404`. The real shape (a single `/v1/systemone` endpoint with a `questions` map) was confirmed from `docs.typesafe.ai/api.md` directly.
2. **Wrong model ID**: The config default `jev-1` (a guess from before a real key existed) was rejected with `"Unknown model: jev-1"`. The real default is `jev-latest`. Fixed and re-verified live (200 OK).

This is the pattern: **for a model this new, "the docs say X" isn't the same as "a live call confirms X"**. Do the live call.

### Matching Existing Interface Patterns
Bob implemented `JevClient` to match the existing `BedrockClient`/`GeminiClient` error-pair pattern:
- `JevInvocationError` mirrors `BedrockInvocationError`/`GeminiInvocationError`
- `JevTimeoutError` mirrors the equivalent timeout error types

This was explicitly directed in the original prompt ("Auth via `TYPESAFE_API_KEY` env var. Timeout handling + error types matching the BedrockClient pattern"). Bob followed the existing interface rather than inventing a new one — this kept `DecisionService` changes minimal in Session 05.

### Deliberate Simplification of Config
The original prompt asked for `SNIFF_JEV_CONFIDENCE_THRESHOLD` as a runtime-configurable env var. Bob made it a code constant in `tier_router.py` instead (`CONFIDENCE_THRESHOLD = 0.75`), with reasoning: it is an implementation detail of the routing policy, not something an operator should tune per environment.

This is Bob applying the engineering discipline principle: **do not add configurability for things that do not need to be configurable**. The simpler approach (code constant) is correct here.

### Test-Driven Verification
Unit tests in `tests/test_jev_client.py` mock the HTTP layer at the real `/systemone` endpoint shape. The real API key was used for a one-off live verification (not committed as an automated test, because no paid third-party API calls should run in CI).

---

## Key Lesson: Live API Verification Over Trusting Documentation

Search results for "Jev API" were found to be heavily polluted with programmatic SEO content repeating the same (incorrect) endpoint shape. The real documentation at `docs.typesafe.ai` and a real smoke-test call were what actually confirmed correctness.

This lesson generalises: for any new or niche API (Jev, k2-horizon, new Gemini model IDs), the correct verification method is a real API call, not documentation alone.
