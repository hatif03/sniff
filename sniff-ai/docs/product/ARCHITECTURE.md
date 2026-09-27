# Sniff Architecture (Hackathon Solo Strategy)

## 1) Objective

Build an **Autonomous Mystery Shopper** that can:
- Navigate a mobile signup flow using AI-driven decisions (not hard-coded selectors only).
- Detect signup friction/failures.
- Diagnose likely root cause and severity.
- Escalate instantly to Slack with evidence.

This architecture is optimized for:
- **Solo execution**
- **8–9 hour build + demo window**
- **High reliability during live judging**

---

## 2) Core Architecture Choice

Use a **modular monolith** with a CLI-first product:
- One codebase, one runtime boundary for most logic.
- Clear internal modules (agent, worker, diagnosis, alerting).
- No distributed microservices in hackathon v1.

> **Current status**: this was the hackathon-era decision. The CLI (Section
> 10) still works and remains a secondary/developer-facing tool, but the web
> dashboard (`sniff-web`) is now the primary way users trigger and watch
> runs/audits, via a FastAPI layer in front of the same modular monolith -
> see `docs/product/SAAS_ROADMAP.md`.

Why:
- Faster to build/debug alone.
- Fewer moving parts and fewer demo-time failures.
- Still clean enough to evolve post-hackathon.

---

## 3) Technology Stack

- **Runtime / package**: Python 3.11+ (`uv` or `pip` workflow)
- **Language**: Python
- **CLI**: `typer` (or `click`) + interactive prompts (`questionary`/`InquirerPy`)
- **Mobile execution**: Playwright with mobile emulation (iPhone/Android profiles)
- **AI decisioning (vision-capable)**: Gemini via Vertex AI (multimodal, Application Default Credentials - not Bedrock)
- **AI decisioning (text-only)**: k2-horizon via ifm.ai (OpenAI-compatible), used for goal enhancement/planning/persona reviews
- **Fast decision tier (optional)**: Typesafe AI's Jev - see Section 7A
- **Persistence**: local SQLite + filesystem artifacts
- **Notifications**: Slack Incoming Webhook (rich blocks)

Optional after MVP:
- Appium / BrowserStack for real-device coverage
- Supabase for hosted run history
- Bun wrapper CLI for distribution/UX if needed

Implementation note:
- For hackathon speed and reliability, keep a **single Python runtime** for CLI, orchestrator, worker, and agent service.
- Avoid cross-runtime Bun<->Python IPC in v1 unless there is a strict product requirement for Bun-first UX.

---

## 4) High-Level Component Model

### A) `Sniff CLI` (Control Plane)
User-facing package and command surface:
- `Sniff init`
- `Sniff run`
- `Sniff personas ...`
- `Sniff report`
- `Sniff alert test`
- `Sniff demo`

Responsibilities:
- Parse command intent and config.
- Start and supervise run orchestration.
- Present status and final summaries.

### B) `Run Orchestrator` (State Machine + Guardrails)
Central runtime coordinator.

Responsibilities:
- Maintains run state and transitions.
- Calls Agent Service for decisions.
- Calls Execution Worker to perform actions.
- Triggers Diagnosis Engine on fail/stuck/timeout.
- Emits report + alert.

### C) `Execution Worker` (Tools Layer)
The deterministic action/sensing engine.

Responsibilities:
- Own Playwright session and mobile context.
- Execute tool actions (`tap`, `type`, `scroll`, `wait`, `screenshot`).
- Capture observations (visible text, timings, status signals, errors).
- Return structured action results.

This is effectively the **agent’s tool interface**.

### D) `Agent Service` (Gemini Decision Brain)
Decision-making brain with persona + context.

Responsibilities:
- Interpret current UI state, screenshot, and goal.
- Decide next action in strict JSON schema.
- Apply persona behavior policy (confused/careful/impatient/etc.).
- Suggest retries/alternate paths with confidence.

Boundary:
- Agent does **not** directly control browser.
- Agent only returns decisions.

### E) `Diagnosis Engine` (Root Cause + Severity)
Fully deterministic incident triage layer (Tier 1 - see Section 7A). No
model call of any kind; root cause, severity, and suggested fix are all
rule trees over extracted signals (HTTP errors, timeouts, console errors).

