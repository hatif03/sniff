# Session 06: Bob Methodology — Scheduled Continuous Runs

## Bob Mode Used

**Agent Mode**

This session was planned but not yet executed at the time the bob_sessions documentation was written — see the session index. The prompt is fully specified and the methodology documented here is based on the planned approach.

---

## Bob Tools and Techniques

### ADR-Guided Implementation
The scheduler approach was decided in Session 01 (Plan mode) and captured in ADR-003 before any code was written. This session's implementation would follow that decision: APScheduler-backed in-process daemon, SQLAlchemy SQLite job store, PID file management.

The `prompt.md` explicitly references ADR-003 so that Bob starts the session knowing the decision was already made and does not re-open it.

### Existing Pattern Reuse: FastAPI + BackgroundTasks
The FastAPI dependency was added in Session 03 (as a forward-planning addition for sessions that would need it). Session 06 uses it for the webhook trigger endpoint, following the same `BackgroundTasks` pattern established in Session 12's `POST /runs` endpoint.

### CLI Command Registration Pattern
New CLI commands (`sniff schedule`, `sniff daemon`) follow the pattern established in the existing `sniff-ai/src/cli/` directory. Bob reads the existing command structure before writing new commands — not to copy-paste, but to match the Typer app registration pattern, help text style, and option naming convention.

### In-Memory SQLite for Tests
The scheduler tests are designed to use in-memory SQLite (`":memory:"` connection string) rather than the real file-backed `sniff_schedules.db`. This is a standard test isolation pattern — tests do not pollute the real schedule store and do not require filesystem cleanup.

---

## Note on Planned vs Actual Implementation

Sessions 06–10 were planned and have full `prompt.md` specifications, but the actual implementation was superseded or substantially changed in later sessions:

- **Session 06 (Scheduled Runs)**: The APScheduler in-process daemon approach (planned here) was **replaced** in Session 15 with a Cloud Scheduler + atomic tick endpoint design. The planned approach would have caused duplicate job execution on a multi-instance Cloud Run deployment. This is a real architectural change, documented in `bob_sessions/architecture.md`.

The methodology lesson: plans made before deployment context existed (APScheduler was decided in Session 01, before Cloud Run was chosen in Session 13) may need to be revised once deployment constraints are known. Bob's job is to notice the conflict and fix it, not to blindly implement the originally planned approach.
