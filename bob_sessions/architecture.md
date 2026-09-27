# Sniff — Architecture Evolution Record

This document tracks every significant architectural decision and change made across all 17 Bob sessions. It is the single place to understand *how the architecture changed*, *when*, *why*, and *what was considered and rejected*.

For the current architecture (latest state), see `sniff-ai/docs/product/ARCHITECTURE.md`. This document is the evolution history, not the current state.

---

## Architecture Timeline

```
Session 00-01  ─── Foundation & Plan
Session 02-05  ─── Core Refactoring (Rename, Deps, Jev, Three-Tier)
Session 06-11  ─── Feature Expansion (Scheduler, Regression, Replay, Score, CI/CD, Docs)
Session 12     ─── Provider Swap + SaaS Foundation (major pivot)
Session 13     ─── Second Product Surface (Audit)
Session 14     ─── Real Persistence (Supabase)
Session 15     ─── Scheduler Architecture Pivot (Cloud Scheduler replaces APScheduler)
Session 16     ─── Third Product Surface (Whole-Site Audit)
```

---

## Decision 1: Three-Tier Intelligence Architecture

**Session**: 01 (Plan mode) + 04/05 (Implementation)  
**ADR**: [ADR-001](../docs/adr/ADR-001-three-tier-architecture.md)  
**Status**: Accepted — in production

### The Problem
Every navigation step called AWS Bedrock Claude — even trivial ones like "tap the Sign Up button." For a 50-step run: 50 full LLM invocations, ~$0.30/run, 2–5s latency per step.

### What Was Decided
Split the decision pipeline into three explicit tiers:

| Tier | Technology | Role |
|---|---|---|
| 1 — Deterministic | Pure Python | Signal extraction, guardrail checks, state transitions |
| 2 — Jev (System One) | Typesafe AI Jev | Fast navigation, goal-reached check, context enrichment, decision gate |
| 3 — Gemini + k2-horizon (System Two) | Vertex AI + ifm.ai | Root cause diagnosis, narrative generation, scoring |

### What Was Considered and Rejected
- **Single-tier (Claude for everything)**: too expensive and slow for continuous runs
- **Two-tier (Rules + Claude)**: misses the fast-decision middle ground
- **Two-tier (Jev + Claude fallback)**: Jev is not suitable for complex diagnosis/narrative
- **Jev-only**: cannot do deep reasoning; diagnosis quality would suffer

### How Implementation Differed From Plan
The plan envisioned a `TieredDecisionService` replacing `DecisionService`. The actual implementation injected `TierRouter` as an optional parameter into the existing `DecisionService` — a smaller diff, keeping all existing callers working unchanged.

The plan envisioned three Jev skill files (`*.skill`). The real Typesafe API has no such runtime concept — one unified `/v1/systemone` endpoint batches all question types. No skill files were created.

The plan envisioned one generic `route() → Tier` dispatcher. The actual implementation identified three specific roles for Jev (ReAct observation interpreter, Speculative Fan-Out context enrichment, Generator-Critic gate) grounded in published patterns from Google and Typesafe.

---

## Decision 2: Dependency Update Strategy

**Session**: 01 (Plan) + 03 (Implementation)  
**ADR**: [ADR-002](../docs/adr/ADR-002-dependency-updates.md)  
**Status**: Accepted

### The Problem
Python and Node packages needed updating. Tailwind v4 is a breaking migration (removes `tailwind.config.js`, changes directive syntax).

### What Was Decided
- Pin to highest versions that actually build (not absolute latest)
- `typescript@6.0.3` / `eslint@9.39.5` (not 7.0/10.x — both have incompatibilities with `eslint-config-next`)
- Tailwind v4: remove `tailwind.config.ts`, update `postcss.config.mjs`, replace `@tailwind` directives with `@import "tailwindcss"` + `@theme` block

### Later Change (Session 12)
`boto3`/`botocore` removed entirely (AWS Bedrock dropped). Added:
- `google-genai>=2.25,<3` (Vertex AI Gemini SDK)
- `openai>=1.50.0` (OpenAI-compatible client reused for k2-horizon)
- `google-auth` (Application Default Credentials)