Responsibilities:
- Apply deterministic rules over extracted signals.
- Classify likely root cause:
  - Backend
  - UX/Content
  - Performance
  - Integration
- Assign severity P0–P3.
- Produce repro steps and ownership routing.

### F) `Evidence & Reporting`
Run artifacts and summaries.

Responsibilities:
- Store screenshots, traces, run logs, diagnosis JSON.
- Create report payload for CLI and Slack.
- Keep auditable trail for judges.

### G) `Alert Service`
Real-time escalation channel.

Responsibilities:
- Send rich Slack alert with:
  - severity
  - root cause guess
  - evidence links/paths
  - top repro steps
  - owner tag

---

## 5) Runtime Flow (End-to-End)

1. User executes:
   - `Sniff run --persona confused --goal "Complete signup with document upload" --device iphone13 --network 3g`
2. CLI loads config + flow target + previously saved persona profile + run goal.
3. Orchestrator enters `SETUP`.
4. Execution Worker boots mobile browser context and opens staging signup URL.
5. Orchestrator enters decision loop:
   - Worker captures observation bundle.
   - Agent Service decides next action JSON.
   - Worker executes action.
   - Orchestrator records step result.
6. If goal reached: mark run success and report.
7. If stuck/fail/timeout:
   - Diagnosis Engine classifies cause + severity.
   - Evidence bundle finalized.
   - Alert Service posts Slack message.
8. CLI prints terminal summary + run id + artifact location.

---

## 6) State Machine

Recommended orchestrator states:
- `SETUP`
- `NAVIGATE`
- `ACTION_EXECUTION`
- `EVALUATE_PROGRESS`
- `STUCK_DETECTED`
- `DIAGNOSE`
- `ALERT`
- `REPORT`
- `DONE`

Guardrails:
- max steps per run
- max retries per intent
- max dwell time per screen
- hard timeout per run
- allowed action whitelist

These guardrails prevent infinite loops and improve demo stability.

---

## 7) Agent Thinking Model (Persona-Driven)

The Agent Service should “think” within bounded policy:
- Input:
  - current screenshot
  - visible text + element hints
  - recent action history
  - run objective
  - persona profile
  - user-defined run goal
- Output:
  - `next_action`
  - `reasoning_summary`
  - `confidence`
  - `fallback_action`

Persona examples:
- `confused_first_time_user`
  - explores more, hesitates, may misinterpret copy
- `impatient_user`
  - low tolerance for delays, early abandonment
- `careful_user`
  - reads labels, validates before submit

Important:
- Persist reasoning summaries per step.
- Show this timeline in demo; judges love transparent intelligence.
- Persona profiles are created during `Sniff personas add` and reused in `Sniff run`.
- Each run must include a user-defined goal (`--goal` or interactive prompt), which is passed to the agent and used in completion checks.

---

## 7A) Three-Tier Decision Architecture (Deterministic / Jev / Reasoning)

Added post-hackathon. There isn't much published literature on Typesafe
AI's "Jev" model specifically (it's new), so this design is grounded in
named patterns from two references instead: the Google Developers Blog's
"4 Engineering Patterns Behind the Strongest AI Agents Challenge
Submissions" and Google Cloud's "Choose a design pattern for your agentic
AI system," plus Typesafe's own documented "Speculative Fan-Out" and
"Confidence-Gated Routing" concepts. **Typesafe's own docs do not claim a
three-tier architecture** - they describe a two-way split (Jev vs. full
reasoning LLMs); the tiering below, including code as its own tier, is this
project's synthesis, not something to attribute to Typesafe.

**Tier 1 (deterministic code)** - unchanged: guardrail checks, the Diagnosis
Engine (Section 4E), `DecisionSanitizer`. No model call, none needed.

**Tier 2 (Jev, "System One")** - Jev (`src/agent/jev_client.py`) is fast
(docs claim 70-500ms) but text/structured-input only, no vision, no free
text generation - three typed primitives: `choice` (pick from an option
set), `score` (position on a rubric), `noul` (binary yes/no probability).
Because it can't see the screenshot the way Tier 3 does, it's used in three
roles (`src/agent/tier_router.py`) rather than as a drop-in Tier 3
replacement:

