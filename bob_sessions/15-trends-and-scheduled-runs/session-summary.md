# Session 15: Trends, Reconnected Analytics, and Reliable Scheduled Runs

**Session Type:** Agent Mode
**Status:** Complete
**Date:** 2026-09-27

---

## Objectives

The user noticed the product showed almost no trend/aggregate data and asked why, whether the gap could be closed, and what else should be shown - "do some research and make a plan." Once the plan was approved, the follow-up instruction was explicit: build all of it, and make sure it runs reliably in production.

---

## What Was Actually Done

### 1. Diagnosis before building anything

Three distinct, confirmed-in-code causes, not guesses: (a) `components/FrictionHeatmap.tsx` was fully built and calling `getFrictionAnalytics()` but never imported anywhere; `lib/queries.ts`'s `getPersonaMetrics()` was defined but never called; the `agent_confidence_metrics` SQL view had no query function at all. (b) `src/evidence/audit_checks.py` captures real Core Web Vitals (LCP/FCP/CLS) and SEO facts on every audit, but `audit_orchestrator.py` only fed them into the k2-horizon prompt as writing context and then discarded the actual numbers - no field for them ever existed on `AuditReport`. (c) Every existing view was single-item scoped (one run, one audit); nothing aggregated. This had been flagged before (`docs/product/MARKET_RESEARCH.md`'s backlog: "Sniff Score," "baseline/regression comparison") but only ever became `bob_sessions/06-10` prompts - no `session-summary.md` exists for any of them, confirming they were planned and never executed.

Research across synthetic monitoring (Checkly, Datadog), product analytics (PostHog, Amplitude), CWV dashboards (Calibre, SpeedCurve), and QA flakiness tooling (BrowserStack) converged on three patterns applied here: a KPI trend with a good/bad threshold band, a categorical breakdown as its own trend (not just a snapshot), and click-through from an anomaly into the item that explains it. CRO/audit tools were the weakest category for history-tracking in the research - a real opening for Sniff's repeatable audit score, which no competitor tracks over time well.

### 2. Reconnected + newly captured data (Phase 1)

`AuditReport` gained `core_web_vitals`/`seo_checks` (both `Optional`, so audits stored before this existed still deserialize). `audits` gained real `lcp`/`fcp`/`cls` columns (not just buried in the JSONB `report_json`) via a migration applied to the live Supabase project, so Phase 2's trend queries can aggregate directly. `FrictionHeatmap` got mounted on the dashboard, `getPersonaMetrics()` got a real "Persona Comparison" home, and a new `getAgentConfidenceMetrics()` surfaces a stat row on the run detail page.

### 3. New aggregate views (Phase 2)

A "Trends" tab on the dashboard: run outcome rate over time, root-cause distribution over time, persona comparison, and - the identified differentiation opportunity - audit score history per URL with click-through to the specific audit, plus a Core Web Vitals distribution trend. Every section has a real, deliberately-designed empty state, verified against actual (sparse) production data rather than assumed: at build time there were 0 runs and only 2-3 audits in production, and every empty-state branch was traced against that real data before calling it done.

### 4. Scheduled/continuous runs, designed for actual reliability (Phase 3)

The one place a naive build would have broken in production. Rejected running `apscheduler` (an anticipated-but-unused dependency) in-process inside FastAPI: the `sniff-api` Cloud Run service is confirmed live to autoscale to 3 instances (`maxScale: 3`), so an in-process scheduler would fire the same job independently on every instance. Instead: a `schedules` table in Supabase (the actual persistent source of truth, survives restarts and is shared across instances), a `POST /internal/scheduler/tick` endpoint that atomically claims a due schedule via a conditional `UPDATE ... WHERE next_run_at <= now()` (Postgres's own row-serialization makes a losing concurrent claim return zero affected rows, not a race), and one real Cloud Scheduler job (`sniff-scheduler-tick`, `*/5 * * * *`) as the single external trigger - GCP-managed, retried automatically, immune to how many Cloud Run instances exist behind it. `apscheduler` removed from `pyproject.toml` since this design never needed it.

`_schedule_still_busy()` guards against a slow run piling up duplicate executions if it outlasts its own interval.

---

## Why These Specific Decisions

**Verify claims about the current architecture, don't assume**: the multi-instance duplicate-scheduler risk wasn't hypothetical - `gcloud run services describe` was checked live before ruling out the in-process approach.

**Prove reliability with a real live schedule, not just unit tests**: a real 5-minute schedule against `https://example.com` was created against production and watched through several real Cloud Scheduler ticks - confirmed the claim advances `next_run_at` correctly, doesn't double-fire, and the busy-guard would apply - before calling the feature done, then deleted once proven.

**Parallelize independent frontend work, but watch for shared-file collisions**: three background agents worked concurrently on `app/dashboard/page.tsx` for different reasons (mounting FrictionHeatmap, adding the Trends tab, adding a Schedules nav link). This was a genuine coordination risk flagged mid-session; in practice each agent's precise Edit-tool patches stacked cleanly since none touched the same lines, but running all three against one shared file was still an avoidable design choice, not something to repeat carelessly next time.

**Don't trust a screenshot's first impression**: a chart line appeared broken (a tiny stub instead of a full connecting line) during visual verification; direct SVG-path inspection showed the path was actually complete, and a longer post-render wait proved it was just Recharts' mount-in animation caught mid-draw, not a bug. Verifying against the actual DOM/SVG state, not just a first screenshot, avoided a false-positive "fix."

---

## Verification

- `uv run --extra dev pytest`: 162/162 passing, including a new concurrency-focused test suite (`tests/test_schedule_store.py`) proving the atomic-claim logic wins/loses correctly against a mocked postgrest client, plus endpoint-level tests for the full `/schedules` CRUD and `/internal/scheduler/tick`.
- `yarn build`/`yarn lint` clean across all three parallel frontend changesets, combined.
- Real production data flowed end-to-end and was visually verified: a live Cloud Scheduler tick fired, claimed a real schedule, ran a real audit, and its Core Web Vitals/SEO data rendered correctly on the audit page and in the Trends tab's score-history chart (including a working click-through to the audit detail page).
- Both backend (Cloud Run) and frontend (Vercel) redeployed and confirmed live.

---

## Next Steps

→ Once real usage accumulates (or a user sets up real recurring schedules), the client-side bucketing in `getRunTrendHistory`/`getAuditTrendHistory` should be revisited for a proper SQL aggregation view if the row counts grow enough to matter.
→ `docs/product/MARKET_RESEARCH.md`'s "Sniff Score"/"baseline regression comparison" backlog items are now substantially addressed by the Trends tab and score-history chart - worth updating that doc to reflect it's no longer purely a backlog item.
