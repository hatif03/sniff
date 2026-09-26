# Sniff Expansion Plan

## Top-Level Overview

**Goal**: Evolve the project from its current state (using its original internal name) into a polished, market-ready product called **Sniff**. This involves a full rename, market positioning, architectural evolution toward a three-tier intelligence model (deterministic → Jev decision model → reasoning LLM), integration of Typesafe AI's Jev skill system, package modernization, and identification of feature gaps relative to the competitive landscape.

**Scope**:
1. Project rename — replacing the project's original internal name with "sniff" everywhere
2. Market research findings embedded as product direction
3. Dependency updates across Python (sniff-ai) and Node (sniff-web), including Tailwind v4 migration
4. Architecture evolution: three-tier intelligence (Deterministic / Jev / Reasoning)
5. Jev skill setup via Typesafe AI (API key available)
6. New feature roadmap derived from competitive analysis
7. Security hygiene — `.gitignore` and `.bobignore` to prevent credential exposure
8. Documentation discipline — every code decision documented inline and in ADR files

**Non-goals**: Full implementation of every new feature (this plan tracks what to build and how; implementation follows per sub-task).

## Confirmed Decisions

| Question | Decision |
|---|---|
| Typesafe AI access | API key available — implement Jev client fully in Sub-Task 3 |
| UI vs CI/CD priority | Journey Replay UI (Sub-Task 7) before CI/CD integration (Sub-Task 8) |
| Tailwind version | Upgrade to v4 during Sub-Task 2 |
| Sniff Score weights | Use research-backed weights: P0=−50, P1=−25, P2=−12, P3=−5; bonus +10 for goal success; performance/step-excess deductions up to −8 total |
| Scheduler approach | APScheduler-backed in-process daemon (`sniff daemon start/stop/status`) — portable, no OS cron dependency, works in containers and cloud VMs |
| Documentation | Every file changed must include a header docstring explaining purpose + decisions; ADR (Architecture Decision Record) files in `docs/adr/` for major architectural choices |
| Security | `.gitignore` and `.bobignore` maintained; no credentials in tracked files; all secrets via env vars only |
| Bob files | All Bob-related files (plan, skills, modes) kept in `.bob/` and maintained |

---

## Competitive Landscape & Market Research

### Similar Products Found

| Product | Type | Key Feature | Gap vs Sniff |
|---|---|---|---|
| **ColdVisit** (coldvisit.com) | AI mystery shopper for B2B sales flows | Records full user journeys, replay, heatmaps, natural language issue reports | No persona system; no mobile emulation; no severity classification |
| **Rainforest QA** | No-code AI test automation | Visual test recording, parallel runs, self-healing tests | No autonomous exploration; requires manual test authoring |
| **Testim** | AI-assisted E2E testing | Smart locators, root cause analysis | No real user behavior simulation; deterministic only |
| **Mabl** | Intelligent test cloud | Auto-healing, regression detection | No persona modeling; no onboarding-specific focus |
| **Playwright/Cypress** | Test frameworks | Fast, reliable, dev-friendly | Fully deterministic; no AI navigation |
| **Ghostery / FullStory** | Session recording & analytics | Real user sessions, funnels | Reactive (real users only); no proactive testing |
| **BrowserStack Automate** | Cross-device testing | Real device farms | No AI; requires scripted tests |
| **Heap / Mixpanel** | Product analytics | Conversion funnel analysis | Analytics only; no simulation |

### ColdVisit Analysis (coldvisit.com)

From their docs and positioning:
- **Core idea**: Simulate real sales prospect visits to find friction in B2B conversion flows (landing pages, sign-up, trial activation)
- **Key differentiation**: "Cold" visitor perspective — no prior context, no bias
- **Features we should learn from**:
  - **Journey replay**: Full step-by-step playback of what the AI visitor did
  - **Natural language summaries**: "The visitor got confused because the CTA was below the fold"
  - **Scheduled recurring runs**: Run every N hours/days automatically
  - **Funnel-specific personas**: Visitor types tuned to ICP (Ideal Customer Profile)
  - **Integration with analytics tools**: Export findings to Segment, Amplitude
  - **Team collaboration**: Share runs, comment on issues, assign to team members
  - **Baseline comparison**: Compare current run vs previous run to detect regressions
  - **Multi-step funnels**: Test not just signup but the full activation sequence

