# Session 15: Bob Methodology — Trends, Reconnected Analytics, and Reliable Scheduled Runs

## Bob Mode Used

**Agent Mode**

This session has the richest methodology story of any in the project. It demonstrates: research before design, sub-agent parallelism with real coordination risk, live production verification as a mandatory step (not just tests), and a significant architectural pivot from the original plan.

---

## Bob Tools and Techniques

### Research Before Design (User-Directed)
The user's instruction was explicit: "do some research and make a plan." Bob researched four categories before proposing anything:
- Synthetic monitoring tools (Checkly, Datadog) — for KPI trend patterns
- Product analytics (PostHog, Amplitude) — for categorical breakdown trends
- Core Web Vitals dashboards (Calibre, SpeedCurve) — for time-series visualisation
- QA flakiness tooling (BrowserStack) — for click-through from anomaly to detail

The research converged on three patterns applied in the implementation:
1. A KPI trend with a good/bad threshold band
2. A categorical breakdown as its own trend (not just a snapshot)
3. Click-through from an anomaly into the item that caused it

The research also identified a differentiation opportunity: no competitor tracks repeatable audit scores over time well. The Sniff audit score history chart fills this gap.

### Diagnosis Before Building (Code Reading)
Three confirmed root causes for the missing trend data, each found by reading the actual code:
1. `components/FrictionHeatmap.tsx` was fully built and calling `getFrictionAnalytics()` but **never imported anywhere** — not even rendered. Not a bug in the component; a missing import.
2. `lib/queries.ts`'s `getPersonaMetrics()` was defined but never called — same issue.
3. `agent_confidence_metrics` SQL view had no corresponding query function at all.
4. `audit_orchestrator.py` captured real Core Web Vitals on every audit but only fed them into the k2-horizon prompt as writing context, then **discarded the actual numbers** — no field ever existed on `AuditReport` to preserve them.

Bob fixed each issue at its root, not with workarounds.

### Supabase MCP: Live Schema Migration
Bob used the Supabase MCP to apply a migration adding `lcp`/`fcp`/`cls` columns to the `audits` table on the live production Supabase project. These columns store Core Web Vitals as real database columns (not just buried in the JSONB `report_json`) so the Trends tab's queries can aggregate directly via SQL.

This is the Supabase MCP being used for a production schema change — not a local/dev migration, but an actual `apply_migration` against the live project.

### Critical Architectural Pivot: Cloud Scheduler vs APScheduler
The original plan (Session 06, ADR-003) specified APScheduler in-process daemon. Bob rejected this for the actual production architecture.

**How the conflict was discovered**: Bob ran `gcloud run services describe sniff-api` and confirmed the Cloud Run service was configured with `maxScale: 3`. An in-process APScheduler would fire the same job independently on every instance — a guaranteed duplicate execution problem on a multi-instance deployment.

**The replacement design**: 
- `schedules` table in Supabase (shared across all instances, survives restarts)
- `POST /internal/scheduler/tick` endpoint that atomically claims a due schedule via conditional `UPDATE ... WHERE next_run_at <= now()` — PostgreSQL row-level locking guarantees a losing concurrent claim returns zero affected rows, not a race
- One real GCP Cloud Scheduler job (`sniff-scheduler-tick`, `*/5 * * * *`) as the single external trigger

`apscheduler` was removed from `pyproject.toml` — it was never needed for this design.

**This is the planned approach being corrected because deployment context changed it.** ADR-003 was correct when it was written (Session 01, before Cloud Run was chosen). Session 15 superseded it.

### Sub-Agent Parallelism With Explicit Coordination Risk
Three background sub-agents worked concurrently on `app/dashboard/page.tsx` for different reasons:
1. Mounting `FrictionHeatmap`
2. Adding the Trends tab
3. Adding a Schedules nav link

Bob flagged this as a genuine coordination risk mid-session: each agent patching the same file. In practice, the patches did not touch the same lines and stacked cleanly. But the session summary explicitly notes: **running three agents against one shared file is an avoidable design choice**, not something to repeat carelessly. The lesson was documented, not glossed over.

### Live Production Verification as a Mandatory Step
Bob's verification process for scheduled runs was more than unit tests:
1. Created a real 5-minute schedule against `https://example.com` in the production Supabase instance
2. Watched it through several real Cloud Scheduler ticks
3. Confirmed: `next_run_at` advances correctly, no double-firing, busy-guard applies
4. Deleted the test schedule after proof

This is the principle: **scheduled jobs cannot be proven correct by mocked tests alone**. The atomicity of the PostgreSQL claim needs to be verified against a real Postgres transaction log, not a mock. Bob did the live test, documented the result, then cleaned up.

### Debugging Visual Artefacts: DOM/SVG Inspection
A chart line appeared broken (a tiny stub instead of a full connecting line) during visual verification. Bob did not immediately file a bug. Instead, it inspected the actual SVG path in the DOM and then waited for a longer post-render delay. The path was complete; the visual artefact was Recharts' mount-in animation caught mid-draw by the screenshot timing.

**Lesson**: do not trust a screenshot's first impression for animated components. Verify against the actual DOM state. This avoided a false-positive "bug fix" that would have changed correct code.

---

## Key Bob Discipline Applied

**Verify claims about the current architecture, don't assume.** The multi-instance duplicate-scheduler risk was confirmed by running `gcloud run services describe`, not hypothesised. If that check had shown `maxScale: 1`, APScheduler in-process would have been fine. Architecture decisions must be grounded in the actual deployment configuration, not the planned one.
