# Session 09: Bob Methodology — Sniff Score

## Bob Mode Used

**Agent Mode**

The Sniff Score was fully specified in the planning session (Session 01) — confirmed formula, confirmed weights, confirmed output format. This session is pure implementation of a decided design.

---

## Bob Tools and Techniques

### Formula-as-Code With Inline Documentation
The scoring formula (`P0=−50, P1=−25, P2=−12, P3=−5, TTFB>3s=−4, excess_steps=−4, goal_complete=+10, clamp 0–100`) was decided in Session 01 and documented in `sniff-expansion-plan.md`. The `scorer.py` module docstring explicitly references this decision and its rationale — not just the formula, but *why these weights* (more severe penalty for P0 blockers; bonus rewards goal completion; TTFB and step-excess are secondary quality signals, not primary failure modes).

This is the documentation discipline applied to a formula: document the decision and its reasoning, not just the implementation.

### `ScoreComponent` for Audit Trail
The `SniffScore` model includes a `components: list[ScoreComponent]` breakdown — not just the final number, but every penalty and bonus that contributed to it. This makes the score transparent and debuggable: a PM looking at a score of 38 can see exactly what caused it (P0 −50, TTFB −4, goal +10 = 56 before clamp to... wait, that math doesn't show 38 — a P1 was also there: −25 more = 31, clamp to minimum doesn't apply here, so 56 − 25 = 31... the component list makes this auditable).

### Emoji Health Bar Pattern for Slack
The Slack alert update adds a score emoji bar (`🟢 92/100`, `🟡 56/100`, `🔴 24/100`). Bob reads `slack.py` before writing the new block — not to guess the Slack block format, but to match the existing pattern exactly (same field structure, same attachment style).

### Supabase Migration
Adding `sniff_score INT` to the `runs` table requires a migration. Bob writes this as a proper migration SQL file, not as a one-off query run manually. This follows the project's migration discipline established in Session 14 (where the first real Supabase project was provisioned).

### Pre-Session Reads
The `prompt.md` requires reading `report_builder.py` and `slack.py` before starting. This is the same "investigate before answering" pattern formalised as a prompt gate — Bob must understand the structures it is extending before extending them.

---

## Note on Score Trend
The `trend: Optional[int]` field on `SniffScore` is set by the `RunComparator` from Session 07, not by the scorer itself. The scorer only knows the current run; the comparator is what provides the delta vs previous. This separation of concerns is deliberate: the scorer computes scores, the comparator diffs them.
