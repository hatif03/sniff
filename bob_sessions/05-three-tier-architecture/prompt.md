# Session 05 Prompt: Three-Tier Intelligence Architecture

**Session Type:** Agent Mode  
**Status:** ⬜ Pending  
**Reference:** Sub-Task 4 in `sniff-expansion-plan.md` | [ADR-001](../../docs/adr/ADR-001-three-tier-architecture.md)

---

## Prompt (to be given when this session starts)

> Sub-Task 4 from `sniff-expansion-plan.md`:
>
> Wire up the three-tier decision routing using the JevClient from Session 04.
>
> 1. Create `sniff-ai/src/agent/tier_router.py`:
>    - `Tier` enum: `DETERMINISTIC`, `JEV`, `CLAUDE`
>    - `RoutingContext` dataclass: observation + step number + run state + recent action history
>    - `TierRouter` class with `route(context: RoutingContext) -> Tier` method
>    - Routing rules (document as constants):
>      * If current state is DIAGNOSE or generating narrative → CLAUDE
>      * If simple navigation (step N, sufficient context, action type is tap/type) → JEV
>      * If deterministic signal check (TTFB, HTTP status, step count) → DETERMINISTIC
>      * If Jev is disabled in config → CLAUDE
>    - Module docstring explaining the routing logic and cognitive science analogy
>
> 2. Update `sniff-ai/src/agent/decision_service.py` to `TieredDecisionService`:
>    - Instantiate `TierRouter`, `JevClient`, and existing `BedrockClient`
>    - `get_decision(observation, goal, persona, context)`:
>      * Call `TierRouter.route(context)` to pick tier
>      * Tier 1: return deterministic result from pure Python rules
>      * Tier 2: call `JevClient.invoke_skill("navigation_decision", ...)`
>        - If confidence < threshold: fall through to Tier 3
>        - If JevClient errors: fall through to Tier 3 (transparent fallback)
>      * Tier 3: call existing `BedrockClient.invoke()` (unchanged)
>    - Track tier used in reasoning timeline: `"tier": "JEV"` or `"CLAUDE"` etc.
>
> 3. Update `sniff-ai/src/diagnosis/classifier.py`:
>    - Signal extraction methods stay purely deterministic (no change)
>    - If LLM-driven narrative generation is present: confirm it goes to Tier 3 (Claude)
>    - Add `_classify_ambiguous_root_cause_jev()` method for Tier 2 root cause classification
>
> 4. Update `sniff-ai/src/core/orchestrator.py`:
>    - Instantiate `TieredDecisionService` instead of `DecisionService`
>    - Pass `SniffConfig.typesafe` to the service
>
> 5. Add per-tier metrics to `RunReport` in `sniff-ai/src/evidence/report_builder.py`:
>    - `tier1_calls: int`
>    - `tier2_calls: int`
>    - `tier3_calls: int`
>    - `tier2_cost_estimate: float` (Jev calls saved vs Claude equivalent)
>
> 6. Write unit tests for `TierRouter` and `TieredDecisionService`:
>    - Routing rules for each tier
>    - Jev fallback to Claude on low confidence
>    - Jev fallback to Claude on error
>    - Per-tier metric tracking
>
> Follow documentation discipline. Include module docstrings, class docstrings, inline comments.

---

## Pre-Session Checklist

Before starting this session, verify:
- [ ] Session 04 is complete (`JevClient` implemented, skill files created)
- [ ] `sniff-ai/src/agent/jev_client.py` exists and tests pass
- [ ] `sniff-ai/src/agent/skills/` directory has 3 skill files
