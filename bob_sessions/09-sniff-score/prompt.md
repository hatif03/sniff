# Session 09 Prompt: Sniff Score

**Session Type:** Agent Mode  
**Status:** ⬜ Pending  
**Reference:** Sub-Task 9 in `sniff-expansion-plan.md`

---

## Prompt (to be given when this session starts)

> Sub-Task 9 from `sniff-expansion-plan.md`:
>
> Add a single composite UX health score (0–100) to every Sniff run.
>
> Confirmed scoring formula:
> ```
> Base: 100
> Deductions:
>   P0 detected:              −50
>   P1 detected:              −25
>   P2 detected:              −12
>   P3 detected:               −5
>   TTFB > 3000ms:             −4
>   Step count > 1.5× median:  −4
> Bonuses:
>   Goal completed:           +10
> Final: clamp(score, 0, 100)
> ```
>
> 1. Create `sniff-ai/src/evidence/scorer.py`:
>    - `ScoreComponent` dataclass: `name: str`, `delta: int`, `reason: str`
>    - `SniffScore` Pydantic model:
>      * `score: int` (0–100)
>      * `components: list[ScoreComponent]` (breakdown of what contributed)
>      * `trend: Optional[int]` (delta vs previous run's score, set by comparator)
>      * `grade: Literal["A", "B", "C", "D", "F"]` (A=90+, B=80+, C=60+, D=40+, F=<40)
>      * `label: Literal["🟢 Healthy", "🟡 Degraded", "🔴 Critical"]`
>    - `score_run(report: RunReport, observations: list[Observation], median_steps: Optional[float]) -> SniffScore`
>    - Module docstring explaining the formula and why these weights (see `sniff-expansion-plan.md` decision table)
>
> 2. Add `SniffScore` to `RunReport` in `sniff-ai/src/evidence/report_builder.py`:
>    - Compute score in `build_report()` after diagnosis is available
>    - Include `sniff_score` field in the report JSON
>
> 3. Update `SlackAlert` in `sniff-ai/src/alerts/slack.py`:
>    - Add score emoji bar to alert header: `🟢 92/100` or `🔴 24/100`
>    - Show score components in a collapsible block if score < 80
>
> 4. Add `sniff_score` column to Supabase `runs` table:
>    - Supabase migration SQL to add `sniff_score INT` to runs table
>    - Update `SupabaseUploader` to include score in run upload
>
> 5. Add `RunOverviewCard` score display in `sniff-web` (if Session 08 is done):
>    - Score displayed as a large number with grade letter
>    - Color: green (A/B), amber (C), red (D/F)
>    - Trend arrow if previous score is available
>
> 6. Add `sniff-ai/src/cli/commands/score.py`:
>    - `sniff score [run_id]` — display score breakdown for a run
>    - If no run_id, shows the most recent run
>    - Rich table output: score, grade, component breakdown
>
> Write tests for the scorer:
> - P0 run with TTFB penalty: verify exact score
> - Successful run with goal completion bonus: verify exact score  
> - Score clamped at 0 for catastrophic run
> - Score clamped at 100 for perfect run
> - Grade and label assignment

---

## Pre-Session Checklist

Before starting this session, verify:
- [ ] Session 05 is complete (three-tier architecture, `RunReport` structure is final)
- [ ] Read `sniff-ai/src/evidence/report_builder.py` before starting
- [ ] Read `sniff-ai/src/alerts/slack.py` before starting