Rationale for reusing `openai` for k2-horizon: ifm.ai's own documentation says `pip3 install openai` and uses the standard client with a custom `base_url`. Following the vendor's documented pattern.

---

## Decision 3: Scheduler Approach (APScheduler → Cloud Scheduler)

**Session**: 01 (Plan), 06 (Original implementation plan), 15 (Production-corrected implementation)  
**ADR**: [ADR-003](../docs/adr/ADR-003-scheduler-apscheduler.md) (original) — superseded in Session 15  
**Status**: Original decision superseded; current implementation uses Cloud Scheduler

### Original Decision (Session 01 / ADR-003)
APScheduler in-process daemon: `SniffScheduler` class, SQLite job store, PID file, `sniff daemon start/stop/status` CLI commands.

**Rationale at decision time**: portable, no OS cron dependency, works in containers and cloud VMs.

### Why the Decision Was Superseded (Session 15)
`gcloud run services describe sniff-api` confirmed the Cloud Run service had `maxScale: 3`. An in-process scheduler would fire the same job independently on every instance — guaranteed duplicate execution on a multi-instance deployment. The APScheduler approach was correct when decided (before Cloud Run was chosen in Session 13), but the deployment constraint invalidated it.

### New Architecture
- `schedules` table in Supabase — shared persistent source of truth, survives restarts, visible to all instances
- `POST /internal/scheduler/tick` endpoint — atomically claims a due schedule via `UPDATE ... WHERE next_run_at <= now()` (PostgreSQL row serialisation makes a losing concurrent claim return zero rows, not a race)
- One GCP Cloud Scheduler job (`*/5 * * * *`) as the single external trigger — GCP-managed, auto-retried, instance-count-agnostic

`apscheduler` dependency removed from `pyproject.toml`.

### Lesson
Architecture decisions made before deployment context is known may need revision once deployment constraints are concrete. ADR-003 was correct at decision time; Session 15 superseded it with evidence from the actual production environment.

---

## Decision 4: AI Provider Swap (AWS Bedrock → Gemini + k2-horizon)

**Session**: 12  
**Status**: Accepted — in production

### The Problem
The original provider was AWS Bedrock Claude. The user had new API credentials for Gemini (Vertex AI, via Application Default Credentials) and k2-horizon (ifm.ai, OpenAI-compatible API).

### The Key Finding That Shaped the Design
k2-horizon is a text-only chat API. Reading ifm.ai's actual docs bundle found zero documented image/vision input path. This is a hard capability gap, not a preference. The existing per-step navigation decision sends a screenshot + text to a vision model — this cannot be routed to k2-horizon.

### The Split
| Work Type | Needs Vision? | Provider |
|---|---|---|
| Per-step navigation decision | Yes (screenshot) | Gemini (Vertex AI) |
| GoalEnhancer, Planner, PersonaReviewer | No | k2-horizon |
| Audit scoring, narrative, copy rewrites | Mixed (score=vision, text=no) | Gemini (score/verdict) + k2-horizon (copy/text) |

### Interface Compatibility
`GeminiClient` and `K2HorizonClient` match `BedrockClient`'s exact `invoke()`/`invoke_with_json_response()` interface. `DecisionService` required no interface changes — just a different concrete client injection.

### Discovered During Live Testing (Not From Documentation)
- `gemini-3.5-flash-lite` returned 404 on the actual GCP project. Added auto-fallback retry to `gemini-2.5-flash-lite` on 404. Documented the tension: 3.x is current per Google's docs but not yet rolled out to every project; 2.5 is on a retirement countdown.
- Jev model ID `jev-1` rejected by real API. Real default: `jev-latest`.

---

## Decision 5: SaaS Architecture — Phase 1

**Session**: 12  
**Status**: Phase 1 in production; Phase 2 documented in `docs/product/SAAS_ROADMAP.md`

### The Problem
`sniff-web` and `sniff-ai` were two disconnected things. Runs could only be started from a developer's CLI. The web dashboard only displayed historical CLI-uploaded data.

