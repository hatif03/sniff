# Session 05: Three-Tier Intelligence Architecture

**Session Type:** Agent Mode
**Status:** ✅ Complete
**Date:** 2026-09-26

---

## Objectives

Wire Jev into the decision pipeline as a real middle tier between deterministic code and the reasoning LLM.

---

## What Actually Happened (grounded in named patterns, not the original ad hoc design)

The original prompt sketched a `Tier` enum (`DETERMINISTIC`/`JEV`/`CLAUDE`) and a single `route(context) -> Tier` dispatch function inside a renamed `TieredDecisionService`. Two things changed once real research and a real API were in hand:

1. **There isn't much published literature on Jev specifically (it's new)**, so instead of inventing routing rules from scratch, the design was grounded in named patterns from two references reviewed live: the Google Developers Blog's "4 Engineering Patterns Behind the Strongest AI Agents Challenge Submissions" and Google Cloud's "Choose a design pattern for your agentic AI system" — plus Typesafe's own documented "Speculative Fan-Out" and "Confidence-Gated Routing" concepts. Important finding to not misattribute: **Typesafe's own docs don't claim a three-tier architecture** — they describe a two-way split (Jev vs. full reasoning LLMs). The three-tier framing (with code as its own tier) here is this project's synthesis, informed by the 2025-2026 model-cascade/routing literature (CASCADIA, RLCascadeRouter), not something to cite as Typesafe's idea.

2. **`DecisionService` was NOT renamed to `TieredDecisionService`.** Instead, `TierRouter` (`src/agent/tier_router.py`) is injected into the existing `DecisionService` as an optional constructor param (`tier_router: Optional[TierRouter] = None`) that's `None`/disabled by default. Smaller diff, same effect, and every existing caller/test that doesn't know about Jev keeps working unchanged.

Rather than one generic `route()` dispatcher, Jev is used in **three distinct roles**, each mapped to a real named pattern:

- **Role D — ReAct Observation interpreter**: `RunOrchestrator._is_goal_reached` used to be a dumb keyword search (`'success' in visible_text`) — a real false-negative bug on any success page that doesn't literally say "success"/"welcome". Keyword match still short-circuits for free; when weak/absent, `JevClient.noul()` decides; anything short of confident falls back to the keyword result unchanged.
- **Role B — parallel context enrichment** (Speculative Fan-Out / Multi-Agent Parallel): before the expensive Gemini call, one batched Jev call classifies screen type / error-visibility / clutter off `visibleText` alone, folded into the Gemini prompt as pre-digested context.
- **Role C — Generator-Critic gate**: after Gemini returns a decision, a cheap Jev `noul()` sanity-checks it; a low-confidence critique is routed through `DecisionService`'s *existing* repair-retry mechanism (same one used for schema-validation failures) rather than a new parallel retry system.

**Not implemented — deliberately deferred, not an oversight**: a *Tiered Routing* shortcut that would skip the Gemini call entirely on obvious steps (the Google blog's own pattern name, ~40% resolved pre-model in their reported case). This needs Jev to name a concrete target element, which needs a structured candidate-element list `Observation` doesn't expose yet (`visibleText` is just strings) — a real prerequisite (extending the Playwright worker's extraction), not a corner to cut silently. `TierRouter` is structured so this slots in later.

`DiagnosisClassifier` was **not** given a new `_classify_ambiguous_root_cause_jev()` method as the original prompt asked — investigating it found the class was *already* 100% deterministic rule trees with **zero LLM involvement**, despite its own docstring falsely claiming "hybrid... optional LLM interpretation." Fixed the docstring instead of adding a speculative new LLM branch to code that works fine as pure rules.

Per-tier call-count metrics on `RunReport` (`tier1_calls`/`tier2_calls`/`tier3_calls`) were **not added** in this pass — flagging as a real gap, not silently dropped: it's a reasonable follow-up once the tiers have run in production long enough to want the telemetry, but wasn't essential to prove the architecture works.

---

## Why These Specific Decisions

**Reuse the existing repair-retry loop for the critic gate** rather than build a second retry mechanism: smaller diff, one bounded-retry policy to reason about instead of two.

**Fix a false docstring instead of adding a speculative branch**: the classifier's actual behavior was already correct (Tier 1, deterministic); the bug was the documentation lying about it, not the code needing a new code path.

---

## Verification

- Unit tests (`tests/test_tier_router.py`) cover: every role degrades to today's exact behavior when Jev is disabled/unavailable/erroring; Role D's confident-vs-inconclusive branching; Role B's batched-call shape; Role C's critique-triggers-repair path.
- Live end-to-end test with real Gemini + real Jev credentials: `TierRouter.enrich_context()` correctly classified a signup form screen (confidence 1.0), and `check_goal_reached()` correctly recognized "Welcome aboard! Your account is ready" as goal-reached via Jev (`source="jev"`) where the old keyword-only check would have missed it.

---

## Next Steps

→ Session 11: architecture docs updated to describe this design (see that session's summary).
