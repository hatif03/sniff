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

Re-ran the exact goal/URL combination that failed in the user's report (`"Find and open the AI Hackathons section"` against `https://lablab.ai/`, `confused_first_time_user` persona) against the fixed, deployed backend to confirm the fix holds for the real reported failure, not just in isolated unit tests. That run genuinely succeeded from a reliability standpoint (2 real steps, a real diagnosis produced, no freeze, no data loss) - but its own outcome was still "failure," which triggered the next round below.

### 5. Two screenshots that never actually worked, and a third real agent bug

Trying to view the seeded `github.com` audit surfaced a `Backend returned 404`, and the re-run `lablab.ai` run's step-by-step replay showed a completely blank screenshot area. Neither was new breakage - both were pre-existing gaps this session's own redeploys and seeding finally exposed:

- `GET /audits/{audit_id}` only ever checked the in-process `AUDIT_STORE`, no Supabase fallback - any completed audit became a permanent 404 the moment that dict lost the entry (which every one of this session's several redeploys did). Fixed by falling back to Supabase (the actual system of record) and reconstructing the response from `report_json`.
- `upload_audit()`'s own docstring admitted the gap: screenshots were never uploaded to Supabase Storage, just left as local filesystem path *strings* inside `report_json.images` - ephemeral, gone the moment the capturing Cloud Run instance did. Fixed by uploading each screenshot the same way run screenshots already were, storing the resulting public URL in `report_json.images` instead.
- Separately, `ScreenshotGallery`'s run screenshots (already real, working Supabase Storage URLs) never rendered either - `next.config.ts`'s image allowlist hardcoded a *different, stale* Supabase project hostname left over from an earlier re-provisioning. Next.js silently refuses any image from a non-allowlisted host, no error, just a blank image. Fixed by deriving the allowlisted hostname from `NEXT_PUBLIC_SUPABASE_URL` at build time instead of a hand-copied string, so it can't drift out of sync again.

Re-running the `lablab.ai` goal repeatedly (to verify the above, and per an explicit ask to get one genuinely clean success for a live demo) surfaced a fourth, independent real bug: the same run kept trying to tap "Accept All" a second time after already successfully dismissing the cookie banner, failing every time. Root-caused via the raw observation data, not guessed: the second observation's `visible_text` still contained the entire cookie banner, word-for-word identical to before the tap - even ~15+ seconds later, ruling out a simple timing race. The actual bug was in `_extract_visible_text()`'s own JS: `el.innerText || el.textContent` specifically defeats visibility-awareness - `innerText` correctly returns `""` for a dismissed (`display:none`) element, but the `textContent` fallback then pulls that same stale text right back in, forever, regardless of how long anything waits. Fixed by checking `el.offsetParent === null` before including an element at all, and dropping the `textContent` fallback. `PlaywrightWorker.tap()`'s fixed 0.5s post-click settle delay was also bumped to 1.2s along the way (a real, if smaller, contributor - `networkidle` was considered and rejected, since these real pages have constant background analytics traffic that never goes idle).

Also fixed, on request: `getRecentRuns()` now excludes `outcome=failure` so the shared public dashboard isn't cluttered with failed attempts from active debugging.

---

## Why These Specific Decisions

**Fix the shared function once, not every caller.** Both blocking-call fixes (goal enhancer, planner) and both screenshot fixes (full-page, viewport) live in the one place every caller already routes through — matching how the k2-horizon continuation retry (session 16) fixed a shared client method rather than patching call sites.

**A queue proportionate to actual scale, not the eventual one.** `SAAS_ROADMAP.md` already flags a real distributed job queue (Celery+Redis) as necessary once there are concurrent paying customers — that remains true and is *not* what got built here. A single in-process `asyncio.Queue` with one consumer is the smallest change that actually solves the problem this session hit: work landing on a Cloud Run instance that then gets reclaimed. Building the Celery version now would be solving a problem Phase 1 doesn't have yet.

**Live production data was the actual bug-finder, twice in one session.** Neither the blocking-call bug nor the concurrent-execution bug was caught by 193 passing mocked tests — both needed a real failed run and real seeding attempts against a real deployed service to surface. Both got a deterministic regression test afterward, but the discovery itself required live data.

**Investigate before concluding "it's just this site."** The instinct on seeing a failed run against one specific site could have been to blame the site. Pulling the actual Supabase rows and Cloud Run logs first showed the real mechanism (a blocking call + a guardrail race, then later a genuine visibility-detection bug in text extraction), which also explained why each failure was 100%-reproducible rather than a flaky one-off.

**A timing symptom deserves a timing-vs-logic diagnosis, not just a bigger sleep.** The repeat-tap failure recurred even after the settle delay was bumped from 0.5s to 1.2s. Rather than keep guessing larger numbers, the raw observation data was checked directly: the second tap attempt happened ~15 seconds after the first succeeded - far more time than any real animation needs. That ruled out "not enough wait time" and pointed straight at the actual bug (a visibility-detection defect that no amount of waiting could ever fix).

**Don't silently backfill history to make a fix look more complete than it is.** Audit screenshots uploaded before the Supabase-persistence fix still hold dead local paths - deliberately left as-is (documented as a known limitation) rather than quietly reprocessed, since reprocessing would need the original ephemeral files, which are already gone.

---

## Verification

- `uv run --extra dev pytest`: 208/208 passing (up from 193 at session start) — goal-enhancement/blocking-call regression (3), screenshot-resilience (4), direct queue-serialization proof (1), Supabase audit-image upload/read-back (6), GET /audits Supabase-fallback (1), plus 7 existing tests updated for the new async execution model.
- `ruff check` clean on every touched file; `yarn build`/`yarn lint` clean on every touched frontend file.
- Real production verification, not just unit tests, at every step: the exact reported failure (lablab.ai goal-run) re-run against the fixed, deployed backend; a real audit (github.com) completed via the queued execution path; a real screenshot-timeout site (stripe.com) completed via the resilience fallback with a real *different* failure surfaced downstream (an unrelated k2-horizon network timeout, not a regression); a previously-404ing audit confirmed viewable again via the Supabase fallback; the `lablab.ai` goal re-run repeatedly until the actual repeat-tap root cause was found and fixed.
- Backend redeployed to Cloud Run (`sniff-api`) five times across this session as each fix landed, each confirmed serving 100% of traffic on its new revision; frontend redeployed to Vercel twice.

---

## Known Limitations

A full, honest list lives in `sniff-ai/docs/product/ARCHITECTURE.md` Section 17 ("Known Limitations"), added this session. Highlights: text extraction can still concatenate two adjacent elements' text with no separator (a *different* bug from the visibility-detection one fixed here, still open); a raw k2-horizon network timeout still fails a page outright (no retry for that failure class, only for reasoning-token exhaustion); the job queue serializes across requests but not within one `parallel=True` experiment; historical audits from before the screenshot-persistence fix still show "unavailable."

## Next Steps

→ Text-run separation in `_extract_visible_text()` (distinct from the visibility-detection bug fixed this session) - two adjacent DOM elements with no whitespace between them still concatenate into one nonsensical string the agent can try to tap.
→ `ExperimentOrchestrator`'s `parallel=True` mode still runs multiple personas' browser sessions concurrently *within* one experiment job — the new queue only serializes *across* separate top-level requests, not a single experiment's own internal concurrency. Deliberately out of scope here (it's the feature's intended behavior, not a bug this session found), but worth keeping in mind if experiments start showing the same Cloud Run scale-up/down symptom.
→ The screenshot resilience fallback logs a warning at each degraded tier but doesn't currently surface "this page's screenshot is a placeholder" anywhere in the `AuditReport` itself — a user looking at a placeholder-image audit today has no in-product signal that the capture degraded, just an unusually blank screenshot.
→ No retry exists for a raw k2-horizon network-level timeout (as opposed to the reasoning-token-exhaustion case the continuation retry already handles) - a genuinely slow/unresponsive upstream response still fails that page outright.