| Role | Named pattern | What it does | Where |
|---|---|---|---|
| Goal-reached check | ReAct's "Observation" step | Backstop for the keyword pre-filter that decides if the run succeeded - text-only, fixes a real false-negative gap in the old pure-keyword check | `RunOrchestrator._is_goal_reached` |
| Context enrichment | Multi-Agent Parallel / Speculative Fan-Out | A batch of cheap typed probes (screen type, error-visible, clutter score) computed off visible text before the Tier 3 call, folded into its prompt so it doesn't re-derive screen classification from scratch every step | `DecisionService.get_decision` |
| Decision critique | Generator-Critic / Review-Critique | A cheap sanity check on a Tier 3 decision before execution; a low-confidence critique is routed through the *existing* repair-retry mechanism (same one used for schema-validation failures), not a new parallel retry path | `DecisionService._attempt_decision` |

Every role degrades to today's Tier-1/Tier-3-only behavior the instant Jev
is disabled (the default), unavailable, or errors - nothing changes for
anyone without a Typesafe API key.

**Not implemented - Phase 2**: a *Tiered Routing* shortcut (the Google
blog's own name for resolving simple cases before spending tokens on the
expensive model) that would skip the Tier 3 call entirely on obvious steps,
building the `AgentDecision` straight from Jev's `choice()` output. This
needs Jev to name a concrete target element, which needs a structured
candidate-element list `Observation` doesn't expose yet (`visibleText` is
just strings) - a real prerequisite (extending the Playwright worker's
extraction), not a corner to cut silently. `TierRouter` is structured so
this slots in later without a redesign.

**Tier 3 (Gemini)** - unchanged in shape from the original Bedrock design,
the existing vision call, just given better inputs (Tier 2 enrichment) and
one more sanity check (Tier 2 critique) around it, and now backed by Gemini
via Vertex AI instead of Bedrock (see Section 8).

**Jev's real API, verified live**: `JevClient` targets the real endpoint
(`POST https://api.typesafe.ai/v1/systemone`, confirmed against
`docs.typesafe.ai/api.md` and a live smoke-test call) - one unified call
batching any mix of Choice/Score/Noul questions against a shared `state`,
not the three separate endpoints an earlier draft guessed at. `TierRouter`
is enabled behind `TYPESAFE_ENABLED` and degrades cleanly to Tier-1/Tier-3
behavior on any error.

---

## 7B) Web-First API and Persistence Layer

The product's primary interface is the web dashboard (`sniff-web`), not the CLI - this section documents how a browser actually triggers and watches a run/audit, and where the data ends up.