### Potential Customers

| Segment | Pain Point | Why Sniff |
|---|---|---|
| **SaaS startups (B2C/B2B)** | High signup drop-off rates; no QA team | Proactive catch of blockers before launch |
| **Growth teams** | Can't reproduce user-reported friction | Persona-driven simulation surfaces real confusion |
| **Mobile-first companies** | Mobile signup 40%+ of traffic; fragile | Playwright mobile emulation covers device diversity |
| **Enterprise onboarding teams** | Complex multi-step flows, compliance forms | Careful/confused personas expose form UX gaps |
| **Dev agencies / QA consultants** | Need to deliver QA for client projects | White-label persona test reports |
| **Product managers** | No visibility into signup quality between releases | Scheduled continuous runs + regression detection |

### Feature Gaps to Fill (derived from competitive analysis)

1. **Scheduled/continuous runs** — cron-triggered automated testing
2. **Baseline regression detection** — compare run N to run N-1
3. **Journey replay UI** — visual step-by-step replay in the web dashboard
4. **Natural language issue reports** — human-readable summaries, not just JSON
5. **Funnel coverage map** — which steps were reached, which were blocked
6. **CI/CD native integration** — GitHub Actions / GitLab CI plugin
7. **Team collaboration** — run sharing, comments, assignment
8. **Multi-step funnel definition** — define checkpoint milestones in a goal
9. **Analytics export** — Segment, Amplitude, webhook output
10. **Sniff Score** — a single UX health score (0-100) per run, trended over time

---

## Sub-Tasks

---

### Sub-Task 1 — Full Project Rename: Original Internal Name → "sniff"

**Status**: [x] done

**Intent**: The project is internally called by its original internal name in every configuration file, package metadata, class names, CLI entry points, environment variables, Slack bot name, and documentation. This sub-task renames all occurrences to "sniff" to match the public brand.

**Expected Outcomes**:
- `pyproject.toml` name = `sniff`, description updated, entry point = `sniff`
- `sniff-web/package.json` name = `sniff-web`
- All Python class names updated: main config class renamed to `SniffConfig`, `SlackAlert` bot name = "Sniff Alert Bot", etc.
- All CLI commands renamed to `sniff`
- Environment variables renamed to the `SNIFF_*` prefix
- Slack bot name, artifact path defaults, DB path updated
- All documentation files (README, guides) updated
- `src/` module import paths unchanged (internal `src.*` references stay)
- `.env.example` variable names updated
- Config file renamed to `sniff.json`

**Todo List**:
1. Update `sniff-ai/pyproject.toml`: name, description, entry point (`sniff = "src.cli.main:app"`)
2. Update `sniff-web/package.json`: name field
3. Rename `src/core/config.py`: main config class renamed to `SniffConfig`, all env var reads renamed to the `SNIFF_*` prefix
4. Rename throughout source: references to the config class in all files that import it
5. Update `.env.example`: all env vars renamed to the `SNIFF_*` prefix (e.g. `SNIFF_ENV`), etc.
6. Update `src/alerts/slack.py`: bot_name default = "Sniff Alert Bot"
7. Update `src/cli/main.py` and all command files: help text, app name
8. Update all Markdown documentation: replace the project's original internal name with "Sniff", update CLI examples
9. Rename CLI guide to `SNIFF_CLI_GUIDE.md`
10. Update config JSON default filename references (renamed to `sniff.json`)
11. Run grep to verify no remaining references to the project's original internal name (except test fixtures or intentional historical notes)

**Relevant Context**:
- `sniff-ai/pyproject.toml` — package metadata
- `sniff-ai/src/core/config.py` — main config class (`SniffConfig`), env var names
- `sniff-ai/src/alerts/slack.py` — bot_name default
- `sniff-ai/src/cli/main.py` — CLI app name and help text
- `sniff-ai/.env.example` — all env variable names
- All `*.md` files in `sniff-ai/`

---

### Sub-Task 2 — Dependency Updates + Tailwind v4 Migration

**Status**: [ ] pending

