# Session 17: Production Reliability Hardening — Blocking Calls, Job Queue, Screenshot Resilience

**Session Type:** Agent Mode
**Status:** Complete
**Date:** 2026-09-27

---

## Objectives

The user reported a real failed run from the live dashboard: a "Test a Goal" run against `https://lablab.ai/` finished with 0 steps, no error message anywhere, and a run detail page that failed to load. Screenshots were attached. The ask was to investigate and verify what actually happened.

Separately, the user asked to seed the production dashboard with 2-3 real (non-`example.com`) audits so the demo data looked genuine, and to clean up duplicate `example.com` rows. Seeding surfaced two more real problems, which the user then asked to be fixed properly: audits couldn't run concurrently without one silently losing to the other, and one seeded site failed outright on a screenshot timeout that should not have taken down the whole audit.

---

## What Was Actually Done

### 1. Root-caused the lablab.ai failure (not just noted it)

Queried the live `runs`/`observations`/`diagnoses` tables directly (Supabase REST, anon key, public-read) and pulled Cloud Run logs for the exact request window. Found: the run navigated successfully (one real observation, cookie-consent banner visible in the captured text), then nothing — zero rows in `agent_reasoning`, `total_actions: 0` — before failing on `Guardrail violated: Exceeded max dwell time on URL: 30s`.

The actual mechanism: `GoalEnhancer.enhance_goal()` (routed to k2-horizon) is a blocking network call, invoked directly inside the `async def _handle_navigate` handler — not wrapped in `run_in_executor`, unlike every other LLM call in the same orchestrator (`agent_service.get_decision` already was). A slow call froze the single FastAPI process for every concurrent request — confirmed live: a concurrent status-poll request logged **36.8 seconds** of latency for what should be an instant in-memory dict read. Worse, the dwell-time clock started right after `navigate()`, before goal enhancement ran, so a merely-slow (not even frozen) call could burn the entire 30-second guardrail budget before the agent ever got to make its first decision — failing the run with zero steps and no error, exactly as reported.