### Phase 1 Architecture
- New `sniff-ai/src/api/` FastAPI app: `POST /runs`, `POST /experiments`, `GET /runs/{run_id}`, `GET /healthz` (later `/status` — see Decision 8)
- Authentication: single shared Bearer token (`SNIFF_API_TOKEN`) — Phase 1 only, not for production with real users
- `sniff-web` Next.js Route Handlers proxy to FastAPI backend server-side; browser only calls same-origin paths
- Runs trigger `RunOrchestrator` as a FastAPI `BackgroundTask`

### What Was Explicitly Not Built (Phase 2)
- Real per-user auth (Supabase Auth + RLS)
- Billing (Stripe)
- Real job queue (in-process `BackgroundTask` is single-instance only)
- Abuse prevention (rate limiting, domain-ownership verification)

Phase 2 items are documented in `docs/product/SAAS_ROADMAP.md`. The distinction between Phase 1 and Phase 2 was written explicitly rather than leaving a vague "SaaS-ready" claim.

---

## Decision 6: Shared Persistence (Supabase, Real Database)

**Session**: 14  
**Status**: In production

### The Problem Before This Decision
- `SUPABASE_ENABLED=false` — no real Supabase project had ever been provisioned
- No `audits` table existed anywhere
- The frontend's audit history was an `localStorage` workaround — visible only to the browser that created it
- The `docs/supabase_schema.sql` had never been run against a real database

### The Bug Found During Provisioning
`docs/supabase_schema.sql` used MySQL-style inline `INDEX name (...)` clauses inside `CREATE TABLE`. Invalid PostgreSQL syntax. It had silently never been tested against a real Postgres instance. Fixed to separate `CREATE INDEX` statements.

### The Design
- Supabase project provisioned via Supabase MCP
- `runs` table: public-read RLS (anyone can see runs — no auth yet)
- `audits` table: public-read RLS, full report stored as JSONB (read whole, not queried by field)
- Backend: `SUPABASE_ENABLED=true`, service role key on Cloud Run
- Frontend: anon key on Vercel via `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### Later Additions
- Session 15: `lcp`, `fcp`, `cls` columns on `audits` (direct SQL columns, not just in JSONB) for aggregate trend queries
- Session 16: `site_audits` table + `audits.site_audit_id` FK

---

## Decision 7: Second and Third Product Surfaces

**Session 13 (Audit) + Session 16 (Whole-Site Audit)**  
**Status**: Both in production

### Single-Page Audit (Session 13)
Added as a second product surface alongside signup-flow testing. Schema derived from a real ColdVisit paid report (parsed from their Next.js page JSON). Two LLM roles:
- Gemini (vision): page score, verdict, 5-dimension analysis, annotated screenshot
- k2-horizon (text): copy rewrites, SEO findings, fix list

### Whole-Site Audit (Session 16)
Extends the single-page audit to an entire website. Key architectural decisions:
- Reuse `run_audit_on_page()` for every crawled page (not duplicated)
- Reuse `audits` table with a nullable `site_audit_id` FK (not a separate table)
- Reuse existing `/dashboard/audits/[auditId]` detail page for every crawled page (no new endpoint)
- Authentication: log in once via `PlaywrightWorker.login()`, reuse the session for all pages
- Discovery: `sitemap.xml` + same-origin link-following, with hard guardrails (`max_pages`, `max_depth`, `site_audit_hard_timeout`)

---

## Decision 8: Cloud Run `/healthz` Reserved Path

**Session**: 13  
**Status**: Permanent (renamed to `/status`)

### What Happened
The deployed backend returned a Google-branded 404 on `/healthz` externally, despite the service being healthy internally. Extensive elimination (DNS, IAM, org policies, load balancers, deploy flags, port, region, image size) ruled out all real misconfigurations.

### Root Cause
`/` and `/healthz` are reserved paths on Cloud Run's default `*.run.app` domain, intercepted at Google's edge before reaching any application, regardless of configuration.

### Fix
Rename the liveness endpoint from `/healthz` to `/status`. One-line change. Nothing was broken.

---

## Decision 9: CSS Token Collision (shadcn vs App Tokens)

**Session**: 12  
**Status**: Fixed — token vocabulary unified

### What Happened
`shadcn@latest init` generated an `@theme inline` block that silently redefined `--color-primary`/`--color-accent`/`--color-muted` on top of the app's own pre-existing tokens of the same names. In Tailwind v4, all `@theme` blocks are a flat registry — last declaration wins. Effect: most secondary body text across the whole site would have been nearly invisible.

### How It Was Found
Verified via *compiled CSS output*, not source code. The source file can look correct while the compiled output is wrong.

### Fix
Renamed ~70 call sites onto shadcn's own token vocabulary. Removed the colliding keys with a comment explaining why, so it cannot silently regress.

---

## Decision 10: k2-horizon Token Budget Exhaustion Retry

**Session**: 16  
**Status**: In production (applied to all k2-horizon callers)

### What Happened
k2-horizon sometimes exhausted its entire token budget on chain-of-thought reasoning before emitting any JSON at all. `response_format=json_object` guarantees JSON syntax, not that reasoning stays within the token budget. Reproduced 100% consistently against real content-rich pages.

### Fix
Bounded continuation retry inside `K2HorizonClient.invoke_with_json_response()`:
1. Raise the token ceiling: 4096 → 8192 (first line of defence)
2. On JSON-parse failure: one follow-up call resends original messages plus truncated response as assistant context, asking for the final JSON only — reusing the model's own reasoning chain rather than discarding it and starting over

Covered by two new client-level tests. Fix applied to the client layer (affects all callers — both single-page and whole-site audits) from one change.

---

## Decision 11: Blocking LLM Call Inside an Async Handler

**Session**: 17
**Status**: In production

### What Happened
A real user-reported run against `https://lablab.ai/` completed with 0 steps and no error anywhere. Investigation of live Supabase data + Cloud Run logs found the actual mechanism: `GoalEnhancer.enhance_goal()` (k2-horizon) was called directly inside the `async def _handle_navigate` handler, not wrapped in `run_in_executor` like every other LLM call in the orchestrator. A slow call froze the single FastAPI process for every request — confirmed live via a concurrent status-poll request logging 36.8s of latency for an in-memory dict read. The dwell-time clock also started before this call ran, so it could burn the entire 30s guardrail budget before the agent's first decision.

