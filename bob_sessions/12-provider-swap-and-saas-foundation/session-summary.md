# Session 12: Provider Swap + SaaS Foundation

**Session Type:** Agent Mode
**Status:** ✅ Complete (Phase 1 - see `docs/product/SAAS_ROADMAP.md` for Phase 2)
**Date:** 2026-09-26

---

## Objectives

1. Remove every remaining trace of the project's original internal name, including inside `bob_sessions/`/`.bob/` themselves.
2. Replace AWS Bedrock with k2-horizon (ifm.ai) and Gemini (Google Cloud), using real provided API credentials.
3. Turn `sniff-web` and `sniff-ai` from two disconnected things into one product - a web UI that can actually trigger and watch a run, not just display historical CLI-uploaded data.
4. Redesign the UI to professional SaaS quality (shadcn/Radix, a real chart library, a distinguished palette, real animation).
5. Expand the analysis/metrics the product surfaces, informed by competitor and PostHog research.

---

## What Was Actually Done

### 1. Full "previous internal name" removal, including the session logs themselves

Earlier in this project's history, a decision was made to leave `bob_sessions/`/`.bob/` untouched as "historical record" when the rename to Sniff happened. That decision was explicitly reversed this session - these session logs are the user's own documentation convention, not something to hide, so they get corrected like any other stale doc rather than preserved-as-is. Renamed `bob_sessions/02-rename-sherlock-to-sniff/` → `bob_sessions/02-project-rename/`, fixed every remaining literal mention across `bob_sessions/`, `.bob/CONTEXT.md`, `.gitignore`, `.bobignore`, `CONTRIBUTING.md`, and `sniff-expansion-plan.md` (paraphrasing historical narrative, fixing code/env-var examples to the real current names, and deleting two `sherlock.json` gitignore entries that had zero code behind them - confirmed via grep before deleting rather than assumed). Final repo-wide case-insensitive search: zero hits, no exclusions.

### 2. Provider swap: Bedrock → Gemini + k2-horizon

**Key finding that shaped the whole design**: k2-horizon (ifm.ai) is a real, working, OpenAI-compatible text-only chat API - confirmed by reading their actual docs bundle and finding zero documented image/vision input path anywhere. The existing per-step navigation decision sends a screenshot + text to a vision model every step. That's not a preference to route around, it's a hard capability gap.

**Resolution**: split by what actually needs vision.
- `src/agent/gemini_client.py` (`GeminiClient`) - Vertex AI Gemini, Application Default Credentials (no API key - `gcloud auth application-default login` was already done on this machine), takes over the vision-dependent navigation call. Same `invoke()`/`invoke_with_json_response()` shape the old `BedrockClient` had, so `DecisionService` needed no interface changes, just a different concrete client.
- `src/agent/k2horizon_client.py` (`K2HorizonClient`) - thin wrapper around the `openai` package (per ifm.ai's own docs, which literally say to reuse the standard OpenAI client with a custom `base_url`) pointed at `api.ifm.ai/v1`. Takes over `GoalEnhancer`/`Planner`/`PersonaReviewer` - none of which need vision.
- `src/agent/bedrock_client.py` deleted. `boto3`/`botocore` removed as dependencies. `BedrockConfig` replaced by `GeminiConfig`/`K2HorizonConfig` in `SniffConfig`, same pattern. `sniff preflight` and `sniff init` (both CLI commands) rewritten to validate/configure the new providers instead of AWS.
- **A model/region access issue was found and fixed via live testing, not just docs**: the publicly-documented current Gemini model (`gemini-3.5-flash-lite`) 404'd ("not found or your project does not have access to it") on the actual GCP project this was tested against, while `gemini-2.5-flash-lite` worked. Rather than just picking whichever model happened to work today, `GeminiClient` now automatically retries once against `fallback_model_id` on a 404 before failing - a real, tested fallback path, not just a config field nobody reads. Documented the tension explicitly in code: 3.x is current per Google's docs but not yet rolled out to every project; 2.5 works today but is on a retirement countdown (~Oct 20 2026 on Vertex AI) - re-check before that date if 3.x access still hasn't landed.
- **Jev's model ID was also wrong and only found by testing live**: the config default `jev-1` (a guess from before a real key existed) got rejected by the real API with `"Unknown model: jev-1"` once actually called - the real default is `jev-latest`. Fixed and re-verified live.

### 3. SaaS foundation - one product, not two

Before this session: zero API routes existed anywhere; `sniff-web` read Supabase directly and unauthenticated; a run could only be started from a developer's local CLI; multi-persona "experiment" runs never even reached Supabase.

- New `sniff-ai/src/api/` FastAPI app: `POST /runs`, `POST /experiments`, `GET /runs/{run_id}`, `GET /healthz`, gated by a shared Bearer token (`SNIFF_API_TOKEN` - explicitly Phase 1; real per-user auth is Phase 2, see below). Wraps `RunOrchestrator`/`ExperimentOrchestrator` directly as background tasks.
- Investigated rather than assumed the "experiments never upload to Supabase" gap: it turned out each persona's `RunOrchestrator` sub-run *was* already auto-uploading independently (identical to a solo run) - implementing the literal ask on top of that would have double-inserted every row. Instead, per-persona auto-upload is disabled for experiment sub-runs and the upload is centralized once per persona in the API's experiment handler, using each persona's full captured `RunReport`.
- Renamed the confusing sync CLI wrapper `Orchestrator` → `SyncOrchestrator` (its actual two call sites, `sniff run` and `sniff demo`, updated) so the API's use of the real async `RunOrchestrator` isn't confused with it.
- Dockerfile based on Playwright's own official image (browser binaries pre-baked, matched to the exact pinned Playwright version) so the backend is deployable as one container.
- `sniff-web` gets Next.js Route Handlers (`app/api/backend/**`) that proxy to the FastAPI backend server-side, attaching the shared Bearer token there - the browser never sees the secret, only calls same-origin paths. A new `/dashboard/new-run` page (URL, goal, persona/device/network, four quick-start templates) posts a run, then polls for live status with an animated progress view, landing on the same run-detail page the existing Supabase-backed dashboard already had (confirmed the `run_id` the frontend gets back is the exact same one the backend threads through to the Supabase row, so "view details" resolves to real data).
- What's explicitly NOT built - written up as `docs/product/SAAS_ROADMAP.md` instead, because each needs an account/decision only the project owner can make: real multi-tenant auth (Supabase Auth + RLS, replacing the Phase-1 shared secret), billing (Stripe), a real job queue (today's in-process background task is single-instance only), abuse prevention (rate limiting, domain-ownership verification before letting a stranger point a browser agent at a URL), and actual hosting/provisioning.

