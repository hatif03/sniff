# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Sherlock** is an autonomous mystery shopper system that tests mobile/web signup flows using AI-driven navigation and diagnosis. The system simulates real user behavior, detects friction points, diagnoses root causes, and escalates issues via Slack alerts.

**Current Status**: Planning phase - architecture and requirements defined, implementation not yet started.

**Tech Stack**: Python 3.11+, Playwright (mobile emulation), AWS Bedrock (AI decisions), optional Strands Agents framework.

## Architecture

### Core Design Pattern: Modular Monolith

Single Python runtime with clear internal module boundaries. All components run in one process to minimize demo-time failures and maximize solo development speed.

### Component Hierarchy

```
CLI (Control Plane)
  ↓
Run Orchestrator (State Machine + Guardrails)
  ↓
├── Agent Service (Bedrock) → returns decisions only
├── Execution Worker (Playwright) → executes actions, captures observations
├── Diagnosis Engine → classifies failures, assigns severity
└── Alert Service (Slack) → escalates with evidence
```

**Critical Boundaries**:
- Agent Service never directly controls the browser - it only returns `AgentDecision` objects
- Run Orchestrator maintains state machine authority, not the LLM
- Execution Worker owns Playwright session lifecycle
- If using Strands framework, keep it confined to `src/agent/` as an implementation detail

### State Machine Flow

```
SETUP → NAVIGATE → ACTION_EXECUTION → EVALUATE_PROGRESS
  ↓
STUCK_DETECTED → DIAGNOSE → ALERT → REPORT → DONE
```

**Guardrails** (prevent infinite loops):
- Max steps per run
- Max retries per intent
- Max dwell time per screen
- Hard timeout per run
- Action whitelist

## Planned Module Structure

```
src/
  cli/
    commands/          # init, run, report, personas, alert, demo
    main.py
  core/
    orchestrator.py    # State machine + run coordination
    state_machine.py
    config.py
    models.py
  agent/
    bedrock_client.py  # AWS Bedrock integration
    decision_service.py
    strands_agent.py   # Optional: Strands framework wrapper
    prompts/
  executor/
    playwright_worker.py  # Browser automation + tool methods
    tool_adapter.py
  diagnosis/
    classifier.py      # Root cause classification
    severity.py        # P0-P3 severity assignment
    owner_routing.py
  evidence/
    artifact_store.py  # Screenshots, traces, logs
    report_builder.py
  alerts/
    slack.py          # Webhook integration
  personas/           # Persona JSON profiles
data/
  sherlock.db        # SQLite for run history
artifacts/
  <runId>/           # Per-run evidence bundles
```

## Key Data Contracts

### Observation (Worker → Agent)
```python
{
  "runId": str,
  "step": int,
  "timestamp": str,
  "url": str,
  "screenshotPath": str,
  "visibleText": list[str],
  "timing": {"ttfb": int, "domReady": int},
  "consoleErrors": list[str],
  "networkEvents": list[dict],
  "lastActionResult": dict
}
```

### AgentDecision (Agent → Orchestrator)
```python
{
  "action": "tap" | "type" | "scroll" | "wait" | "back" | "abort",
  "target": str,  # coordinates/text/selectorHint
  "inputText": str,  # REQUIRED when action == "type"
  "reasoningSummary": str,
  "confidence": float,  # 0-1
  "fallbackAction": dict | None
}
```

**Critical Validation**: When `action == "type"`, `inputText` is REQUIRED. Missing `inputText` should be treated as invalid decision.

### DiagnosisResult
```python
{
  "rootCause": "Backend" | "UX/Content" | "Performance" | "Integration",
  "severity": "P0" | "P1" | "P2" | "P3",
  "evidence": dict,
  "likelyOwner": str,
  "reproSteps": list[str],
  "suggestedFix": str
}
```

## CLI Commands (Planned)

### `sherlock init`
Interactive setup for:
- **Primary staging URL** - Default entry point for test runs (e.g., `https://staging.acme.com`)
- **Allowed domains** - Security allowlist to prevent accidental production runs (e.g., `["staging.acme.com", "auth-staging.acme.com"]`)
- Bedrock region/model
- Slack webhook
- Default persona/device/network
- Owner routing map

The primary staging URL becomes the default starting point for all `sherlock run` executions unless overridden.

### `sherlock personas add`
LLM-assisted persona builder:
1. User provides minimal natural language description
2. LLM expands to normalized persona JSON
3. CLI shows preview and asks for confirmation/edit
4. Saves to `src/personas/`

Personas may include optional `default_goal_template`, but final goal is always specified at run time.

### `sherlock run`
Launches autonomous test run.

**Required at runtime**: User-defined goal via `--goal` flag or interactive prompt. The goal drives agent decisions and completion evaluation.

**URL Handling**:
- Uses the **primary staging URL** configured during `sherlock init` by default
- Optional `--url` flag overrides the default for specific test scenarios
- URL is the **starting/entry point** - agent navigates from there based on the goal
- All navigation is validated against the allowed domains allowlist

Examples:
```bash
# Uses configured default staging URL (typical usage)
sherlock run --persona confused_first_time_user \
             --goal "Complete signup with document upload" \
             --device iphone13 \
             --network 3g

# Override starting URL for specific test scenario
sherlock run --url https://staging.acme.com/signup \
             --persona impatient_user \
             --goal "Complete signup with document upload" \
             --device iphone13 \
             --network 3g
```