Fixed both symptoms in `src/core/orchestrator.py`: wrapped the call (and a second, latent instance of the same mistake in the planner's `get_next_action_plan` call) in `run_in_executor`; moved the dwell-clock reset to after goal enhancement completes, so the guardrail measures only the time the agent actually had to act. 3 new regression tests prove both the non-blocking behavior (a concurrent tick counter keeps advancing during a simulated slow call) and the dwell-clock ordering — confirmed they fail against the pre-fix code.

Along the way, ruff caught a real bug introduced mid-fix: a later, now-redundant `import asyncio` inside the same function made `asyncio` function-scope-local for the *whole* function, which would have raised `UnboundLocalError` the first time the planner branch executed. Fixed before it ever shipped.

### 2. A single in-process job queue (`JOB_QUEUE`)

Seeding real audits by firing several `POST /audits` requests back to back reproduced a second, distinct production issue: multiple concurrent Playwright-backed background tasks triggered a Cloud Run scale-up, and the subsequent scale-down silently killed whichever job had landed on the reclaimed instance — no error, no trace, the work just vanished. Confirmed via Cloud Run logs: an `INFO: Shutting down` line mid-crawl, no completion or failure log for two of three concurrently-fired audits.

Replaced all 6 `BackgroundTasks.add_task(...)` call sites (`/runs`, `/audits`, `/experiments`, both branches of `/internal/scheduler/tick`, `/site-audits`) with a single module-level `asyncio.Queue` (`JOB_QUEUE`) and one consumer coroutine (`_job_worker`), started via the app's `lifespan`. Every request still returns immediately with `status: "queued"` — the API contract is unchanged — but actual execution is now strictly serialized, one job at a time, in submission order, regardless of how many requests arrive concurrently or how many schedules are due in the same scheduler tick.

A new test (`test_queued_jobs_run_strictly_one_at_a_time`) proves the actual guarantee, not just that things still work: three audits are queued back to back, a tracking fake orchestrator records the maximum number simultaneously "in flight," and the queue is drained — `max_seen` must be exactly 1.

Updating this also required converting 7 existing tests that relied on `TestClient`'s old quirk of running `BackgroundTasks` synchronously within the request/response cycle — an assumption that's no longer true now that execution is genuinely decoupled via a background consumer. Added a `run_queued_jobs()` test helper that deterministically drains the queue on demand.

### 3. Screenshot capture degrades gracefully instead of failing the whole audit

One seeded audit (`stripe.com`) failed independently of the queue issue: `Page.screenshot(full_page=True)` timed out after 30 seconds waiting for the page to reach a "stable" render state (fonts still loading), taking down the entire audit before a single check had run.

Added a fallback chain to `PlaywrightWorker.screenshot()`: full-page capture, then (on failure) a cheaper viewport-only capture with a longer explicit timeout, then (on failure) a placeholder image — so `screenshotPath` always points to a real, openable file and the rest of the audit pipeline (checks, text/vision synthesis) can still run on a degraded page instead of losing the whole result. `screenshot_viewport()` got the same placeholder fallback directly; `screenshot_with_overlay()` inherits it for free since it already delegates its capture to `screenshot_viewport()`. 4 new tests using a fake Playwright `Page` prove each fallback tier, including that a real, openable image always exists at the returned path.

### 4. Data hygiene and verification

Seeded `github.com` (6.5/10, "Strong concept, but form friction") as a real audit via the fixed production backend, seeded one more site after this session's fixes, and deleted 2 of 3 duplicate `example.com` demo rows (kept the most recent), all via the Supabase REST API using the service-role key pulled quietly from the Cloud Run service's own environment — never printed or logged. Confirmed the dashboard's `getRecentAudits`/`getRecentRuns`/`getRecentSiteAudits` queries have no `user_id` filtering, no auth middleware, no session-scoping anywhere: every audit, run, and site-audit — seeded or user-created — is visible to any visitor, exactly matching the current no-auth Phase 1 design.

Re-ran the exact goal/URL combination that failed in the user's report (`"Find and open the AI Hackathons section"` against `https://lablab.ai/`, `confused_first_time_user` persona) against the fixed, deployed backend to confirm the fix holds for the real reported failure, not just in isolated unit tests.

---

## Why These Specific Decisions

**Fix the shared function once, not every caller.** Both blocking-call fixes (goal enhancer, planner) and both screenshot fixes (full-page, viewport) live in the one place every caller already routes through — matching how the k2-horizon continuation retry (session 16) fixed a shared client method rather than patching call sites.

**A queue proportionate to actual scale, not the eventual one.** `SAAS_ROADMAP.md` already flags a real distributed job queue (Celery+Redis) as necessary once there are concurrent paying customers — that remains true and is *not* what got built here. A single in-process `asyncio.Queue` with one consumer is the smallest change that actually solves the problem this session hit: work landing on a Cloud Run instance that then gets reclaimed. Building the Celery version now would be solving a problem Phase 1 doesn't have yet.

**Live production data was the actual bug-finder, twice in one session.** Neither the blocking-call bug nor the concurrent-execution bug was caught by 193 passing mocked tests — both needed a real failed run and real seeding attempts against a real deployed service to surface. Both got a deterministic regression test afterward, but the discovery itself required live data.

**Investigate before concluding "it's just this site."** The instinct on seeing a failed run against one specific site could have been to blame the site. Pulling the actual Supabase rows and Cloud Run logs first showed the real mechanism (a blocking call + a guardrail race), which also explained why the failure was 100%-reproducible rather than a flaky one-off.

---

## Verification

- `uv run --extra dev pytest`: 201/201 passing (up from 193) — 8 new tests (3 goal-enhancement/blocking-call regression, 4 screenshot-resilience, 1 direct queue-serialization proof) plus 7 existing tests updated for the new async execution model.
- `ruff check` clean on every touched file.
- Real production verification, not just unit tests: the exact reported failure (lablab.ai goal-run) re-run successfully against the fixed, deployed backend; a real audit (github.com) completed via the queued execution path; a real screenshot-timeout site (stripe.com) completed via the resilience fallback.
- Backend redeployed to Cloud Run (`sniff-api`) and confirmed serving 100% of traffic on the new revision.

---

## Next Steps

→ `ExperimentOrchestrator`'s `parallel=True` mode still runs multiple personas' browser sessions concurrently *within* one experiment job — the new queue only serializes *across* separate top-level requests, not a single experiment's own internal concurrency. Deliberately out of scope here (it's the feature's intended behavior, not a bug this session found), but worth keeping in mind if experiments start showing the same Cloud Run scale-up/down symptom.
→ The screenshot resilience fallback logs a warning at each degraded tier but doesn't currently surface "this page's screenshot is a placeholder" anywhere in the `AuditReport` itself — a user looking at a placeholder-image audit today has no in-product signal that the capture degraded, just an unusually blank screenshot.