### 4. UI redesign

- `shadcn@latest init` (Radix-based components) on top of the existing Tailwind v4 setup. Added Card/Table/Tabs/Badge/Dialog/Sheet/Button/Input/Select/Label/Textarea/Chart.
- **Found and fixed a real bug the shadcn CLI introduced**: its generated `@theme inline` block silently redefined `--color-primary`/`--color-accent`/`--color-muted` on top of the app's own pre-existing tokens of the same names (Tailwind v4 treats all `@theme` blocks as one flat registry - last one wins). Verified via *compiled CSS output*, not just source, that this would have made most secondary body text across the whole site nearly invisible. Fixed by renaming ~70 call sites onto shadcn's own token vocabulary rather than maintaining two colliding systems, and removed the dead colliding keys with a comment explaining why, so it can't silently regress again.
- Palette: brand indigo primary + a reserved gold accent for premium touches; chart-specific status colors (good/warning/critical) came from the `dataviz` skill's pre-validated palette, deliberately scoped to charts only rather than reused as a general UI accent.
- Two previously hand-rolled `<div>` progress-bar components replaced with real shadcn/Recharts bar charts with tooltips.
- Animation: staggered list reveal, a dependency-free `AnimatedNumber` count-up component, and a live-updating progress view for an in-flight run.

### 5. Expanded analysis - research done, implementation deferred

Live research this session (PostHog's actual product pages, Lighthouse/PageSpeed's scorecard model, and a few AI-driven UX-critique tools) produced a prioritized list of new metrics the agent could surface with little/no new browser instrumentation (Core Web Vitals capture, cross-persona comparison, per-step friction/confusion scoring, an accessibility pass, AI-suggested fixes, and others) - written into `docs/product/MARKET_RESEARCH.md`'s backlog section with rationale and rough effort per item. **Not implemented this pass** - the session's time went into the architecture/provider/SaaS-foundation work above instead of also building new metrics on top of it in the same pass.

---

## Why These Specific Decisions

**Live-test before trusting docs, especially for very new products (k2-horizon, Jev)**: both the Gemini model-access issue and the Jev model-ID issue were things public docs either didn't cover or got slightly wrong relative to the actual live API - caught only because real calls were made with the real keys before calling any of this "done."

**Reuse existing patterns instead of inventing parallel ones**: the Gemini/k2-horizon clients match `BedrockClient`'s old interface exactly; the Jev critic reuses `DecisionService`'s existing repair-retry loop; the FastAPI backend reuses `RunOrchestrator`'s existing Supabase-upload call rather than re-implementing it. Fewer new mechanisms to reason about.

**Scope Phase 1 vs Phase 2 explicitly rather than half-build a SaaS**: real multi-tenant billing infrastructure is not a one-session job, and a vague "SaaS-ready" claim without naming what's missing (auth, billing, queueing, abuse prevention) would be actively misleading about what's actually safe to put in front of strangers.

---

## Verification

- `uv run --extra dev pytest`: 129/129 passing (includes new `test_gemini_client.py`, `test_k2horizon_client.py`, rewritten `test_jev_client.py`, new `test_api.py`).
- `uv run --extra dev ruff check` clean on every file touched this session.
- `yarn build` and `yarn lint` clean in `sniff-web`, including the new `/api/backend/*` routes and `/dashboard/new-run` page.
- Live end-to-end smoke test with real credentials: Gemini (with the fallback path actually exercised), k2-horizon, and Jev's `TierRouter` (`enrich_context`, `check_goal_reached`, `critique_decision`) all called against the real APIs successfully, not just against mocks.
- Repo-wide case-insensitive search for the project's original internal name: zero hits, no exclusions.

---

## Next Steps

→ Implement the highest-priority items from `docs/product/MARKET_RESEARCH.md`'s backlog (Core Web Vitals capture, cross-persona comparison, friction scoring - flagged as near-zero marginal cost since the agent already produces the underlying data).
→ Work through `docs/product/SAAS_ROADMAP.md` Phase 2 items when ready to accept real outside users (real auth first, before anything else - the current shared-secret gate is not meant to survive contact with the public internet).
