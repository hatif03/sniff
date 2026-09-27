# Sniff — Agent-Assisted Development Record

This document describes how **IBM Bob 2.0** (the AI coding agent) was used to design, plan, and build every feature of Sniff from the ground up. It serves as the canonical reference for the agent-assisted development methodology used across all 17 Bob sessions.

---

## ⚠️ IBM Bob Organisation Disclaimer

This project was built using **IBM Bob 2.0** across two IBM organisations:

| Organisation | Region | Sessions | Notes |
|---|---|---|---|
| `TECHZONE-TS022872826` | us-east | Sessions 00–12 | Existing organisation from a prior IBM hackathon. Used for the majority of the build — all foundational, architectural, and early-feature work. |
| `ibm-coding-challenge-uat` | us-east | Sessions 13–16 + current | Active organisation for this challenge. Used for deployment, the audit feature, Supabase provisioning, trends analytics, and whole-site audit. |

> Both organisations ran **identical IBM Bob 2.0 capabilities**: Plan mode, Agent mode, sub-agent spawning, MCP server connections (including Supabase MCP), skills, and shell tool access. The org switch was a workspace/billing boundary, not a capability boundary — the same Bob tooling and the same methodology applied across both.

---

## What Is IBM Bob?

IBM Bob is an AI coding agent with multiple operating modes, tool integrations, and capabilities. On this project it was used as the primary implementation partner — not just for code generation, but for market research, architectural design, documentation, live API verification, and deployment.

Key Bob capabilities used on this project:

| Capability | How It Was Used |
|---|---|
| **Plan Mode** | Architectural design, market research, ADR authoring, feature roadmap planning before any code was written |
| **Agent Mode** | Full-stack implementation: Python backend, Next.js frontend, Supabase migrations, Cloud Run + Vercel deployments |
| **Sub-agents (spawn_subagent)** | Parallelising independent frontend work, separating large UI rebuilds from backend wiring |
| **MCP Servers** | Supabase MCP for live database provisioning and migrations; filesystem tools for bulk file operations |
| **Skills** | The `dataviz` skill for chart palette validation; the `qodo-get-rules` skill for coding conventions |
| **IBM Docs Search** | Researching integration patterns, API docs, and deployment guidance |
| **Web search + live API testing** | Verifying real API shapes for Typesafe Jev, Gemini, k2-horizon before coding against them |

---

## Project Overview

Sniff is an autonomous browser agent that simulates real user behaviour to test signup/onboarding flows and audit landing pages. It was built entirely through IBM Bob sessions, starting from a working but internally-named prototype and evolving into a publicly deployed, multi-product SaaS.

**Starting state**: A Python CLI tool with a single-tier AWS Bedrock Claude decision pipeline, no public name, no web product surface, and no deployment.

**Final state**: A fully deployed product (Cloud Run backend + Vercel frontend), two product surfaces (signup-flow testing + landing-page conversion audit + whole-site crawl), a three-tier AI reasoning stack (Deterministic → Jev → Gemini/k2-horizon), shared Supabase persistence, scheduled continuous runs, and 193 passing tests.

---

## Session Index