**Intent**: Bring all Python and Node packages to their latest stable versions. Identify any breaking changes in major version bumps, update usage accordingly, and ensure all tests pass after the upgrade. Tailwind v4 is a confirmed breaking migration — it removes `tailwind.config.js` in favour of CSS-based configuration (`@import "tailwindcss"` in the CSS file) and changes the class utility naming convention for some utilities.

**Expected Outcomes**:
- `sniff-ai/pyproject.toml` dependencies reflect latest stable versions
- `sniff-web/package.json` dependencies reflect latest stable versions
- `tailwindcss` upgraded to v4; `tailwind.config.js` removed; CSS config migrated to `globals.css`
- `uv.lock` / lock files regenerated cleanly
- All existing tests pass
- No deprecation warnings from updated packages
- `docs/adr/ADR-002-dependency-updates.md` documents every breaking change handled

**Todo List**:
1. **Python packages** — update to latest stable:
   - `playwright >=1.52.0`
   - `boto3 >=1.38.0`
   - `pydantic >=2.11.0`
   - `typer >=0.16.0`
   - `rich >=14.0.0`
   - `httpx >=0.28.0`
   - `supabase >=2.15.0`
   - `pytest >=8.4.0`
   - `pytest-asyncio >=0.26.0`
   - `ruff >=0.11.0`
2. Update `pyproject.toml` with pinned latest stable versions
3. Run `uv lock` to regenerate lock file
4. Run `uv run pytest` to verify no regressions
5. **Node packages** — update to latest stable:
   - `next ^15.3.0`
   - `react` / `react-dom ^19.1.0`
   - `@supabase/supabase-js ^2.50.0`
   - `framer-motion ^12.x` (check changelog for breaking changes)
   - `tailwindcss ^4.0.0` (breaking — see step 6)
   - `@tailwindcss/postcss ^4.0.0` (replaces old PostCSS plugin)
   - `typescript ^5.8.0`
   - `eslint ^9.x`
6. **Tailwind v4 migration** (breaking):
   - Remove `tailwind.config.js` (or `tailwind.config.ts`)
   - Update `postcss.config.js` to use `@tailwindcss/postcss` plugin
   - Update `globals.css`: replace `@tailwind base; @tailwind components; @tailwind utilities;` with `@import "tailwindcss";`
   - Move any `theme.extend` values to CSS custom properties in `globals.css`
   - Run the Tailwind v4 upgrade codemod: `npx @tailwindcss/upgrade`
   - Audit component files for renamed utilities (e.g. `shadow-sm` → `shadow-xs` in v4)
7. Run `npm install` and `npm run build` to verify
8. Write `docs/adr/ADR-002-dependency-updates.md` documenting all breaking changes handled

**Relevant Context**:
- `sniff-ai/pyproject.toml`
- `sniff-ai/uv.lock`
- `sniff-web/package.json`
- `sniff-web/tailwind.config.js` (to be removed)
- `sniff-web/app/globals.css` (to be updated)
- `sniff-ai/requirements.txt`

---

### Sub-Task 3 — Typesafe AI Jev Skill Setup

**Status**: [ ] pending

**Intent**: Integrate Typesafe AI's Jev model (a "System One" fast decision model) as a new intelligence tier between the deterministic rule engine and the full reasoning model (Bedrock Claude). Jev operates as a skill-based agent: it receives structured inputs, applies learned heuristics, and returns rapid decisions without deep chain-of-thought reasoning. This sub-task sets up the skill definitions and client integration following https://docs.typesafe.ai/agent-skill.

**Expected Outcomes**:
- A new `src/agent/jev_client.py` module wrapping the Typesafe AI API
- Jev skill definitions written as structured JSON/YAML skill specs
- Jev integrated into the decision pipeline as a middle tier
- Configuration keys for Typesafe AI added to `SniffConfig` and `.env.example`
- The existing `DecisionService` updated to route decisions by complexity tier

**Todo List**:
1. Read Typesafe AI docs at https://docs.typesafe.ai/agent-skill to understand:
   - Skill spec format (inputs, outputs, schema)
   - API authentication and invocation pattern
   - How skills differ from prompts
2. Add `typesafe-ai` (or equivalent SDK) to `pyproject.toml` dependencies
3. Create `src/agent/jev_client.py`:
   - `JevClient` class wrapping the Typesafe AI API
   - `invoke_skill(skill_name, inputs)` method returning structured output
   - Auth via `TYPESAFE_API_KEY` env var
