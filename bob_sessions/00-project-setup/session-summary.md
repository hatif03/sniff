# Session 00: Project Setup & Security

**Session Type:** Plan Mode → Agent Mode  
**Status:** ✅ Complete  
**Coins Used:** ~0.8  
**Date:** 2025 (initial session)

---

## Prompt

> Set up security hygiene and Bob agent infrastructure for the sniff monorepo. Create:
> - `.gitignore` at the repo root covering secrets, artifacts, Python, Node, Playwright
> - `.bobignore` at the repo root so Bob doesn't index credentials or lock files
> - `CONTRIBUTING.md` with setup instructions, coding conventions, ADR process, security rules
> - `docs/adr/` directory with ADR template and first three ADRs
> - `.bob/CONTEXT.md` so Bob has project context on every session
> - `docs/README.md` as a documentation index

---

## What Was Done

### Files Created

| File | Lines | Purpose |
|---|---|---|
| `.gitignore` (repo root) | 185 | Excludes secrets, artifacts, venvs, Node, Playwright output |
| `.bobignore` (repo root) | 109 | Mirrors .gitignore + excludes lock files from Bob context |
| `CONTRIBUTING.md` | 264 | Full contributor guide: setup, conventions, ADR process, security |
| `docs/README.md` | 22 | Documentation index |
| `docs/adr/ADR-000-template.md` | 46 | Reusable ADR template |
| `docs/adr/ADR-001-three-tier-architecture.md` | 80 | Three-tier AI decision model design decision |
| `docs/adr/ADR-002-dependency-updates.md` | 82 | Tailwind v4 migration + dependency strategy |
| `docs/adr/ADR-003-scheduler-apscheduler.md` | 72 | APScheduler daemon vs OS cron decision |
| `.bob/CONTEXT.md` | 56 | Bob agent context for every session |

### Security Audit Results

- ✅ No hardcoded secrets found in any tracked source file
- ✅ No `.env` files committed
- ✅ No `sniff.json` files found
- ✅ All credential patterns excluded by `.gitignore`

### Key Decisions Made

1. **Root-level `.gitignore`**: Protects against `sniff init` being run from the repo root, which would create `sniff.json` with API keys at a path not covered by sub-project gitignores.
2. **`.bobignore` excludes lock files** (`uv.lock`, `yarn.lock`): These are auto-generated, high-noise, and add no value to Bob's code understanding context.
3. **ADRs written before implementation**: All three architectural ADRs (three-tier model, dependency strategy, scheduler approach) were documented as "Accepted" before code was written, ensuring decisions are traceable.

---

## Next Steps

→ Session 01: Planning & Market Research
→ Session 02: Rename the project's original internal name → sniff