**Journey Pattern**: The URL defines WHERE to start, the goal defines WHAT to accomplish. For example:
- URL: `https://staging.acme.com` (homepage)
- Goal: "Complete signup with document upload"
- Agent behavior: Finds signup button → navigates to signup flow → completes steps

This tests realistic user journeys, not just direct links to specific pages.

### `sherlock report`
Displays run summary with artifact references by run ID.

### `sherlock alert test`
Validates Slack webhook and payload formatting.

### `sherlock demo`
Deterministic mode for judge presentation with known-failure path to guarantee visible alerting.

## Persona System

**Behavior Profiles** shape agent exploration patterns:
- `confused_first_time_user` - explores more, hesitates, may misinterpret copy
- `impatient_user` - low tolerance for delays, early abandonment
- `careful_user` - reads labels thoroughly, validates before submit

**Storage**: JSON files in `src/personas/` with schema validation via Pydantic.

**Creation**: Via `sherlock personas add` with LLM normalization for consistency.

## Execution Worker Tool Interface

Browser automation tools exposed to Agent Service:

- `tap(target)` - Click/tap element
- `type(target, inputText)` - Focus and type text (inputText required)
- `scroll(direction)` - Scroll viewport
- `wait(duration)` - Explicit wait
- `back()` - Browser back button
- `screenshot()` - Capture current state

**Returns**: Structured `Observation` with visible text, timing, errors, and action result.

## Agent Service Implementation Notes

**Input**: Current observation + persona profile + run goal + recent action history

**Output**: Strict JSON `AgentDecision` schema

**Key Requirements**:
- Enforce JSON schema validation
- Implement bounded retry on malformed output
- Include confidence scores and reasoning summaries
- Persist reasoning timeline for demo transparency (judges love this)
- Apply persona behavior policies consistently

**Bedrock Integration**:
- Use organizer-provided Bedrock resources
- Support model swapping flexibility
- Handle timeouts with fallback strategies

**Optional Strands Framework**:
- If used, keep inside `src/agent/` only
- Do NOT let it own browser execution lifecycle
- Keep RAG/memory behind explicit tools for auditability

## Diagnosis Engine

**Hybrid approach**: Deterministic signals + LLM interpretation

**Root Cause Categories**:
- **Backend** - Server errors, API failures
- **UX/Content** - Confusing copy, unclear labels
- **Performance** - Timeouts, slow responses
- **Integration** - Document upload failures, third-party issues

**Severity Mapping**:
- **P0** - Blocking signup completion
- **P1** - Major friction, likely abandonment
- **P2** - Noticeable issue, workaround exists
- **P3** - Minor UX annoyance

**Output includes**: Repro steps, likely owner tag, suggested fix

## Slack Alerting

**Rich block format** with:
- Severity indicator
- Root cause classification
- Evidence links/paths
- Top reproduction steps
- Owner tag for routing

**Latency target**: ≤10 seconds from failure detection to alert post

## Development Workflow

### Dependency Management
Prefer `uv` for Python package management, fallback to `pip` if needed.

Required packages:
- `typer` - CLI framework
- `rich` - Terminal output formatting
- `pydantic` - Schema validation
- `playwright` - Browser automation
- `boto3` - AWS Bedrock client
- `httpx` - HTTP client for Slack webhooks
- `python-dotenv` - Environment configuration
- `questionary` - Interactive prompts

### Environment Configuration
Use `.env` for secrets (Bedrock credentials, Slack webhook URL). Never commit secrets or log sensitive data.

### Testing Strategy
Must target staging URLs only. Never automate against production environments.

## Critical Implementation Constraints

### Hackathon Scope (8-9 hours)
**Build ONE reliable end-to-end path**, not many shallow features.

**Priority sequence**:
1. End-to-end `sherlock run` with one signup journey
2. Persona-driven decision loop with strict JSON action schema
3. Failure diagnosis + P0-P3 severity
4. Evidence bundle + Slack alert
5. Deterministic `sherlock demo` path

**Explicitly out of scope for v1**:
- Multi-industry templates
- Fancy frontend website
- Heavy distributed deployment
- Real device testing (Appium/BrowserStack)
- Multi-tenant SaaS dashboard

### Demo Reliability Requirements
- **3/3 successful rehearsal runs** required before judging
- Avoid flakiness through deterministic demo mode
- Clear, actionable error messages for debugging
- No manual recovery needed between runs

### Security Boundaries
- Domain allowlist enforcement
- Sanitize logs to avoid PII leakage
- Disable risky autonomous actions outside allowed domains
- CAPTCHA/OTP handling out of scope for v1

## Related Documentation

- **ARCHITECTURE.md** - Full architectural specification and component details
- **CHALLENGE.md** - Original hackathon problem statement
- **IMPLEMENTATION_PLAN.md** - Phase-by-phase build tasks and checklist
- **PRODUCT_REQUIREMENTS.md** - Complete PRD with functional requirements and acceptance criteria
- **STRANDS_BEDROCK_REPORT.md** - Technical decision report on Agent Service layer framework tradeoffs
- **AGENT_README.md** / **AGENT_SETUP_GUIDE.md** - Strands + Bedrock AgentCore deployment documentation (reference material)

## Post-Hackathon Evolution Path

After demo success, consider:
- Appium/BrowserStack for real device matrix
- Locale packs and country flow scheduling
- Issue similarity detection across runs
- Hosted dashboard for team triage
- CI/nightly execution mode
- Multi-agent orchestration
