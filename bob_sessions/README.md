# Sniff — Bob Sessions

This folder documents every Bob agent session used to build and expand Sniff. It follows the same convention as the [Atlas project](https://github.com/chanjoongx/atlas/tree/main/bob_sessions), which was used as a reference for this documentation format.

## What Is This?

Each subfolder represents one distinct Bob session (a focused unit of work). Inside each folder you will find:

| File | Purpose |
|---|---|
| `prompt.md` | The exact prompt(s) given to Bob for this session |
| `session-summary.md` | What was accomplished, files created/changed, deviations, next steps |
| `architecture.md` | (Where applicable) Architectural decisions and diagrams for this session |

## Session Index

| # | Session | Status | Bob Mode | Key Output |
|---|---|---|---|---|
| [00](./00-project-setup/) | Project Setup & Security | ✅ Complete | Plan | `.gitignore`, `.bobignore`, `CONTRIBUTING.md`, `docs/adr/` |
| [01](./01-planning-and-market-research/) | Planning & Market Research | ✅ Complete | Plan | `sniff-expansion-plan.md`, competitive analysis, all ADRs |
| [02](./02-rename-sherlock-to-sniff/) | Rename: sherlock → sniff | ✅ Complete | Agent | All source, config, docs, env vars renamed |
| [03](./03-dependency-updates/) | Dependency Updates + Tailwind v4 | 🔄 In Progress | Agent | `pyproject.toml`, `package.json`, `globals.css`, Tailwind v4 migration |
| [04](./04-jev-client-setup/) | Typesafe AI Jev Setup | ⬜ Pending | Agent | `jev_client.py`, skill definitions, `SniffConfig.typesafe` |
| [05](./05-three-tier-architecture/) | Three-Tier Intelligence Architecture | ⬜ Pending | Agent | `tier_router.py`, `TieredDecisionService`, per-tier metrics |
| [06](./06-scheduled-runs/) | Scheduled Continuous Runs | ⬜ Pending | Agent | `src/scheduler/`, `sniff daemon`, APScheduler daemon |
| [07](./07-regression-detection/) | Baseline Regression Detection | ⬜ Pending | Agent | `comparator.py`, `RunComparator`, `sniff compare` |
| [08](./08-journey-replay-ui/) | Journey Replay UI | ⬜ Pending | Agent | `/runs/[id]/replay`, `ReplayViewer`, mobile device frame |
| [09](./09-sniff-score/) | Sniff Score | ⬜ Pending | Agent | `scorer.py`, `SniffScore`, Slack emoji bar |
| [10](./10-cicd-integration/) | CI/CD GitHub Actions | ⬜ Pending | Agent | `sniff-action/`, `action.yml`, `--exit-on-severity` |
| [11](./11-architecture-docs/) | Architecture Docs Update | ⬜ Pending | Agent | Updated `ARCHITECTURE.md`, `SNIFF_CLI_GUIDE.md` |

## How to Read These Sessions

Each session summary answers four questions:
1. **What was the goal?** — Intent, context, why this session existed
2. **What was done?** — Every file created or changed, every decision made
3. **Why those decisions?** — The reasoning, alternatives considered, trade-offs
4. **What comes next?** — Unfinished work, open questions, handoff notes

## Relationship to the Expansion Plan

The full roadmap lives at [`sniff-expansion-plan.md`](../sniff-expansion-plan.md). The bob_sessions folder is the execution diary that tracks what actually happened vs what was planned.

## Architecture Decision Records

Major architectural decisions are captured as ADRs in [`docs/adr/`](../docs/adr/). Each session summary links to the relevant ADR(s) it produced or acted on.

| ADR | Title | Created In Session |
|---|---|---|
| [ADR-001](../docs/adr/ADR-001-three-tier-architecture.md) | Three-Tier Intelligence Architecture | Session 01 |
| [ADR-002](../docs/adr/ADR-002-dependency-updates.md) | Dependency Updates & Tailwind v4 | Session 01 |
| [ADR-003](../docs/adr/ADR-003-scheduler-apscheduler.md) | Scheduler: APScheduler Daemon | Session 01 |