4. Define Jev skills (in `src/agent/skills/`):
   - `navigation_decision.skill` — given an observation, choose the next action type (tap/type/scroll/wait/abort) without deep reasoning
   - `stuck_detector.skill` — given recent action history, classify if the agent is stuck
   - `element_selector.skill` — given visible text + goal, pick the best target element
5. Add `SniffConfig.typesafe` config block with `api_key`, `model_id`, `enabled` fields
6. Update `.env.example` with `TYPESAFE_API_KEY`, `TYPESAFE_MODEL_ID`
7. Write unit tests for `JevClient` with mocked API responses

**Relevant Context**:
- `src/agent/bedrock_client.py` — pattern to follow for a new AI client
- `src/agent/decision_service.py` — where Jev will be integrated in Sub-Task 4
- `src/core/config.py` — config block pattern

---

### Sub-Task 4 — Three-Tier Intelligence Architecture

**Status**: [ ] pending

**Intent**: Restructure the decision-making pipeline into three explicit tiers:

| Tier | Technology | When Used | Examples |
|---|---|---|---|
| **Tier 1 — Deterministic** | Pure Python rules / code | Signal extraction, state machine transitions, guardrail checks, root cause signals | "Is TTFB > 5s?" "Has step count exceeded max?" "Is this a 4xx error?" |
| **Tier 2 — Jev (System One)** | Typesafe AI Jev | Fast, frequent, low-cost decisions during navigation | "Which element to tap next?", "Is the agent stuck?", "Pick the right form field" |
| **Tier 3 — Reasoning (Claude)** | AWS Bedrock Claude | Deep, rare, high-stakes decisions | "Is this a P0 blocker?", "What's the root cause?", "Generate persona review narrative" |

This restructuring moves the majority of per-step navigation decisions to Jev (cheaper, faster), reserves Claude for diagnosis, persona review, and ambiguous high-stakes reasoning, and makes all deterministic signal extraction pure code with no LLM involvement.

**Expected Outcomes**:
- `src/agent/decision_service.py` updated with a `TieredDecisionService` that routes to the right tier
- `src/diagnosis/classifier.py` updated: deterministic signals stay pure Python; only final root cause narrative (if ambiguous) goes to Claude
- New `src/agent/skills/` directory with Jev skill definitions
- A `TierRouter` class that decides which tier to invoke based on context
- Cost and latency reduced per-run due to fewer Claude invocations
- Existing behavior preserved (Claude fallback when Jev is unavailable or confidence is low)
- Architecture documented in updated `ARCHITECTURE.md`

**Todo List**:
1. Define the routing logic: what inputs → which tier (document as `TierRouter` rules)
2. Create `src/agent/tier_router.py`:
   - `TierRouter` class with `route(observation, context) → Tier` method
   - Rules: if action is simple navigation and confidence signal is clear → Jev; if diagnosis or narrative → Claude; if signal is deterministic → code
3. Update `DecisionService` → `TieredDecisionService`:
   - Call `TierRouter.route()` to pick tier
   - Tier 1: return result from pure Python rules
   - Tier 2: call `JevClient.invoke_skill()`
   - Tier 3: call `BedrockClient.invoke()` (existing behavior)
   - Fall back to Claude if Jev returns low confidence or errors
4. Refactor `DiagnosisClassifier`:
   - Move all `DiagnosisSignals` methods to remain purely deterministic (no change needed, already pure)
   - Move ONLY the "generate suggested fix narrative" to Claude (if currently LLM-driven)
   - Move "classify ambiguous root cause" to Jev
5. Move the "persona behavior guidelines → action style" injection to a Jev skill instead of embedding it in the Claude system prompt
6. Update `RunOrchestrator` to instantiate `TieredDecisionService`
7. Add per-tier metrics to `RunReport`: `tier1_calls`, `tier2_calls`, `tier3_calls`, `tier2_cost_saved`
8. Update `ARCHITECTURE.md` with three-tier diagram

**Relevant Context**:
- `src/agent/decision_service.py` — current single-tier decision logic
- `src/diagnosis/classifier.py` — hybrid rules + LLM, needs tier split
- `src/core/orchestrator.py` — instantiates DecisionService
- `src/core/models.py` — `AgentDecision`, `DiagnosisResult` models