**Backend (`sniff-ai/src/api/main.py`)**: a FastAPI app exposing `POST /runs`, `POST /audits`, `POST /experiments`, `GET /runs/{run_id}`, `GET /audits/{audit_id}`, `GET /audits/{audit_id}/images/{filename}`, `POST /site-audits`, `GET /site-audits/{site_audit_id}` (session 16 - whole-site crawl, see below), `POST /schedules`/`GET /schedules`/`PATCH /schedules/{id}`/`DELETE /schedules/{id}`, `POST /internal/scheduler/tick` (session 15 - recurring runs, ticked by an external Cloud Scheduler job rather than an in-process scheduler, since the service autoscales across multiple instances), and `GET /status` (liveness, no auth - deliberately not `/healthz` or `/`, both reserved paths on Cloud Run's default `*.run.app` domain). Every other route is gated by a single shared Bearer token (`SNIFF_API_TOKEN`) - Phase 1 scope, not real per-user auth (see `SAAS_ROADMAP.md` Section 1). Runs/audits/site-audits execute as FastAPI `BackgroundTasks` against in-process dicts (`RUN_STORE`/`AUDIT_STORE`/`SITE_AUDIT_STORE`) that track *live* status while work is in flight - this in-process store is lost on process restart by design, which is fine because it only ever needs to survive the seconds-to-minutes (or, for a whole-site crawl, up to the `site_audit_hard_timeout`) a request takes, not act as the system of record.

**Whole-site audit (session 16)**: `SiteAuditOrchestrator` (`src/core/site_audit_orchestrator.py`) discovers a site's pages via `sitemap.xml` plus same-origin link-following (`src/core/site_crawl.py`), optionally logs in once (or accepts a pasted Playwright `storage_state`) and reuses that one authenticated browser session for every page it crawls, then runs the same per-page audit pipeline `AuditOrchestrator` already used for a single page (extracted into `run_audit_on_page` so both paths share it). Each crawled page is a normal row in the `audits` table (tagged with a nullable `site_audit_id` FK) - `GET /audits/{audit_id}` and its image endpoint serve per-page proof unchanged, no separate per-page API. A `CrawlManifest` records audited/skipped/failed for every URL considered, persisted to the `site_audits` table.

**Frontend proxy (`sniff-web/app/api/backend/**`)**: Next.js Route Handlers that forward to the FastAPI backend server-side, attaching `SNIFF_API_TOKEN` there - the browser never sees the secret, only calls same-origin paths. `/dashboard/new-run` posts a run, audit, or whole-site audit through this proxy and polls for live status.

**Persistence (Supabase/Postgres)**: once a run, audit, or site-audit *completes* (and, for a site-audit, incrementally as each page finishes), its result is uploaded to Supabase (`SupabaseUploader.upload_run`/`upload_audit`, `SiteAuditStore`, `ScheduleStore` in `src/integrations/supabase_client.py`) - `runs`, `observations`, `actions`, `diagnoses`, `agent_reasoning`, `persona_reviews`, `audits`, `site_audits`, and `schedules` tables, each with a public-read RLS policy (`USING (true)`). This is the actual system of record for anything that's finished: the dashboard's list views query these tables directly from the browser via the Supabase anon key, not through the FastAPI backend. Public-read is deliberate for this phase (no auth exists yet, everyone can see every run/audit) - see `SAAS_ROADMAP.md` Section 1 for what real per-user auth (`auth.uid()`-scoped RLS) looks like later.

---

## 8) Why Agent Cloud + Worker Local

### Use Gemini + k2-horizon for Agent Service
- Gemini (Vertex AI) is the only one of the two available providers with
  documented multimodal/vision input - required for the per-step screenshot
  + text navigation decision. Auth via Application Default Credentials, no
  API key to manage.
- k2-horizon (ifm.ai) is OpenAI-compatible, text-only, and is used for
  goal enhancement, next-action planning, and persona reviews - none of
  which need vision, so they're cheaper/faster on a dedicated text model
  than sharing Gemini's vision-capable path.
- Centralized model calls per tier, model swap flexibility (both clients
  share the same `invoke()`/`invoke_with_json_response()` interface).

### Keep Execution Worker local
- Reliable browser/device control.
- Fast debug loops.
- Lower complexity than remote browser orchestration in v1.

Result:
- Best balance of AI sophistication and operational reliability.

### Agent Runtime Decision (v1)
- Treat the "agent" as a bounded decision function: `Observation -> AgentDecision`.
- Keep run control/state machine authority in `Run Orchestrator`, not in the LLM framework.
- Keep RAG/memory behind explicit tools so behavior remains auditable and guardrailed.

---

## 9) Data Contracts (Suggested)

### `Observation`
- `runId`
- `step`
- `timestamp`
- `url`
- `screenshotPath`
- `visibleText[]`
- `timing` (ttfb/domReady/actionLatency)
- `consoleErrors[]`
- `networkEvents[]`
- `lastActionResult`

### `RunIntent`
- `personaName`
- `goal` (required, user-provided at run time)
- `successCriteria` (optional, derived from goal or user override)

### `AgentDecision`
- `action` (`tap` | `type` | `scroll` | `wait` | `back` | `abort`)
- `target` (coordinates/text/selectorHint)
- `inputText` (optional)
- `reasoningSummary`
- `confidence` (0–1)
- `fallbackAction` (optional)

### `DiagnosisResult`
- `rootCause`
- `severity` (`P0` | `P1` | `P2` | `P3`)
- `evidence`
- `likelyOwner`
- `reproSteps[]`
- `suggestedFix`

---

## 10) CLI Package Design

### `Sniff init`
Interactive setup:
- staging URL
- GCP project/region for Gemini, ifm.ai key for k2-horizon
- Slack webhook
- default persona/device/network
- owner routing map

### `Sniff run`
Launch autonomous run with overrides.

Goal behavior:
- Require a run goal via `--goal` or interactive prompt.
- Use goal text as primary objective for agent decisions and completion evaluation.
- Optionally allow persona-level default goal template, but run-time goal always takes precedence.

### `Sniff personas`
- list/add/test persona profiles.

### `Sniff personas add` (LLM-assisted persona builder)
Flow:
- User provides minimal persona intent in CLI (short natural language).
- LLM expands this into normalized persona JSON.
- CLI shows preview and asks for confirmation/edit.
- Confirmed profile is saved under `src/personas/` (or configurable persona store).

Goal handling:
- Persona profile may include `default_goal_template` (optional).
- Final active goal is selected by the user at `Sniff run` time.

Why:
- Minimal typing for users.
- Consistent, schema-safe persona configs.
- Better repeatability across runs.

### `Sniff report`
- summarize by run id and print artifact references.

### `Sniff alert test`
- verify Slack payload channel + formatting.

### `Sniff demo`
- deterministic mode for judge presentation.

---

## 11) File/Module Layout (Recommended)

```txt
src/
  cli/
    commands/
      init.py
      run.py
      report.py
      personas.py
      alert.py
      demo.py
    main.py
  core/
    orchestrator.py
    state_machine.py
    config.py
  executor/
    playwright_worker.py
    tool_adapter.py
  agent/
    gemini_client.py
    k2horizon_client.py
    jev_client.py
    decision_service.py
    prompts/
  diagnosis/
    classifier.py
    severity.py
    owner_routing.py
  evidence/
    artifact_store.py
    report_builder.py
  alerts/
    slack.py
  personas/
    confused_first_time_user.json
    impatient_user.json
    careful_user.json
data/
  Sniff.db
artifacts/
  <runId>/
```

---

## 12) Demo-Winning Scope (Strict)

Build this first and polish it hard:
- One signup flow on staging.
- Two personas.
- Three diagnosis classes minimum.
- Full evidence + one clean Slack escalation.
- Terminal replay of step-by-step reasoning.

Do **not** prioritize:
- multi-industry templates
- fancy frontend website
- heavy distributed deployment

---

## 13) Security, Safety, and Compliance

- Test only on staging URLs.
- Do not automate production credentials.
- Keep secrets in `.env` / secure local config.
- Sanitize logs to avoid leaking PII.
- Disable risky autonomous actions outside allowed domains.

---

## 14) Post-Hackathon Evolution Path

After demo success:
- Add Appium / BrowserStack real-device matrix.
- Add locale packs and country flow scheduling.
- Add issue similarity detection across runs.
- Add hosted dashboard for team triage.
- Add CI/nightly execution mode.

---

## 15) Final Recommendation

For a solo hackathon win:
- Use a **Python-first CLI and runtime**.
- Keep **Execution Worker local** and deterministic.
- Use **Gemini + k2-horizon Agent Service** for persona-driven thinking (vision and text-only reasoning split across tiers).
- Use **Diagnosis Engine** for clear owner-ready incident reports.
- Nail one powerful live demo path end-to-end.

This architecture maximizes:
- implementation speed
- live demo reliability
- judge-visible AI differentiation

---

## 16) Supporting Decision Document

- `STRANDS_BEDROCK_REPORT.md` is a **historical decision report** for the `Agent Service` layer from when it ran on AWS Bedrock/Strands - kept for context on that tradeoff, superseded by the Gemini + k2-horizon provider swap (Section 8).
- It does not change control-plane ownership: the orchestrator remains the runtime authority in this architecture.
- `MARKET_RESEARCH.md` covers the competitive landscape and customer segments referenced when prioritizing the Post-Hackathon Evolution Path (Section 14).