| # | Session | Bob Mode | Key Bob Techniques |
|---|---|---|---|
| [00](./bob_sessions/00-project-setup/) | Project Setup & Security | Plan | Plan mode for infrastructure decisions; ADR authoring |
| [01](./bob_sessions/01-planning-and-market-research/) | Planning & Market Research | Plan | Plan mode for codebase audit + market research + roadmap; web browsing for competitor research |
| [02](./bob_sessions/02-project-rename/) | Project Rename | Agent | Bulk grep/replace; systematic file-by-file audit; shell tools |
| [03](./bob_sessions/03-dependency-updates/) | Dependency Updates + Tailwind v4 | Agent | Live registry lookups; build verification; breaking-change analysis |
| [04](./bob_sessions/04-jev-client-setup/) | Jev Client Setup | Agent | Live API verification; doc reading; test-driven development |
| [05](./bob_sessions/05-three-tier-architecture/) | Three-Tier Architecture | Agent | Research-grounded pattern application; existing-interface reuse |
| [06](./bob_sessions/06-scheduled-runs/) | Scheduled Continuous Runs | Agent | APScheduler integration; daemon architecture |
| [07](./bob_sessions/07-regression-detection/) | Baseline Regression Detection | Agent | Diff modelling; Pydantic model design |
| [08](./bob_sessions/08-journey-replay-ui/) | Journey Replay UI | Agent | Next.js App Router; Supabase query design; component architecture |
| [09](./bob_sessions/09-sniff-score/) | Sniff Score | Agent | Scoring formula implementation; Slack block extension |
| [10](./bob_sessions/10-cicd-integration/) | CI/CD GitHub Actions | Agent | Docker action packaging; exit-code contract design |
| [11](./bob_sessions/11-architecture-docs/) | Architecture Docs Update | Agent | Documentation synthesis across all prior sessions |
| [12](./bob_sessions/12-provider-swap-and-saas-foundation/) | Provider Swap + SaaS Foundation | Agent | Live API credential testing; FastAPI backend; shadcn/UI; sub-agent parallelism |
| [13](./bob_sessions/13-audit-feature-and-deployment/) | Audit Feature + Public Deployment | Agent | Real competitor schema extraction; Cloud Run + Vercel deployment; path-traversal security |
| [14](./bob_sessions/14-ui-reimagine-and-shared-data/) | UI Reimagine + Shared Data | Agent | Supabase MCP provisioning; sub-agent delegation; investigate-before-build discipline |
| [15](./bob_sessions/15-trends-and-scheduled-runs/) | Trends + Reliable Scheduled Runs | Agent | Sub-agent parallelism; GCP Cloud Scheduler integration; live production verification |
| [16](./bob_sessions/16-whole-site-audit/) | Whole-Site Audit | Agent | Research-before-design; live-testing-as-bug-finder; four bug fixes from real runs |

---

## Bob Modes Used

### Plan Mode
Used in Sessions 00 and 01 — the two foundational sessions that had to produce durable decisions before any code was written. Plan mode's constraint (no file writes) kept these sessions focused on thinking, researching, and documenting rather than building prematurely.

Session 01's Plan mode session produced the entire `sniff-expansion-plan.md` roadmap, three ADRs, competitive analysis, and all confirmed architectural decisions from a single prompt. The user's follow-up answers (API key availability, feature priority, Tailwind version, score weights, scheduler approach) were incorporated before the plan was written — not after.

### Agent Mode
Used for all implementation sessions (02–16). Agent mode had access to read/write file tools, shell execution, and MCP server connections. The key discipline applied: **investigate before writing**. Every session started with Bob reading the existing codebase before proposing changes, not after.

---

## MCP Servers Used

### Supabase MCP
Used in Session 14 to provision a real Supabase project and apply the initial schema migration. This was not a manual database setup — Bob used the Supabase MCP tools to:
- Create the actual Supabase project (`xpzcpsjjmubxfmbpfnvn`)
- Apply `docs/supabase_schema.sql` as a migration (and fix a real PostgreSQL syntax bug in it — MySQL-style `INDEX` clauses — discovered only when applied to a real database for the first time)
- Apply the `audits` table migration in Session 14
- Apply the `lcp`/`fcp`/`cls` columns migration in Session 15
- Apply the `site_audits` table + `audits.site_audit_id` FK migration in Session 16

The Supabase MCP enabled Bob to do database work that would otherwise require a human to log into the Supabase dashboard or run the CLI manually.

### Filesystem / Shell Tools
Used across all Agent mode sessions for:
- Bulk grep/replace during the Session 02 rename
- Running `uv run pytest` to verify tests after every change
- Running `yarn build` and `yarn lint` to verify Next.js builds
- Running `gcloud run deploy` for Cloud Run deployments in Session 13

---

