# Session 00: Bob Methodology — Project Setup & Security

## Bob Mode Used

**Plan Mode → Agent Mode**

This session was run in two phases. Plan mode was used first to decide *what* infrastructure files to create and why. Agent mode was then used to actually write all the files.

The split was deliberate: security infrastructure (`.gitignore`, `.bobignore`, ADR templates) demands careful thought before any code is written, because mistakes here (e.g. accidentally tracking a `.env` file) are hard to undo once they are in git history.

---

## Why Plan Mode First?

Plan mode's constraint — it cannot write files — kept this session focused on answering three questions before touching anything:
1. What patterns of sensitive data exist in this repo?
2. What should Bob itself never index (`.bobignore`)?
3. What ADRs need to exist before implementation begins?

Only after all three questions were answered did the session switch to Agent mode to write the files.

---

## Bob Tools and Techniques

### File Investigation
Bob read the existing repo structure before proposing any `.gitignore` patterns — it did not guess what file patterns might exist. This is the standard Bob "investigate before answering" discipline applied to infrastructure.

### Shell Execution
Bob ran a grep for existing committed secrets before writing the `.gitignore`, confirming zero secrets were already tracked. This is a real audit, not an assumption.

### Structured Output: ADR Format
The ADR template (`docs/adr/ADR-000-template.md`) was written by Bob following the standard ADR format (Status / Context / Decision / Rationale / Consequences). All subsequent ADRs follow this template exactly.

### Documentation-First Order
Three ADRs were written *before* any implementation:
- **ADR-001**: Three-tier intelligence architecture (decided before Session 05 wrote any code)
- **ADR-002**: Dependency update strategy (decided before Session 03 updated anything)
- **ADR-003**: APScheduler daemon (decided before Session 06 built the scheduler)

This is Bob being used in a documentation-first way: the decisions are written down and accepted before they are implemented, so the implementation has a traceable reason.

---

## Bob Configuration Files Created

### `.bobignore`
Bob's own ignore file — tells Bob not to index lock files (`uv.lock`, `yarn.lock`), secrets (`.env`, `*.key`, `*.pem`), and large auto-generated artifacts. Without this, Bob wastes context window space on high-noise files that add no value to code understanding.

### `.bob/CONTEXT.md`
The Bob context file gives Bob a brief project summary at the start of every session, so it does not need to re-read the whole codebase from scratch each time. It includes: project purpose, tech stack, key files, and the current state of the expansion plan.

---

## Key Bob Discipline Applied

**Security before features.** This session ran first (Session 00) because the plan called for security hygiene as the first sub-task. Bob followed the execution order from the expansion plan: `Sub-Task 11 (Security + Bob Files) → Sub-Task 1 (Rename) → ...`. The rationale: any accidental secret commit during fast-moving implementation sessions would be much harder to clean up if the `.gitignore` was not in place first.
