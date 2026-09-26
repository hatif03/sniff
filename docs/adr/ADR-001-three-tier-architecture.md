# ADR-001: Three-Tier Intelligence Architecture

## Status
Accepted

## Date
2025-01-01

## Context

*(Note: at the time this ADR was written, Sniff's Tier 3 reasoning model was AWS Bedrock Claude. It has since been replaced with Gemini via Vertex AI + k2-horizon via ifm.ai - see `ARCHITECTURE.md` Section 8 and `STRANDS_BEDROCK_REPORT.md`. The tiering decision and rationale below are unaffected by that swap; only the Tier 3 provider name changed.)*

Sniff's architecture at the time routed every navigation decision to AWS Bedrock Claude — a powerful reasoning model (System Two thinking). This creates three problems:

1. **Cost**: Each Playwright step triggers a Tier 3 model invocation. For a 50-step run, that is 50 full LLM calls. At Claude Sonnet pricing (the model in use at the time), this makes continuous/scheduled runs expensive.
2. **Latency**: Claude invocations add 2–5 seconds per step. A 50-step run takes 100–250 seconds just in model latency, independent of browser time.
3. **Overkill**: Most navigation decisions ("tap the Sign Up button", "type email in the email field") do not require deep reasoning — they require fast, accurate pattern matching. Sending them to a System Two model is like using a chainsaw to butter toast.

The competitive landscape (ColdVisit, Mabl, Testim) uses cheaper, faster specialized models for routine decisions and reserves expensive models for analysis and reporting.

## Decision

Restructure the decision pipeline into three explicit tiers:

| Tier | Name | Technology | When Invoked |
|---|---|---|---|
| 1 | **Deterministic** | Pure Python rules/code | Signal extraction, guardrail checks, state machine transitions, HTTP error detection |
| 2 | **System One (Jev)** | Typesafe AI Jev | Routine navigation decisions: which element to tap, which field to fill, stuck detection |
| 3 | **System Two (Gemini/k2-horizon)** | Gemini (Vertex AI) + k2-horizon (ifm.ai) - originally AWS Bedrock Claude | Root cause diagnosis, persona review narratives, ambiguous high-stakes decisions |

A `TierRouter` class decides which tier to invoke based on decision context:
- If the required operation maps to a deterministic rule → Tier 1 (no model call)
- If the required operation is a navigation step with sufficient context → Tier 2 (Jev)
- If the required operation requires deep reasoning or the Jev confidence is below threshold → Tier 3 (Gemini/k2-horizon)
- If Jev is unavailable or errors → fall back to Tier 3 (Gemini/k2-horizon) transparently

## Rationale

| Option | Considered | Rejected because |
|---|---|---|
| Three-tier: Deterministic + Jev + Claude (chosen) | ✅ | — |
| Single-tier: Claude for everything (current) | ✅ | Too expensive and slow for continuous runs |
| Two-tier: Rules + Claude | ✅ | Misses the fast-decision middle ground; still expensive for high-frequency navigation |
| Two-tier: Jev for everything + Claude fallback | ✅ | Jev is not suitable for complex diagnosis/narrative generation |
| Full replacement with Jev only | ✅ | Jev cannot do deep reasoning; diagnosis quality would suffer |

The three-tier model matches the "System One / System Two" cognitive science model:
- System One: fast, automatic, low-effort (Jev for navigation)
- System Two: slow, deliberate, high-effort (Claude for diagnosis)
- Below System One: deterministic rules that need no model at all

## Consequences

**Positive:**
- ~70% reduction in Claude invocations per run (estimated, based on navigation-to-diagnosis ratio)
- Faster runs: Jev decisions are expected to be 5–10× faster than Claude
- Lower cost per run enables affordable continuous/scheduled runs
- Cleaner separation of concerns: each tier does exactly what it is good at
- Tier 3 (Gemini/k2-horizon) remains authoritative for high-stakes outputs (diagnosis, reports)

**Negative / Trade-offs:**
- Additional complexity: three clients, routing logic, fallback handling
- Jev skill definitions require maintenance when navigation patterns change
- Requires Typesafe AI API key and network dependency (mitigated by Claude fallback)
- Must tune Jev confidence threshold to avoid over-escalation to Tier 3

**Neutral:**
- Existing Tier 3 client code (Bedrock at the time, now Gemini/k2-horizon) is unchanged in shape; it becomes Tier 3 only
- All existing tests remain valid; new tests needed for routing logic

## Implementation Notes

- `src/agent/tier_router.py` — `TierRouter` class with routing rules
- `src/agent/jev_client.py` — `JevClient` wrapping Typesafe AI API
- `src/agent/decision_service.py` — update to `TieredDecisionService`
- `src/agent/skills/` — Jev skill definitions (YAML or JSON)
- Routing confidence threshold: default 0.75 (configurable via `SNIFF_JEV_CONFIDENCE_THRESHOLD`)
- Metrics tracked per run: `tier1_calls`, `tier2_calls`, `tier3_calls`
