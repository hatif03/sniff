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
- **AI decisioning**: Amazon Bedrock Runtime (multimodal capable model)
- **Agent framework (optional)**: Strands Agents (Python) for tool orchestration/RAG/memory patterns
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

### D) `Agent Service` (Bedrock Decision Brain)
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
Hybrid incident triage layer.

Responsibilities:
- Combine deterministic signals + LLM interpretation.
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

## 8) Why Agent Cloud + Worker Local

### Use Bedrock for Agent Service
- Organizers provided Bedrock resources.
- Strong story alignment with sponsor ecosystem.
- Centralized model calls, model swap flexibility.

### Keep Execution Worker local
- Reliable browser/device control.
- Fast debug loops.
- Lower complexity than remote browser orchestration in v1.

Result:
- Best balance of AI sophistication and operational reliability.

### Agent Runtime Decision (v1)
- Treat the "agent" as a bounded decision function: `Observation -> AgentDecision`.
- Keep run control/state machine authority in `Run Orchestrator`, not in the LLM framework.
- If using Strands, use it inside `agent/` as an implementation detail; do not let it own browser execution lifecycle.
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
- Bedrock region/model
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
    bedrock_client.py
    decision_service.py
    prompts/
    strands_agent.py
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
- Use **Bedrock Agent Service** for persona-driven thinking, with optional **Strands Python** if it accelerates agent-tool workflows.
- Use **Diagnosis Engine** for clear owner-ready incident reports.
- Nail one powerful live demo path end-to-end.

This architecture maximizes:
- implementation speed
- live demo reliability
- judge-visible AI differentiation

---

## 16) Supporting Decision Document

- `STRANDS_BEDROCK_REPORT.md` is a **supporting technical decision report** for the `Agent Service` layer.
- It informs framework/provider tradeoffs (Strands vs SDK-only), Bedrock constraints, RAG/memory integration options, and deployment caveats.
- It does not change control-plane ownership: the orchestrator remains the runtime authority in this architecture.
