# Session 07: Bob Methodology — Baseline Regression Detection

## Bob Mode Used

**Agent Mode**

This session was planned but not yet executed at the time the bob_sessions documentation was written. The prompt is fully specified.

---

## Bob Tools and Techniques

### Data Model First
The `RegressionResult` Pydantic model is designed before the `RunComparator` logic. This is deliberate: defining the output shape first forces clarity about what the comparator needs to produce, which in turn clarifies what inputs it needs.

The model captures five distinct change dimensions: severity change, severity delta (direction and magnitude), new issues (appeared in current), resolved issues (gone from current), step count delta, score delta, and an `is_regression: bool` flag. Designing all of these up front prevents the common mistake of discovering mid-implementation that the model is missing a needed field.

### Supabase Query Pattern for Baseline Selection
The `RunOrchestrator` update to auto-load the previous run uses Supabase's existing client from `src/integrations/supabase_client.py`. The query pattern: fetch the most recent run with the same `goal_hash` + `persona` combination, excluding the current run.

Bob reads `supabase_client.py` before writing this query — not to guess the client API, but to use the exact same query builder pattern that already exists in the codebase.

### CLI Exit Code Contract
The `sniff compare` command exits with code 1 when a regression is detected. This is the same exit-code-as-signal contract used by the CI/CD integration in Session 10 (`sniff run --exit-on-severity`). Establishing this contract early means CI pipelines can use `sniff compare` as a release gate without additional scripting.

### Graceful No-Baseline Handling
The comparator is designed to handle the "no baseline available" case gracefully — returning a `RegressionResult` with `is_regression: False` and an explanatory `summary` string. This is important for first-time runs against a new goal/persona combination, which by definition have no baseline.

---

## Note on Relationship to Session 15

The "baseline regression comparison" item from `docs/product/MARKET_RESEARCH.md`'s backlog was noted in Session 15's summary as "substantially addressed by the Trends tab and score-history chart." The `RunComparator` as a discrete CLI command is one approach; the Trends tab's audit-score history chart serves a similar purpose for the web product surface. Both are valid and complementary.
