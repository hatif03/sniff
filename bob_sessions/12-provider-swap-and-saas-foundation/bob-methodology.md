# Session 12: Bob Methodology — Provider Swap + SaaS Foundation

## Bob Mode Used

**Agent Mode**

This is the largest and most complex session in the project. It performed five distinct categories of work simultaneously: removing the last traces of the original internal name, replacing the AI provider stack, building the FastAPI SaaS backend, redesigning the UI, and researching new metrics. Multiple Bob capabilities were used together.

---

## Bob Mode: Agent Mode

Agent mode was required for this session's scope: writing code, running `gcloud` and `uv` commands, installing new packages, and deploying services all require Agent mode's tool access.

---

## Bob Tools and Techniques

### Live API Testing With Real Credentials (Critical Technique)
Two separate bugs were found only through live API calls — not through documentation or unit tests:

1. **Gemini model ID wrong for this GCP project**: The publicly-documented current model `gemini-3.5-flash-lite` returned 404 on the actual GCP project tested. `gemini-2.5-flash-lite` worked. Rather than hardcode the working model, Bob added an automatic fallback retry on 404 — `GeminiClient` retries once against `fallback_model_id` before failing. The tension was documented explicitly in code: 3.x is current per Google's docs but not yet rolled out to every project; 2.5 is on a retirement countdown.

2. **Jev model ID wrong (from Session 04 context)**: The config default `jev-1` was rejected with `"Unknown model: jev-1"`. Real default: `jev-latest`. Found live, fixed live, re-verified.

**Lesson**: for new or niche APIs, live verification is mandatory, not optional. Search results for these APIs were polluted with outdated or SEO-generated content.

### Capability Gap Analysis Before Design
The k2-horizon decision split was discovered by reading ifm.ai's actual docs bundle: k2-horizon is a text-only chat API. Zero documented image/vision input path anywhere. This is not a preference — it is a hard capability gap.

Bob's response: design the split around the capability gap, not around what would be convenient. Vision-dependent calls go to Gemini; text-only calls go to k2-horizon. This is the correct engineering response to a constraint discovered through documentation reading.

### Minimal Interface Change
The new `GeminiClient` and `K2HorizonClient` match `BedrockClient`'s old interface exactly — same `invoke()`/`invoke_with_json_response()` method signatures. `DecisionService` needed no interface changes, just a different concrete client.

This is the "reuse existing patterns instead of inventing parallel ones" principle: fewer new mechanisms to reason about.

### Sub-Agent for UI Work
A sub-agent was used for the initial UI redesign exploration in parallel with the backend provider-swap work. The two streams of work did not touch the same files, making parallelism safe and efficient.

### Bug Found via Compiled CSS Output
The shadcn `@theme inline` block silently redefined `--color-primary`/`--color-accent`/`--color-muted` on top of the app's own pre-existing tokens (Tailwind v4's token system: last `@theme` declaration wins, flat registry). Bob verified this via *compiled CSS output*, not source code alone. The effect: most secondary body text would have been nearly invisible in production. Fixed by renaming ~70 call sites onto shadcn's own token vocabulary.

**Lesson**: for CSS token systems, the source file is not the truth — the compiled output is. Verify CSS changes against what is actually emitted.

### Phase 1 vs Phase 2 Scoping
Bob explicitly scoped what was and was not built, written into `docs/product/SAAS_ROADMAP.md`:
- Phase 1 (built): single shared Bearer token, in-process FastAPI background tasks, Supabase service role
- Phase 2 (not built, documented): real per-user auth (Supabase Auth + RLS), billing (Stripe), a real job queue, abuse prevention, rate limiting

Bob's principle: **a vague "SaaS-ready" claim without naming what is missing is actively misleading**. Explicit Phase 1/Phase 2 separation is the honest alternative.

### Supabase MCP (Partial)
The Supabase project had not yet been provisioned (that happened in Session 14). This session designed the FastAPI backend using the existing Supabase client pattern from `sniff-ai/src/integrations/supabase_client.py`, with real Supabase provisioning deferred to Session 14.

---

## Key Bob Discipline Applied

**Investigate before building**. All five streams of work in this session started with reading existing code or documentation:
- Read `bob_sessions/` before cleaning up remaining internal name mentions
- Read ifm.ai's docs before designing the k2-horizon split
- Read Typesafe's docs before fixing the Jev model ID
- Read `package.json` before proposing new UI libraries
- Read compiled CSS before fixing the token collision

None of the major decisions in this session were made by assumption.
