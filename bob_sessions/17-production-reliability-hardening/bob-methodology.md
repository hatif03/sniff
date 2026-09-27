# Session 17: Bob Methodology — Production Reliability Hardening

## Bob Mode Used

**Agent Mode**

This session had no plan-mode phase — every fix was driven directly by a real, user-reported production failure or a real failure Bob caused itself while seeding demo data. It is the clearest example in the project of live production evidence, not specification, driving the diagnosis.

---

## Bob Tools and Techniques

### Root-Cause Investigation From Production Data, Not Assumption
Given a screenshot of a failed run and a vague "see what happened," Bob did not guess. It queried the live `runs`/`observations`/`diagnoses` Supabase tables directly via REST (the public read-only anon key — the same access any dashboard visitor already has) and pulled the exact Cloud Run log window for that request. The failure's shape (one real observation, zero `agent_reasoning` rows, a guardrail violation with no prior error) was reconstructed from real data before any code was touched. Only after that reconstruction did Bob form and confirm a hypothesis: a blocking call inside an async handler.

### Confirming a Hypothesis With Direct Evidence, Not Inference Alone
Bob's theory — that a blocking LLM call froze the event loop — was not just inferred from reading code. It was confirmed by a specific, independent piece of live evidence: a *concurrent, unrelated* request (a status poll) logged 36.8 seconds of latency in Cloud Run's own request logs, for an endpoint that does nothing but read an in-process dict. That number, found in the platform's own structured logs, is what turned "the code looks like it could block" into "this is confirmed to have actually blocked everything."

### Root Cause Once, In the Shared Function
Both fixes in this session (the blocking-call fix and the screenshot resilience fix) were applied at the one shared function every caller already routes through — `GoalEnhancer.enhance_goal`'s call site and `PlaywrightWorker.screenshot()` respectively — rather than patched at each symptom. This is the same discipline session 16 applied to the k2-horizon client fix, applied twice more here to two unrelated subsystems.

### A Second Live Bug Found By Doing the Requested Task, Not By Searching For Bugs
The job-queue problem was not hunted for. It was discovered as a direct side effect of doing exactly what was asked — seeding real demo audits — and noticing the results didn't match what was sent. This is the same pattern as session 16's four live-discovered bugs: real usage, not code review, is what surfaced it.

### Correct Scope Boundary, Then Correct Scope Expansion on Request
Bob found the screenshot-timeout failure and the concurrent-execution failure in the same seeding attempt, reported both clearly with the exact evidence (Cloud Run log lines), and did not silently start rearchitecting the execution model on its own initiative. Once the user explicitly asked for a queue and screenshot resilience, Bob built both properly — real implementation, real tests, real deployment — rather than a minimal patch. The same boundary session 16 documented for the k2-horizon bug (document first, fix fully once asked) held again here.

### A Regression Test Proves the Actual Guarantee, Not Just "It Still Works"
For the queue, Bob did not write a test that merely confirms an audit still completes. It wrote a test with a tracking fake orchestrator that records the maximum number of jobs simultaneously in flight, and asserted that number is exactly 1 — a test that would fail immediately if the queue silently allowed concurrency back in. This is a deliberately stronger claim than "the existing tests still pass."

### A Real Linter Catching a Real Bug Mid-Fix
While wrapping a second blocking call in `run_in_executor`, Bob introduced a genuine bug: a redundant local `import asyncio` elsewhere in the same function made the name function-scope-local everywhere in that function, which would have raised `UnboundLocalError` the first time that code path ran. `ruff check` caught this before it was committed or deployed — a concrete instance of running the full verification pipeline (lint + test) on every change, not just the specific lines touched.

### Closing the Loop With the Original Failure
The session did not end at "the unit tests pass." Bob re-ran the exact goal and URL from the user's original bug report against the fixed, deployed backend, closing the loop on the specific complaint rather than treating a passing test suite as sufficient proof.

---

## Key Bob Discipline Applied

**A failed run report is a starting point for investigation, not a ticket to triage by symptom.** The literal user ask was "see what happened" — Bob treated that as license to pull real logs and real data until the actual mechanism was found, rather than stopping at the first plausible-looking explanation (the guardrail message) and fixing the guardrail's message instead of the reason it fired.
