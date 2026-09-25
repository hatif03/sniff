# Session 07 Prompt: Baseline Regression Detection

**Session Type:** Agent Mode  
**Status:** ⬜ Pending  
**Reference:** Sub-Task 6 in `sniff-expansion-plan.md`

---

## Prompt (to be given when this session starts)

> Sub-Task 6 from `sniff-expansion-plan.md`:
>
> After each run, compare results to the previous run on the same goal+persona combination to detect regressions.
>
> 1. Create `sniff-ai/src/evidence/comparator.py`:
>    - `RegressionResult` Pydantic model:
>      * `baseline_run_id: str`
>      * `current_run_id: str`
>      * `severity_changed: bool`
>      * `severity_delta: int` (e.g. P1 → P0 = worse, P0 → P2 = better)
>      * `new_issues: list[str]` (issues in current but not baseline)
>      * `resolved_issues: list[str]` (issues in baseline but not current)
>      * `step_count_delta: int`
>      * `score_delta: Optional[float]` (once Session 09 is done)
>      * `is_regression: bool`
>      * `summary: str` (human-readable one-liner)
>    - `RunComparator` class with `compare(baseline: RunReport, current: RunReport) -> RegressionResult`
>    - Module docstring explaining purpose and how baselines are selected
>
> 2. Add `sniff-ai/src/cli/commands/compare.py`:
>    - `sniff compare <run_id_1> <run_id_2>` — load two RunReports from local artifacts and compare
>    - Rich table output showing what changed
>    - Exit code 1 if regression detected (for CI use)
>
> 3. Update `RunOrchestrator` to auto-compare after each run:
>    - Load the most recent previous run with the same `goal_hash` + `persona` from Supabase (if enabled) or local artifacts
>    - Run `RunComparator.compare(baseline, current)` in the REPORT phase
>    - Include `RegressionResult` in the `RunReport`
>
> 4. Update `SlackAlert` to include regression summary block when a regression is detected:
>    - New block: "📉 Regression Detected" with severity delta and new/resolved issues
>    - 🟢 "Improvement" block when issues are resolved
>
> 5. Write tests for comparator:
>    - Same severity (no regression)
>    - Severity worsened (regression)
>    - Severity improved
>    - New issues appeared
>    - Issues resolved
>    - No baseline available (graceful handling)

---

## Pre-Session Checklist

Before starting this session, verify:
- [ ] Session 05 is complete (three-tier architecture working)
- [ ] `sniff-ai/src/evidence/report_builder.py` has been read — understand `RunReport` structure
