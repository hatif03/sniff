# Sniff Product Requirements Document (PRD)

## 1. Document Control

- **Product Name:** Sniff
- **Version:** v1.0 (Hackathon PRD)
- **Date:** February 6, 2026
- **Owner:** Solo Builder
- **Status:** Approved for implementation

---

## 2. Executive Summary

Sniff is a CLI-first autonomous mystery shopper for mobile/web signup journeys. It simulates realistic user behavior, detects signup friction, diagnoses probable root causes, and escalates issues to Slack with actionable evidence.

This PRD is intentionally scoped for a solo hackathon build in ~8–9 implementation hours plus demo polish. The strategy is to deliver one deeply reliable end-to-end flow (not many shallow features) that visibly demonstrates AI value.

---

## 3. Problem Statement

Teams lose users when signup flows fail or create friction. Most bugs are discovered late through manual QA cycles or user complaints. Manual testing does not scale to:
- Device/browser/network combinations
- 24/7 coverage
- UX confusion patterns
- Fast triage to the correct owner

The result is delayed detection, unclear ownership, and conversion loss.

---

## 4. Product Vision

Enable teams to catch signup friction before real users are impacted by running an AI-driven test agent that:
1. Navigates flows like a human
2. Understands when/why it is blocked
3. Escalates with evidence and severity instantly

---

## 5. Goals and Success Criteria

## 5.1 Primary Goals (Hackathon MVP)

- Execute one mobile signup journey autonomously.
- Use an AI decision loop (Bedrock-backed) rather than static scripts only.
- Produce machine-readable diagnosis (`Backend`, `UX/Content`, `Performance`, `Integration`).
- Trigger a real-time Slack alert with severity and evidence.
- Provide reproducible run artifacts and reasoning timeline.

## 5.2 Success Metrics (Hackathon)

- **Demo pass rate:** 3/3 successful end-to-end demo runs in local rehearsal.
- **Detection-to-alert latency:** ≤ 10 seconds from failure detection to Slack post.
- **Diagnosis completeness:** 100% of failed runs include root cause + severity + repro steps.
- **Run trace quality:** 100% runs include screenshot trail and step log.

---

## 6. Non-Goals (Strict for v1)

- Multi-tenant SaaS dashboard
- Production environment testing
- Full cross-industry journey packs
- CAPTCHA breaking / unsafe auth bypasses
- Large-scale distributed orchestration
- Fancy marketing website

---

## 7. Users and Personas

## 7.1 Primary User

- **Hackathon Judge / QA Lead / Engineer**
- Wants to see autonomous detection + practical triage value quickly.

## 7.2 Persona Profiles Used by Agent

Persona behavior profiles drive how the agent explores UI:
- `confused_first_time_user`
- `impatient_user`
- `careful_user`

Persona setup is created with `Sniff personas add`, where minimal natural-language input is expanded to structured persona JSON using an LLM-assisted normalization step.

---

## 8. Product Scope

## 8.1 In Scope (MVP)

- Bun + TypeScript CLI package (`Sniff`)
- Commands:
  - `Sniff init`
  - `Sniff personas add|list|test`
  - `Sniff run`
  - `Sniff report`
  - `Sniff alert test`
  - `Sniff demo`
- Playwright-based mobile emulation worker
- Bedrock-based decision service
- Diagnosis engine (hybrid rule + LLM interpretation)
- Artifact and report generation
- Slack webhook alerting

## 8.2 Out of Scope (MVP)

- Native-app automation with Appium (post-MVP)
- BrowserStack/device farm integration (post-MVP)
- Hosted analytics UI (post-MVP)

---

## 9. Functional Requirements

## 9.1 CLI and Configuration

- FR-1: System must initialize project config through `Sniff init`.
- FR-2: System must store Bedrock model/region, staging URL, Slack webhook, and defaults.
- FR-3: System must support run-time overrides (`--persona`, `--device`, `--network`, `--url`).
- FR-4: System must fail fast on missing required config.

## 9.2 Persona Management

