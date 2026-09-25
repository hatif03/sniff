# Session 11 Prompt: Architecture Documentation Update

**Session Type:** Agent Mode  
**Status:** ⬜ Pending  
**Reference:** Sub-Task 10 in `sniff-expansion-plan.md`

---

## Prompt (to be given when this session starts)

> Sub-Task 10 from `sniff-expansion-plan.md` — the final session:
>
> Update all architecture and user-facing documentation to reflect the complete expanded state of Sniff.
>
> 1. Update `sniff-ai/docs/product/ARCHITECTURE.md`:
>    - Replace the old single-tier architecture diagram with the three-tier diagram
>    - Add TierRouter routing rules table
>    - Add new component descriptions: `JevClient`, `TierRouter`, `TieredDecisionService`, `SniffScheduler`, `RunComparator`, `SniffScore`
>    - Add new CLI commands: `sniff daemon`, `sniff schedule`, `sniff compare`, `sniff score`
>    - Document the scheduler daemon architecture (APScheduler + SQLite job store)
>    - Update the sequence diagram to show tier routing
>
> 2. Update `sniff-ai/README.md`:
>    - New tagline: "Autonomous signup QA — catch onboarding bugs before real users do"
>    - Updated features list including: scheduled runs, regression detection, journey replay, Sniff Score, CI/CD integration
>    - Competitive positioning section (vs ColdVisit, Mabl, Rainforest QA)
>    - Updated quick start with `sniff daemon start` example
>    - Badge section: CI status badge, Sniff Score badge
>
> 3. Update `sniff-ai/SNIFF_CLI_GUIDE.md` with all new commands:
>    - `sniff daemon start|stop|status`
>    - `sniff schedule add|list|remove|run-now`
>    - `sniff compare <run_id_1> <run_id_2>`
>    - `sniff score [run_id]`
>    - Updated `sniff run` with `--exit-on-severity` and `--output-json` flags
>
> 4. Update `sniff-web/README.md`:
>    - Updated project description
>    - New pages: Journey Replay UI (`/runs/[id]/replay`)
>    - Updated setup instructions
>
> 5. Update `bob_sessions/README.md` session index:
>    - Mark all completed sessions as ✅
>
> 6. Update `sniff-expansion-plan.md`:
>    - Mark all sub-tasks as `[x] done`
>
> 7. Update `.bob/CONTEXT.md`:
>    - Mark expansion as complete
>    - Update key files table with all new files created

---

## Pre-Session Checklist

Before starting this session, verify:
- [ ] All sessions 04–10 are complete
- [ ] All tests pass: `uv run pytest`
- [ ] `sniff-web` build passes: `yarn build`
- [ ] All new CLI commands work end-to-end
