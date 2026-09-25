# Sniff — Bob Agent Context

## Project Summary

**Sniff** is an autonomous quality assurance system that simulates real user behaviour to continuously test signup and onboarding experiences across mobile and web platforms.

- **Python backend** (`sniff-ai/`): Playwright browser automation + AWS Bedrock Claude + Typesafe AI Jev + APScheduler
- **Next.js frontend** (`sniff-web/`): Dashboard, journey replay UI, Supabase integration
- **GitHub Actions plugin** (`sniff-action/`): CI/CD integration

## Active Expansion Plan

See [`sniff-expansion-plan.md`](../sniff-expansion-plan.md) for the full roadmap and sub-task tracker.

## Key Architecture

Three-tier intelligence model (see [ADR-001](../docs/adr/ADR-001-three-tier-architecture.md)):
- **Tier 1 — Deterministic**: Pure Python rules (signal extraction, guardrails)
- **Tier 2 — Jev (System One)**: Typesafe AI for fast navigation decisions
- **Tier 3 — Claude (System Two)**: AWS Bedrock for deep reasoning and diagnosis

## Key Files

| File | Purpose |
|---|---|
| `sniff-ai/src/core/config.py` | `SniffConfig` — all configuration |
| `sniff-ai/src/core/orchestrator.py` | `RunOrchestrator` — state machine |
| `sniff-ai/src/agent/decision_service.py` | `TieredDecisionService` — AI routing |
| `sniff-ai/src/agent/jev_client.py` | `JevClient` — Typesafe AI wrapper |
| `sniff-ai/src/agent/tier_router.py` | `TierRouter` — decision routing |
| `sniff-ai/src/executor/playwright_worker.py` | `PlaywrightWorker` — browser automation |
| `sniff-ai/src/diagnosis/classifier.py` | `DiagnosisClassifier` — root cause analysis |
| `sniff-ai/src/evidence/report_builder.py` | `ReportBuilder` + `RunReport` |
| `sniff-ai/src/evidence/scorer.py` | `SniffScore` — UX health score |
| `sniff-ai/src/cli/main.py` | CLI entry point (`sniff` command) |

## Coding Standards

1. Every Python file needs a module-level docstring explaining purpose and decisions
2. No hardcoded credentials — always via env vars → `SniffConfig`
3. All new features need an ADR in `docs/adr/` if they involve an architectural decision
4. Tests required for all new logic

## Security

- `.gitignore` and `.bobignore` at repo root prevent credential exposure
- `sniff.json` and `.env` are always excluded from git
- See `CONTRIBUTING.md` for full security rules

## Bob Sessions Log

All Bob agent sessions are documented in [`bob_sessions/`](../bob_sessions/README.md).
Each session folder contains `prompt.md` (exact prompt used) and `session-summary.md` (what was done and why).

| Session | Topic | Status |
|---|---|---|
| [00](../bob_sessions/00-project-setup/) | Security + Bob files | ✅ Complete |
| [01](../bob_sessions/01-planning-and-market-research/) | Planning + market research | ✅ Complete |
| [02](../bob_sessions/02-rename-sherlock-to-sniff/) | Rename sherlock → sniff | ✅ Complete |
| [03](../bob_sessions/03-dependency-updates/) | Dependency updates + Tailwind v4 | 🔄 In Progress |
| [04](../bob_sessions/04-jev-client-setup/) | Typesafe AI Jev client | ⬜ Pending |
| [05](../bob_sessions/05-three-tier-architecture/) | Three-tier architecture | ⬜ Pending |
| [06](../bob_sessions/06-scheduled-runs/) | Scheduled runs daemon | ⬜ Pending |
| [07](../bob_sessions/07-regression-detection/) | Regression detection | ⬜ Pending |
| [08](../bob_sessions/08-journey-replay-ui/) | Journey replay UI | ⬜ Pending |
| [09](../bob_sessions/09-sniff-score/) | Sniff Score | ⬜ Pending |
| [10](../bob_sessions/10-cicd-integration/) | CI/CD GitHub Actions | ⬜ Pending |
| [11](../bob_sessions/11-architecture-docs/) | Architecture docs update | ⬜ Pending |