- FR-5: `Sniff personas add` must accept short natural-language persona input.
- FR-6: System must convert input into validated persona JSON schema.
- FR-7: User must confirm/edit generated persona before saving.
- FR-8: `Sniff run` must load a saved persona profile by name.

## 9.3 Run Orchestration

- FR-9: System must run a deterministic state machine for each execution.
- FR-10: Orchestrator must enforce guardrails (max steps, retries, timeout).
- FR-11: System must persist step-by-step action logs.

## 9.4 Execution Worker (Tools Layer)

- FR-12: Worker must launch mobile browser context with selected device profile.
- FR-13: Worker must expose action tools: `tap`, `type`, `scroll`, `wait`, `back`, `screenshot`.
- FR-14: Worker must capture observations (URL, visible text hints, timing, errors).
- FR-15: Worker must return structured execution results for each action.

## 9.5 Agent Service (Bedrock)

- FR-16: Agent service must receive observation + goal + persona + recent history.
- FR-17: Agent service must return strict JSON action decisions.
- FR-18: Agent service must include confidence and reasoning summary per step.
- FR-19: System must reject malformed AI output and retry with repair strategy.

## 9.6 Diagnosis and Severity

- FR-20: On fail/stuck/timeout, diagnosis engine must classify root cause.
- FR-21: Severity must be assigned as `P0|P1|P2|P3`.
- FR-22: Diagnosis output must include likely owner and repro steps.

## 9.7 Evidence and Reporting

- FR-23: Each run must generate an evidence bundle in `artifacts/<runId>/`.
- FR-24: Evidence must include screenshots, action timeline, diagnosis JSON, and summary report.
- FR-25: `Sniff report` must print a concise run summary and artifact locations.

## 9.8 Alerting

- FR-26: On diagnosed failure, system must send Slack alert with rich formatting.
- FR-27: Alert must include severity, root cause, top repro steps, and evidence references.
- FR-28: `Sniff alert test` must validate webhook and payload formatting.

---

## 10. Non-Functional Requirements

- NFR-1: End-to-end run should complete within practical demo time (target ≤ 5 minutes).
- NFR-2: Failure-to-alert latency target ≤ 10 seconds.
- NFR-3: System must be reliable for repeated demo runs (no manual recovery between runs).
- NFR-4: Logs must avoid exposing secrets/PII.
- NFR-5: System must only target allowed staging domains.
- NFR-6: CLI UX must be clear, with explicit actionable error messages.

---

## 11. Architecture Alignment

This PRD maps directly to the architecture in `ARCHITECTURE.md`:
- CLI control plane
- Run orchestrator state machine
- Local execution worker (tools)
- Bedrock agent decision service
- Diagnosis engine
- Evidence/report module
- Slack alert module

Deployment model for MVP:
- Local runtime for CLI, orchestration, worker, diagnosis, alerting
- Cloud Bedrock calls for AI reasoning

---

## 12. Data Contracts (MVP Schemas)

## 12.1 Observation

- `runId`
- `step`
- `timestamp`
- `url`
- `screenshotPath`
- `visibleText[]`
- `timing`
- `consoleErrors[]`
- `networkSignals[]`
- `lastActionResult`

## 12.2 AgentDecision

- `action`
- `target`
- `inputText?`
- `reasoningSummary`
- `confidence`
- `fallbackAction?`

## 12.3 DiagnosisResult

- `rootCause`
- `severity`
- `likelyOwner`
- `reproSteps[]`
- `suggestedFix`
- `evidenceRefs[]`

---

## 13. CLI Command Requirements

## 13.1 `Sniff init`

- Must prompt for required environment settings.
- Must validate Bedrock model + region configuration shape.
- Must persist config to local project config file.

## 13.2 `Sniff personas add`

- Must accept minimal persona text.
- Must run LLM-assisted normalization.
- Must present preview and confirmation.
- Must save JSON profile with unique persona name.

## 13.3 `Sniff run`

