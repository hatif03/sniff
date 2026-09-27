# The Agent Cognition Spectrum

## A Framework for AI Agent Architecture

**Documented:** Session 05 (architecture), Session 12 (provider materialisation)  
**Status:** In production — Sniff's live decision pipeline

---

## The Core Idea

Traditional software engineering makes a binary choice: write code, or call an LLM. Agent systems built this way pay the full cost of a reasoning model for decisions that don't need it, and fall back to rigid rule trees for decisions that actually do need judgment.

The insight this architecture is built on is that decisions exist on a **spectrum**, not a binary:

```
Deterministic Code ──────── System One (Jev) ──────── System Two (Gemini)
     Fast, free,                Fast, typed,              Slow, expensive,
     zero ambiguity             structured judgment        open-ended reasoning
```

At the left end: everything that can be expressed as a rule tree — HTTP status codes, keyword presence, element-not-found counters. Zero model involvement. At the right end: everything that requires open-ended multi-modal reasoning — interpreting a screenshot of an unfamiliar UI, generating narrative, synthesising a root cause. In between: a class of decisions that are *judgment calls*, but narrow, typed, and fast. Not yes/no based on a rule, but not complex enough to warrant a full reasoning model either. This middle tier is what Jev (Typesafe AI's System One model) fills.

---

## The Three Tiers in Sniff

| Tier | Technology | Decision Type | Cost Profile |
|---|---|---|---|
| **1 — Deterministic** | Pure Python | Rule trees, signal extraction, guardrail checks | Free, sub-millisecond |
| **2 — System One (Jev)** | Typesafe AI `jev-latest` | Fast typed probes: noul/choice/score in a single batched call | ~5–50ms, fraction of T3 cost |
| **3 — System Two (Reasoning)** | Gemini (vision) + k2-horizon (text) | Open-ended multi-modal reasoning, narrative, scoring | 1–5s, primary cost driver |

### Tier 1 — Deterministic Code

Files: [`sniff-ai/src/diagnosis/classifier.py`](../sniff-ai/src/diagnosis/classifier.py), [`sniff-ai/src/core/state_machine.py`](../sniff-ai/src/core/state_machine.py), [`sniff-ai/src/evidence/audit_checks.py`](../sniff-ai/src/evidence/audit_checks.py)

The deterministic tier handles everything where the answer is derivable from observable signals without judgment:

- `DiagnosisSignals` — extracts HTTP error presence, console errors, timeout patterns, element-not-found counters from raw run data. No model call.
- `DiagnosisClassifier` — rule trees over `DiagnosisSignals`: maps signal combinations to root cause categories (`Backend`, `Performance`, `UX/Content`, `Integration`) and severity (`P0`–`P3`). 100% deterministic, despite an earlier docstring falsely claiming "hybrid with optional LLM interpretation" — corrected in Session 05 when investigation found zero LLM involvement in the actual code.
- `DecisionSanitizer` and keyword guardrails — deterministic pre-filter on the goal-reached check: if the success keyword is present, we're done. No model call needed.
- State machine transitions, step counting, stuck detection — all pure logic.

The key discipline for this tier: **if the decision can be expressed as a rule tree, it belongs here**. The temptation to reach for an LLM on Tier-1 decisions is real (it "feels smarter") but it adds latency and cost for zero benefit. The classifier's actual behavior was already correct; the bug was the documentation claiming it was something it wasn't.

### Tier 2 — System One (Jev)

Files: [`sniff-ai/src/agent/jev_client.py`](../sniff-ai/src/agent/jev_client.py), [`sniff-ai/src/agent/tier_router.py`](../sniff-ai/src/agent/tier_router.py)

Jev is Typesafe AI's System One model. It is not a conversational LLM. It never generates free text. It takes a `state` (text context) and a batch of named typed questions, and returns typed answers:

- **`noul`** — a binary probability (0.0–1.0). "Has the user's goal been achieved?" → `0.89`
- **`choice`** — picks one from a fixed set with confidence. "What kind of screen is this?" → `{"choice": "form", "confidence": 0.97}`
- **`score`** — places input on an ordered rubric. "How cluttered is this screen?" → `{"score": 2.1}`

Multiple questions are batched into **one HTTP call** against `/v1/systemone` — Typesafe calls this the "Speculative Fan-Out" pattern. This is critical: enriching the Tier 3 context with three questions costs one network round-trip, not three.

Jev fires in exactly three roles in Sniff's pipeline, each mapped to a named pattern:

**Role 1: ReAct Observation Interpreter** (`TierRouter.check_goal_reached`)  
The old goal-reached check was a keyword search (`'success' in visible_text`) — a real false-negative bug on any success page that doesn't literally say "success" or "welcome". The new flow: keyword match short-circuits for free (if "success" is present, done). On a weak/absent keyword match, Jev evaluates whether the goal was achieved from visible text. Anything below 0.75 confidence falls back to the keyword result — today's existing behavior. Pattern: ReAct's Observation interpreter.

**Role 2: Context Enrichment** (`TierRouter.enrich_context`)  
Before the expensive Tier 3 Gemini call, one batched Jev call classifies screen type, error visibility, and clutter off `visibleText` alone. These pre-computed signals are folded into the Gemini prompt — the reasoning model gets a pre-digested screen classification instead of re-deriving it from scratch every step. Pattern: Speculative Fan-Out / Multi-Agent Parallel.

**Role 3: Generator-Critic Gate** (`TierRouter.critique_decision`)  
After Gemini returns a decision, a cheap Jev `noul()` sanity-checks whether the proposed action plausibly makes progress toward the goal. A low-confidence critique (< 0.25) routes through `DecisionService`'s *existing* repair-retry mechanism — the same bounded-retry path used for malformed JSON output — rather than a new parallel retry system. Pattern: Generator-Critic.

Critical degradation guarantee: **every role degrades gracefully to Tier-1/Tier-3-only behavior the moment Jev is disabled, unavailable, or errors**. `TierRouter(enabled=False)` is the default. The whole pipeline behaves exactly as it did before Jev existed for any caller without a Typesafe key.

### Tier 3 — System Two (Reasoning)

Files: [`sniff-ai/src/agent/gemini_client.py`](../sniff-ai/src/agent/gemini_client.py), [`sniff-ai/src/agent/k2horizon_client.py`](../sniff-ai/src/agent/k2horizon_client.py), [`sniff-ai/src/agent/decision_service.py`](../sniff-ai/src/agent/decision_service.py)

Tier 3 is reserved for decisions that genuinely require open-ended reasoning. It is not called until Tier 1 and Tier 2 have done everything they can.

The key implementation finding (Session 12): **Tier 3 is itself split by capability**, not just by cost:

- **Gemini** (Vertex AI, `gemini-3.5-flash-lite` / fallback `gemini-2.5-flash-lite`) — vision-capable. Used for every decision that requires interpreting a screenshot: per-step navigation decisions, audit scoring, page analysis. Gemini's built-in JSON mode (`response_mime_type: application/json`) is used instead of relying on markdown fence parsing.
- **k2-horizon** (ifm.ai, `IFM/K2-Horizon-375B-A23B`, OpenAI-compatible API) — text-only. Used for `GoalEnhancer`, `Planner`, `PersonaReviewer`, copy rewrites, SEO findings, fix list generation. Cheaper and faster when vision is not needed.

Both clients expose the same `invoke()` / `invoke_with_json_response()` interface as the original `BedrockClient` they replaced. `DecisionService` required no interface changes — only which concrete client is injected changes.

---

## How Instructions Are Split Across the Spectrum

Before this architecture, agent instructions (system prompts, skill files) came in two pieces: a *static system prompt* baked into the Tier-3 call, and *dynamic context* assembled at runtime. That two-way split mapped to: "what the agent always knows" vs. "what it knows about this step."

The three-tier architecture splits instructions into three pieces:

| Layer | Where it lives | What it encodes |
|---|---|---|
| **Deterministic** | Python rules and constants | Facts that are always true and derivable without judgment: HTTP 5xx = backend error, TTFB > 5000ms = performance issue, keyword "success" = goal reached. These never need to be in a prompt. |
| **Decision** (Jev) | Structured question definitions in `tier_router.py` | Judgment calls that are typed and narrow: "what kind of screen is this?" is a choice over four options, not a free-text question. The *criteria* for each question are the instructions; Jev returns a typed answer, not prose. |
| **Reasoning** (Gemini) | `decision_prompts.py` system/user prompt templates | Instructions that require open-ended interpretation: semantic matching rules, phase-recognition logic, anti-pattern examples, persona behavior profiles. Everything that's too nuanced for a rule tree and too complex for a typed probe. |

The practical consequence: the Gemini system prompt in [`decision_prompts.py`](../sniff-ai/src/agent/prompts/decision_prompts.py) no longer needs to explain "what kind of screen is this" — Jev pre-answered that as a typed signal that's already in the prompt context by the time Gemini reads it. The reasoning model's instructions can be narrower, because the decisions those instructions would have handled have already been delegated to the appropriate tier.

---

## The Routing Mechanism

The pipeline per navigation step:

```
Observation (screenshot + visible text + URL + history)
    │
    ▼
[Tier 1] Keyword pre-filter
    ├─ keyword hit → GoalCheckResult(reached=True, source="keyword")  [done, no model call]
    └─ no keyword hit ──→
                        │
                        ▼
              [Tier 2] Jev: noul("Has the goal been achieved?")
                  ├─ confidence ≥ 0.75 → GoalCheckResult(reached=True, source="jev")
                  └─ confidence < 0.75 → GoalCheckResult(reached=False, source="keyword_fallback")
    │
    ▼
[Tier 2] Jev: system_one(screen_type + has_error + clutter)  ← one batched call
    │         returns jev_signals dict
    ▼
[Tier 3] Gemini: DecisionService._attempt_decision(screenshot, jev_signals injected into prompt)
    │         returns AgentDecision
    ▼
[Tier 2] Jev: noul("Does this proposed action plausibly make progress toward the goal?")
    ├─ plausible ≥ 0.25 → execute decision
    └─ implausible < 0.25 → route through DecisionService repair-retry loop
```

The confidence threshold is `0.75` throughout. Below it, Jev's answer is treated as inconclusive and the system falls back to the adjacent tier's behavior — never trusting a coin-flip probability.

---

## Why This Architecture Matters Beyond Sniff

The three-tier framing maps to a broader principle in agentic system design that was emerging in 2025–2026:

**Not all decisions need the same reasoning depth.** The cascade literature (CASCADIA, RLCascadeRouter) frames this as routing to the *minimum-cost model that can answer correctly*. The spectrum framing is the same insight, but with an important extension: the leftmost point on the spectrum isn't a cheap LLM — it's **no model at all**. Pure code is always the right answer for decisions that have no ambiguity.

**System One vs. System Two is not just about speed.** Jev's typed question API (`noul`/`choice`/`score`) forces you to decide, at design time, exactly what you're asking and what the valid answer space is. This is a fundamentally different cognitive mode than prompting a reasoning model. It's closer to designing a structured data schema than writing a prompt. The instruction authoring splits accordingly: you write *criteria* for Jev, you write *prompts* for Gemini.

**The middle tier is not a shortcut to the reasoning tier.** Jev cannot navigate a complex UI. Jev cannot generate a root-cause narrative. Jev cannot look at a screenshot. Its value is not that it approximates Gemini cheaply — it's that for a specific class of *typed, narrow judgment calls*, it produces better-specified, more reliable answers than asking a reasoning model to reason about something it could answer in one word.

---

## Implementation Notes

- **Jev API shape** (verified live, 2026-09-26): one unified endpoint `POST /v1/systemone`, `Authorization: Bearer`, body `{"state": "<context>", "model": "jev-latest", "questions": {...}}`. No separate endpoints per question type. No "skill files" at the API level — that concept exists only in Typesafe's documentation metaphor, not the wire protocol.
- **Jev model ID**: the config default `jev-1` was rejected by the live API with `"Unknown model: jev-1"`. Real default: `jev-latest`. Found via live testing, not docs.
- **Gemini model access**: `gemini-3.5-flash-lite` is current per Google's docs but 404'd on the actual GCP project at the time of implementation. `GeminiClient` retries once against `gemini-2.5-flash-lite` on 404. Both model IDs are config-overridable.
- **The three-tier framing is this project's synthesis**, not something attributable to Typesafe. Typesafe's own docs describe a two-way split (Jev vs. full reasoning LLMs). The three-tier model — with pure code as its own explicit first tier — was synthesised from the Google Developers Blog's "4 Engineering Patterns Behind the Strongest AI Agents Challenge Submissions" and Google Cloud's "Choose a design pattern for your agentic AI system", plus Typesafe's Speculative Fan-Out and Confidence-Gated Routing concepts.

---

## Deferred Work

**Tiered Routing shortcut (Phase 2)**: a path that skips the Tier 3 Gemini call entirely on obvious steps (~40% of steps in Google's reported case for their own pipeline). This requires Jev to name a concrete target element, which needs a structured candidate-element list that `Observation.visibleText` (currently plain strings) doesn't expose. `TierRouter` is structured so this slots in — see the docstring in [`tier_router.py`](../sniff-ai/src/agent/tier_router.py). The prerequisite is extending `PlaywrightWorker` to extract a typed element list from the DOM, not a corner to cut silently.

**Per-tier call-count telemetry**: `tier1_calls` / `tier2_calls` / `tier3_calls` on `RunReport`. Not added in Session 05 — the right time for this is once the tiers have run in production long enough to want aggregate cost data.