## Sub-Agents

Sub-agents (spawned via `spawn_subagent`) were used where work was genuinely independent and could run in parallel without conflicting with the main session's work.

| Session | Sub-agent Work | Why Parallelised |
|---|---|---|
| Session 12 | Initial UI redesign exploration | Frontend-only, no overlap with backend provider-swap work |
| Session 14 | Full marketing-page rebuild (7 sections) | Well-specified, frontend-only, while main thread handled Supabase provisioning |
| Session 15 | Three concurrent agents on `dashboard/page.tsx` | Mounting FrictionHeatmap, adding Trends tab, adding Schedules nav link |

**Lesson noted** (Session 15): three agents on the same file is a coordination risk even when their patches don't overlap on the same lines. Flagged in the session summary as an avoidable design choice for next time.

---

## Skills Used

### `dataviz` Skill
Used in Session 12 for chart colour palette validation. The skill's pre-validated good/warning/critical palette was used for chart-specific status colours, deliberately scoped to charts only rather than reused as a general UI accent — to avoid the token-collision problem Bob had already encountered with shadcn's theme block.

### Investigate-Before-Build (Discipline, Not a Named Skill)
Every session summary explicitly records what was read before any code was written. This is Bob's built-in discipline enforced by the `investigate_before_answering` system instruction, but it was also actively reinforced in prompts ("research first, then plan, before writing any code" in Session 16).

Notable examples where investigation changed what was built:
- Session 04: Live API call revealed wrong endpoint shape and wrong model ID; the planned implementation had to be replaced
- Session 05: Reading existing code revealed `DiagnosisClassifier` was already 100% deterministic, not hybrid; fixed the docstring instead of adding a new code path
- Session 14: Reading `package.json` revealed all needed libraries were already installed; no new installs needed

---

## Architectural Decisions Made With Bob

All major architectural decisions were documented as ADRs (Architecture Decision Records) in `docs/adr/`. The full evolution of the architecture across all sessions is documented in [`bob_sessions/architecture.md`](./bob_sessions/architecture.md).

Key decisions and which session they were taken in:

| Decision | Session | ADR |
|---|---|---|
| Three-tier AI architecture (Deterministic + Jev + Claude) | 01 | ADR-001 |
| APScheduler daemon for scheduled runs | 01 | ADR-003 |
| Dependency update + Tailwind v4 migration strategy | 01 | ADR-002 |
| Gemini (vision) + k2-horizon (text) replacing AWS Bedrock | 12 | — |
| FastAPI backend + Next.js proxy pattern (SaaS Phase 1) | 12 | — |
| Supabase as shared persistence (replacing per-browser localStorage) | 14 | — |
| Cloud Scheduler + atomic tick endpoint (replacing in-process APScheduler) | 15 | — |
| Reuse `audits` table + existing detail page for site-audit crawl pages | 16 | — |

---

## Documentation Discipline

Every session followed the same documentation standard:
1. Every file touched includes a module-level docstring stating purpose, decisions, and rationale
2. Every class has a docstring explaining its role in the architecture
3. Non-obvious logic has inline comments with the reasoning
4. Major architectural decisions go into `docs/adr/`
5. Each `bob_sessions/` folder records: the prompt, what was done, why, and what comes next

This discipline was set in the original planning session (Session 01) and enforced throughout. The user's explicit instruction: *"For every line of code you change, document every decision, reason, motive behind it."*

---

## How to Read the Session Logs

Each `bob_sessions/NN-name/` folder contains:

| File | Contents |
|---|---|
| `prompt.md` | The exact prompt(s) given to Bob |
| `session-summary.md` | What was accomplished, files changed, decisions, deviations, next steps |
| `bob-methodology.md` | **How IBM Bob was used**: modes, tools, sub-agents, skills, and techniques specific to this session |

The [`bob_sessions/architecture.md`](./bob_sessions/architecture.md) file documents the evolution of the system architecture across all sessions, including every point where the architecture changed and why.