- Must validate persona existence and runtime config.
- Must execute the full state machine.
- Must output final status and report pointer.

## 13.4 `Sniff report`

- Must retrieve and display run outcome, diagnosis, key timestamps, artifact path.

## 13.5 `Sniff demo`

- Must run deterministic demo mode optimized for judge walkthrough.
- Must include known-failure path to guarantee visible alerting narrative.

---

## 14. Core User Flows

## 14.1 First-Time Setup

1. User runs `Sniff init`
2. Provides staging URL, Bedrock details, webhook
3. Config saved and validated

## 14.2 Persona Creation

1. User runs `Sniff personas add`
2. Enters short phrase (e.g., “confused first-time user, low patience on slow network”)
3. LLM returns structured profile
4. User confirms and saves

## 14.3 Test Run and Escalation

1. User runs `Sniff run --persona confused_first_time_user --device iphone13 --network 3g`
2. Agent navigates flow via worker tools
3. Failure detected and diagnosed
4. Slack alert sent with evidence
5. User checks `Sniff report`

---

## 15. Edge Cases and Error Handling

- Invalid webhook URL -> clear validation error
- Bedrock timeout / malformed response -> bounded retry + fallback failure status
- Agent loops on same screen -> stuck detection using dwell + repeated action signature
- Missing persona profile -> suggest available profiles and exit
- Navigation outside allowlist domain -> block and fail safely

---

## 16. Risk Register and Mitigations

- **Risk:** Model output unpredictability  
  **Mitigation:** Strict JSON schema + parser/repair retry + bounded action set.

- **Risk:** Demo flakiness  
  **Mitigation:** Deterministic `Sniff demo` mode and rehearsed staging path.

- **Risk:** Scope overload for solo build  
  **Mitigation:** Lock MVP scope to one flow + core diagnosis + one alert channel.

- **Risk:** Misdiagnosis confidence  
  **Mitigation:** Include confidence and “likely cause” language, not absolute claims.

---

## 17. Instrumentation and Metrics

Each run should track:
- Run start/end timestamps
- Step count and retries
- Screen dwell times
- Failure point and diagnosis latency
- Alert delivery status
- Agent confidence distribution

Metrics should be available in run summary and stored with run metadata.

---

## 18. Security and Compliance Requirements

- Must run only against staging/test environments.
- Must store secrets in environment/config, never in logs.
- Must redact sensitive form values from exported reports where possible.
- Must provide domain allowlist enforcement in run configuration.

---

## 19. Implementation Milestones (Solo Plan)

## M1: Foundation
- CLI scaffold
- Config + init
- Persona storage and schema

## M2: Execution Loop
- Playwright worker tools
- Orchestrator state machine
- Bedrock decision integration

## M3: Diagnosis and Alert
- Diagnosis classifier + severity mapping
- Artifact and report builder
- Slack alert module

## M4: Demo Hardening
- Deterministic demo mode
- Error handling polish
- Rehearsal and final script

---

## 20. Acceptance Criteria (Definition of Done)

Product is MVP-complete when all are true:
- AC-1: `Sniff init` completes and saves valid config.
- AC-2: `Sniff personas add` creates a usable validated profile from minimal input.
- AC-3: `Sniff run` autonomously executes one staging signup journey.
- AC-4: On failure, diagnosis + severity + repro steps are generated.
- AC-5: Slack alert is posted with evidence references.
- AC-6: `Sniff report` outputs run summary with artifact path.
- AC-7: Demo run is repeatable with high reliability.

---

## 21. Post-Hackathon Backlog (Prioritized)

1. Real-device support via BrowserStack/Appium
2. Scheduled continuous monitoring mode
3. Multi-language and locale regression packs
4. Issue similarity clustering across run history
5. Hosted team dashboard and assignment workflows

---

## 22. Final Scope Lock

To maximize hackathon win probability:
- Build one robust end-to-end path.
- Show unmistakable AI decisioning + diagnosis.
- Deliver instant actionable escalation.
- Avoid non-essential UI/distributed complexity until after judging.