---

### Sub-Task 5 — New Feature: Scheduled Continuous Runs

**Status**: [ ] pending

**Intent**: Enable Sniff to run autonomously on a schedule (hourly, daily, or on deploy webhook), building a continuous quality baseline. This is the most requested feature in the competitive landscape and directly enables the "catch bugs before real users do" value proposition.

**Expected Outcomes**:
- New `sniff schedule` CLI command: `sniff schedule --goal "..." --cron "0 * * * *" --persona careful_user`
- A `ScheduleConfig` model stored to `sniff.json`
- A lightweight scheduler daemon (`sniff daemon start`) using APScheduler or cron
- Webhook endpoint option: POST to `/webhook/trigger` to start a run (for CI/CD integration)
- Scheduled run results saved to Supabase with `schedule_id` linkage
- Slack alert includes "scheduled run" context

**Todo List**:
1. Add `apscheduler` to Python dependencies
2. Create `src/scheduler/scheduler.py` with `SniffScheduler` class
3. Add `src/cli/commands/schedule.py`: `sniff schedule add|list|remove|run-now`
4. Add `ScheduleConfig` model to `src/core/config.py`
5. Add `src/cli/commands/daemon.py`: `sniff daemon start|stop|status`
6. Add webhook trigger support via a minimal `httpx`-based server or FastAPI endpoint
7. Update Supabase schema to include `schedule_id` on runs table
8. Update Slack alert builder to include schedule context
9. Write tests for scheduler logic

**Relevant Context**:
- `src/core/config.py` — config model to extend
- `src/cli/main.py` — add new commands
- `src/integrations/supabase_client.py` — add schedule_id to run records

---

### Sub-Task 6 — New Feature: Baseline Regression Detection

**Status**: [ ] pending