### Fix
Wrapped the call (and a second, latent instance in the planner's `get_next_action_plan`) in `run_in_executor`. Moved the dwell-clock reset to after goal enhancement completes. 3 regression tests, confirmed to fail against the pre-fix code.

---

## Decision 12: Single In-Process Job Queue (`JOB_QUEUE`)

**Session**: 17
**Status**: In production (all 6 background-task call sites migrated)

### What Happened
Firing several `POST /audits` requests concurrently (while seeding demo data) triggered a Cloud Run scale-up followed by a scale-down that silently killed whichever job had landed on the reclaimed instance — no error recorded, the work just vanished.

### Fix
Replaced every `BackgroundTasks.add_task(...)` call (`/runs`, `/audits`, `/experiments`, both branches of `/internal/scheduler/tick`, `/site-audits`) with a single module-level `asyncio.Queue` and one consumer coroutine (`_job_worker`), started via the app's `lifespan`. Every job now executes strictly one at a time, in submission order, on this one already-warm instance — regardless of how many requests arrive concurrently. API responses are unchanged (still immediate `status: "queued"`); only execution timing changed. A deliberate, proportionate choice: a real distributed queue (Celery+Redis) remains Phase 2 scope per `SAAS_ROADMAP.md` — this is the smallest change that solves the problem Phase 1 actually hit.

---

## Decision 13: Screenshot Capture Resilience

**Session**: 17
**Status**: In production

### What Happened
A seeded audit against `stripe.com` failed entirely: `Page.screenshot(full_page=True)` timed out after 30s waiting for the page to reach a stable render state (fonts still loading), taking down the whole audit before a single check had run.

### Fix
`PlaywrightWorker.screenshot()` now falls back from a full-page capture to a cheaper viewport-only capture, then to a placeholder image, on failure — so `screenshotPath` always points to a real file and the rest of the audit pipeline can still run on a degraded page. `screenshot_viewport()` got the same placeholder fallback directly; `screenshot_with_overlay()` inherits it for free (it already delegates to `screenshot_viewport()`). 4 new tests using a fake Playwright `Page` prove each fallback tier.

---

## Decision 14: Audit Data Must Survive Its Own Backend

**Session**: 17
**Status**: In production

### What Happened
Trying to view a seeded `github.com` audit returned `Backend returned 404`, and a run's step-by-step screenshots rendered as blank. Neither was new breakage: `GET /audits/{id}` only ever checked the in-process `AUDIT_STORE` (no Supabase fallback, so any redeploy lost every completed audit permanently); `upload_audit()` stored screenshot *local path strings*, never the actual files, into Supabase (`report_json.images` pointed at a filesystem path that only ever existed on the capturing Cloud Run instance); and `next.config.ts`'s image allowlist hardcoded a stale Supabase project hostname from an earlier re-provisioning, so Next.js silently refused to render even the screenshots that *were* real, working Storage URLs (run screenshots, uploaded correctly since session 13).

### Fix
`upload_audit()` now uploads each screenshot to Supabase Storage the same way run screenshots already are, storing the public URL in `report_json.images`. `GET /audits/{id}` falls back to Supabase (the actual system of record) when the in-process store has lost the entry, reconstructing the response from `report_json`. `next.config.ts` now derives its allowlisted hostname from `NEXT_PUBLIC_SUPABASE_URL` at build time instead of a hand-copied string. Audits uploaded before this fix still hold dead local paths - not backfilled, documented as a known limitation (`ARCHITECTURE.md` Section 17).

---

## Decision 15: Visibility-Blind Text Extraction

**Session**: 17
**Status**: In production

### What Happened
A goal-run against a real site kept trying to tap "Accept All" a second time after already successfully dismissing the cookie banner, failing every time. The raw observation data showed why: `visible_text` after the first (successful) tap was byte-for-byte identical to before it, even ~15 seconds later - too long for any real animation, ruling out a simple timing race. The actual bug was in `_extract_visible_text()`'s JS: `el.innerText || el.textContent` specifically defeats visibility-awareness. `innerText` correctly returns `""` for a dismissed (`display:none`) element, but the `textContent` fallback then pulled that same stale text back in, forever, regardless of how long anything waited.

### Fix
Check `el.offsetParent === null` before including any element at all; dropped the `textContent` fallback. `PlaywrightWorker.tap()`'s post-click settle delay was also bumped from 0.5s to 1.2s along the way (a real, smaller contributor - `networkidle` was considered and rejected since these real pages have constant background analytics traffic that never goes idle).

---

## Architecture State: Beginning vs End

### Beginning (Before Session 00)
```
sniff-ai/
├── Python CLI (Typer, original internal name)
├── Single-tier AI: every step → AWS Bedrock Claude (vision)
├── No web API
└── Next.js dashboard (sniff-web): read Supabase directly, CLI-upload only

No deployment. No brand name. No Supabase project provisioned.
193 test count: 67 (end of planning phase)
```

### End (After Session 17)
```
sniff-ai/ (sniff)
├── Python FastAPI backend
│   ├── Tier 1: Deterministic Python (signal extraction, guardrails)
│   ├── Tier 2: Typesafe AI Jev (goal-reached, context enrichment, decision gate)
│   ├── Tier 3: Gemini/Vertex AI (vision navigation, audit scoring)
│   │         + k2-horizon/ifm.ai (text: planning, persona review, copy rewrites)
│   ├── RunOrchestrator + AuditOrchestrator + SiteAuditOrchestrator
│   ├── JOB_QUEUE + _job_worker — every background job serialized, one at a time
│   ├── POST /runs, POST /audits, POST /site-audits
│   └── Cloud Scheduler → POST /internal/scheduler/tick (atomic claim pattern)
│
sniff-web/ (Next.js App Router)
├── /dashboard/new-run (single-page audit + site audit + run)
├── /dashboard/runs/[id] + /dashboard/audits/[auditId]
├── /dashboard/site-audits/[siteAuditId]
├── /dashboard (Trends tab: KPI history, root-cause distribution, audit score timeline)
└── Supabase (public Postgres): runs, audits, site_audits, schedules

Deployed: Cloud Run (backend) + Vercel (frontend) + GCP Cloud Scheduler
Tests: 208/208 passing
```
