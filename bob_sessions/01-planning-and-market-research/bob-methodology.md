# Session 01: Bob Methodology — Planning & Market Research

## Bob Mode Used

**Plan Mode (exclusively)**

Session 01 was the most important planning session in the project. It used Plan mode from start to finish — the entire session was about thinking, researching, and deciding, not about writing code.

Plan mode was the right tool here because:
1. The user's prompt spanned multiple topics (rename, market research, competitor analysis, architecture, package updates, new AI model integration) that needed to be organised into a coherent, sequenced plan before any implementation started
2. Architectural decisions made here (three-tier model, APScheduler, Sniff Score weights) needed to be durable — they should not change with every session
3. Plan mode's "no file writes" constraint forced a documentation-only output, which is exactly what `sniff-expansion-plan.md` needed to be

---

## Bob Tools and Techniques

### Web Browsing (Competitor Research)
Bob browsed ColdVisit's website (`coldvisit.com`) and its docs to extract features, positioning, and what the app paywalls. This was real research, not guesses. The findings directly shaped the feature roadmap:
- Journey replay UI → Session 08
- Scheduled continuous runs → Session 06
- Baseline regression detection → Session 07
- Natural language summaries → embedded in diagnosis output

Bob also researched Rainforest QA, Mabl, Testim, Playwright/Cypress, FullStory, BrowserStack, Heap, and Mixpanel to understand the full competitive landscape.

### Codebase Audit in Plan Mode
Bob read the entire existing codebase before writing the plan. Key findings that shaped the plan:
- Every navigation step called AWS Bedrock Claude — even trivial ones like "tap the Sign Up button"
- No public brand name existed anywhere (only folder names `sniff-web/`, `sniff-ai/`)
- The test suite had a pre-existing import error (`PersonaManager` imported but not implemented)
- The project had a comprehensive state machine orchestrator but a single-tier AI pipeline

### Clarifying Questions (Follow-Up Prompt)
Bob generated a set of clarifying questions after the initial prompt, which the user answered:
- Is the Typesafe AI key available? → Yes, implement fully
- Journey Replay vs CI/CD priority? → Journey Replay first
- Tailwind version? → v4
- Sniff Score weights? → Confirmed formula
- Scheduler approach? → Left to Bob; Bob chose APScheduler

This Q&A loop is a core Plan mode pattern: produce a near-complete plan, identify the remaining decision points, get them resolved before finalising.

### ADR Authoring
Three ADRs were authored in this session as part of the planning output:
- **[ADR-001](../../docs/adr/ADR-001-three-tier-architecture.md)**: The three-tier intelligence model
- **[ADR-002](../../docs/adr/ADR-002-dependency-updates.md)**: Dependency update strategy and Tailwind v4 migration
- **[ADR-003](../../docs/adr/ADR-003-scheduler-apscheduler.md)**: APScheduler daemon vs OS cron

ADRs were written in the same session as the plan, not deferred to later, because the decisions were already made and needed to be captured while the reasoning was fresh.

### Single-Output Discipline
The entire session's output was one file: `sniff-expansion-plan.md`. This is an intentional Plan mode pattern — produce one authoritative document that every subsequent Agent mode session can reference, rather than scattering decisions across multiple loose notes.

---

## Architectural Decision: Three-Tier Model (Session 01, Before Any Code)

The most important architectural decision in the whole project was made in this session, in Plan mode, before a single line of code was written for it:

> Every navigation step calling AWS Bedrock Claude is expensive, slow, and overkill for routine steps. Split into three tiers: deterministic code → Jev (fast decision model) → Claude (reasoning).

This decision was captured in ADR-001, accepted, and then implemented across Sessions 04 and 05. The fact that it was decided and documented first — not discovered during implementation — meant Sessions 04 and 05 had clear success criteria before they started.

---

## How the Plan Mode Output Was Used

`sniff-expansion-plan.md` became the reference for every subsequent session:
- Sessions 02–10 each reference a specific "Sub-Task N" from the plan
- The session index in `bob_sessions/README.md` tracks actual status vs planned status
- Deviations from the plan (e.g. the APScheduler approach being replaced by Cloud Scheduler in Session 15) are documented in session summaries with reasons

This is the "plan in Plan mode, execute in Agent mode" pattern at its purest.