**Intent**: After each run, compare results to the previous run on the same goal+persona combination. Detect regressions (issues that weren't present before) and improvements. This enables teams to use Sniff as a release gate.

**Expected Outcomes**:
- `RunComparator` class that diffs two `RunReport` objects
- `RegressionResult` model: new issues, resolved issues, severity changes, step count delta
- `sniff compare <run_id_1> <run_id_2>` CLI command
- Slack alert for scheduled runs includes regression diff vs last run
- Supabase stores baseline run_id reference

**Todo List**:
1. Create `src/evidence/comparator.py` with `RunComparator` and `RegressionResult` models
2. Add `sniff compare` CLI command in `src/cli/commands/compare.py`
3. Update `RunOrchestrator` to auto-load previous run for the same goal+persona from Supabase or local artifacts
4. Integrate `RunComparator` into the reporting phase
5. Update `SlackAlert` to include regression summary block
6. Write tests for comparator logic

**Relevant Context**:
- `src/evidence/report_builder.py` — `RunReport` model to compare
- `src/alerts/slack.py` — extend Slack blocks
- `src/integrations/supabase_client.py` — query previous runs

---

### Sub-Task 7 — New Feature: Journey Replay UI (Web Dashboard)

**Status**: [ ] pending

**Intent**: The `sniff-web` Next.js dashboard currently exists but its capabilities are not fully defined. This sub-task adds a visual step-by-step journey replay: users can click through each step of a run, see the screenshot, the action taken, the agent's reasoning, and any errors at that step. This is the primary feature that differentiates Sniff's reporting from raw JSON artifacts.

**Expected Outcomes**:
- `/runs/[run_id]` page in `sniff-web` showing run overview
- `/runs/[run_id]/replay` page with step-by-step screenshot + action + reasoning viewer
- Supabase query to fetch observations and actions by run_id
- Mobile-frame UI: screenshots displayed inside a phone/browser frame
- Severity badge and root cause tag visible on the run overview page

**Todo List**:
1. Audit existing `sniff-web/app/` structure to understand current pages
2. Create Supabase queries for fetching run data (observations + actions + diagnosis)
3. Build `RunOverviewCard` component: status, severity, goal, persona, step count
4. Build `ReplayViewer` component: scrollable timeline with screenshot thumbnails
5. Build `StepDetail` panel: full screenshot, action details, reasoning summary, errors
6. Add mobile device frame SVG wrapper for screenshots
7. Add `DiagnosisBadge` component: severity color + root cause icon
8. Wire up `/runs/[run_id]/replay` route
9. Add navigation between steps (prev/next keyboard shortcuts)

**Relevant Context**:
- `sniff-web/app/` — Next.js app directory
- `sniff-web/components/` — existing React components
- `sniff-ai/src/integrations/supabase_client.py` — data schema stored in Supabase

---

### Sub-Task 8 — New Feature: CI/CD Integration (GitHub Actions Plugin)

**Status**: [ ] pending

**Intent**: Package Sniff as a GitHub Actions step so engineering teams can run signup flow tests as part of their deployment pipeline. A failed P0/P1 can optionally block the deployment.

**Expected Outcomes**:
- `sniff-action/` directory with GitHub Action YAML definition
- `action.yml` defining inputs: `goal`, `url`, `persona`, `fail_on_severity`
- Docker-based action that runs `sniff run` and exits with code 1 on P0/P1
- Published to GitHub Actions Marketplace (plan only; actual publish is out of scope)
- Documentation in `docs/CI_CD_INTEGRATION.md`

**Todo List**:
1. Create `sniff-action/action.yml` with input schema
2. Create `sniff-action/Dockerfile` for the action container
3. Create `sniff-action/entrypoint.sh` that runs `sniff run` and parses exit code
4. Add `--exit-on-severity` flag to `sniff run` CLI command
5. Write `docs/CI_CD_INTEGRATION.md` with GitHub Actions example

**Relevant Context**:
- `sniff-ai/src/cli/commands/run.py` — add exit code logic
- `sniff-ai/DEPLOYMENT_GUIDE.md` — reference for Docker setup

---

### Sub-Task 9 — New Feature: Sniff Score

**Status**: [ ] pending

**Intent**: Introduce a single composite UX health score (0–100) computed per run, trended over time. The score uses research-backed penalty weights and rewards, giving product teams a simple north-star metric.

**Scoring Formula** (confirmed):
```
Base score: 100
Deductions:
  P0 issue detected:        −50
  P1 issue detected:        −25
  P2 issue detected:        −12
  P3 issue detected:         −5
  TTFB > 3s:                 −4
  Step count > 1.5× median:  −4
Bonuses:
  Goal completed:           +10 (max 100 cap)
Final: clamp(score, 0, 100)
```

**Expected Outcomes**:
- `SniffScore` model with score (0-100), component breakdown (per-penalty detail), trend vs previous run
- Score computed in `ReportBuilder.build_report()`
- Score displayed in Slack alerts (emoji bar: 🟢 80+, 🟡 50-79, 🔴 <50)
- Score stored in Supabase `runs` table
- Score visible in web dashboard on run overview cards
- `sniff score [run_id]` CLI command to display score

**Todo List**:
1. Define scoring formula in `src/evidence/scorer.py` with the confirmed weights above
2. Add `SniffScore` to `RunReport` model
3. Integrate scoring into `ReportBuilder.build_report()`
4. Add score to Slack alert blocks (emoji health bar)
5. Add score to Supabase `runs` table (migration)
6. Add `RunOverviewCard` score display in `sniff-web`
7. Add `sniff score` CLI command

**Relevant Context**:
- `src/evidence/report_builder.py` — `RunReport`, `ReportBuilder`
- `src/alerts/slack.py` — Slack block extensions
- `sniff-web/components/` — dashboard card components

---

### Sub-Task 10 — Architecture Documentation Update

**Status**: [ ] pending

**Intent**: Update `ARCHITECTURE.md` and the README to reflect the renamed project, the three-tier intelligence model, the new feature set, and the expanded component graph. This is the canonical reference for the system's design.

**Expected Outcomes**:
- `ARCHITECTURE.md` updated with three-tier diagram and routing rules
- `README.md` updated: new name, new features, updated CLI examples
- `SNIFF_CLI_GUIDE.md` created from the renamed CLI guide file with all new commands
- Competitive positioning section added to README

**Todo List**:
1. Update `sniff-ai/docs/product/ARCHITECTURE.md` with three-tier diagram (ASCII art + description)
2. Update `sniff-ai/README.md`: name, features list, CLI examples
3. Rename the CLI guide file to `SNIFF_CLI_GUIDE.md` and update all commands
4. Add competitive positioning section to README
5. Update `sniff-web/README.md` with updated project name and web features

**Relevant Context**:
- `sniff-ai/docs/product/ARCHITECTURE.md`
- `sniff-ai/README.md`
- `sniff-ai/SNIFF_CLI_GUIDE.md`

---

### Sub-Task 11 — Security Hygiene and Bob File Maintenance

**Status**: [ ] pending

**Intent**: Ensure no credentials or sensitive data can accidentally leak into version control. Maintain all Bob-related agent files properly. This sub-task runs alongside all others as a cross-cutting concern.

**Expected Outcomes**:
- `.gitignore` at repo root covers: `.env`, `*.env`, `sniff.json`, `artifacts/`, `*.pem`, `*.key`, AWS credential files, `__pycache__/`, `.uv/`, `node_modules/`
- `.bobignore` at repo root covers the same secrets + tells Bob not to index credential files
- `sniff-expansion-plan.md` kept in repo root (Bob context artifact)
- All `docs/adr/` files tracked in git (they are documentation)
- `CONTRIBUTING.md` added documenting: how to run, how to add features, coding conventions, ADR process

**Todo List**:
1. Create/update `.gitignore` at repo root with comprehensive secret and artifact exclusions
2. Create `.bobignore` at repo root with same exclusions + Bob-specific patterns
3. Audit existing tracked files for any accidentally committed secrets (`.env`, config JSON with keys)
4. Create `CONTRIBUTING.md` documenting project conventions
5. Create `docs/adr/` directory with `ADR-000-template.md` and `ADR-001-three-tier-architecture.md`
6. Ensure `sniff-expansion-plan.md` is tracked and up to date

**Relevant Context**:
- Repo root `d:\sniff`
- `sniff-ai/.env.example` — reference for what secrets look like
- `sniff-ai/sniff.json` — may contain API keys if user ran `sniff init`

---

## Execution Order

The sub-tasks should be executed in this order:

```
Sub-Task 11 (Security + Bob Files)       ← First: safety before anything else
    ↓
Sub-Task 1 (Rename)
    ↓
Sub-Task 2 (Dependencies + Tailwind v4)
    ↓
Sub-Task 3 (Jev Setup)
    ↓
Sub-Task 4 (Three-Tier Architecture)     ← Depends on 3
    ↓
Sub-Task 5 (Scheduled Runs)              ← APScheduler daemon approach
Sub-Task 6 (Regression Detection)        ← Can run in parallel with 5
Sub-Task 7 (Journey Replay UI)           ← Priority over Sub-Task 8
Sub-Task 9 (Sniff Score)                 ← Can run after 4
    ↓
Sub-Task 8 (CI/CD Integration)           ← After 7
    ↓
Sub-Task 10 (Architecture Docs)          ← Last, documents everything
```

---

## Documentation Standards (applies to all sub-tasks)

Every file touched during implementation must:
1. Include a module-level docstring stating: purpose, decisions made, why this approach was chosen
2. Each class must have a docstring explaining its role in the architecture
3. Non-obvious logic must have inline comments with the reasoning
4. Major architectural decisions go into `docs/adr/ADR-XXX-<topic>.md`

ADR format:
```
# ADR-XXX: Title
## Status: Accepted
## Context: What problem are we solving?
## Decision: What did we decide?
## Rationale: Why this option over alternatives?
## Consequences: What are the trade-offs?
```

---

## All Decisions Recorded

| # | Question | Decision | Rationale |
|---|---|---|---|
| 1 | Typesafe AI access | Full implementation, key available | No need to stub |
| 2 | UI vs CI/CD priority | Journey Replay (Sub-Task 7) first | Higher user value, ColdVisit parity |
| 3 | Tailwind version | Upgrade to v4 | Modern standard; avoid tech debt |
| 4 | Sniff Score weights | P0=−50, P1=−25, P2=−12, P3=−5, success=+10 | More severe penalty for P0 blockers; P1 is still major |
| 5 | Scheduler approach | APScheduler in-process daemon | Works in Docker/cloud; no OS cron dependency; portable |
| 6 | Documentation | ADR files + module docstrings on every change | Traceability for all decisions |
| 7 | Security | .gitignore + .bobignore; audit for leaked secrets | First sub-task executed |
