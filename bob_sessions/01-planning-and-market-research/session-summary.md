# Session 01: Planning & Market Research

**Session Type:** Plan Mode  
**Status:** ✅ Complete  
**Coins Used:** ~1.2  
**Date:** 2025  

---

## Objectives

1. Explore the full codebase to understand the current state
2. Perform competitive market research
3. Identify feature gaps and potential customers
4. Design the expansion plan with confirmed architectural decisions
5. Produce `sniff-expansion-plan.md` as the single source of truth

---

## Codebase Audit Findings

The existing project was fully functional but had the internal name **"sherlock"** everywhere — package name, class names, env vars, CLI entry point, Slack bot name, Supabase bucket names, and all documentation. The public brand "Sniff" was only used in the folder name (`sniff-web/`, `sniff-ai/`).

**Architecture found:**
- Python modular monolith (`sniff-ai/`) with Playwright + AWS Bedrock Claude
- Single-tier AI: every navigation decision went to Claude (expensive, slow)
- State machine orchestrator with clean agent/executor separation
- Next.js dashboard (`sniff-web/`) with Supabase storage
- Typer CLI with 9 commands (`sherlock run`, `sherlock init`, etc.)
- Comprehensive test suite: 67 tests (all passing once path was fixed)

---

## Market Research

### Competitive Landscape

| Competitor | Type | What to Learn |
|---|---|---|
| **ColdVisit** (coldvisit.com) | AI mystery shopper for B2B sales flows | Journey replay, scheduled runs, natural language summaries, baseline regression comparison |
| **Rainforest QA** | No-code AI test automation | Parallel multi-persona runs, self-healing selectors |
| **Mabl** | Intelligent test cloud | Auto-healing, "journey health" score (equivalent to Sniff Score) |
| **Testim** | AI-assisted E2E testing | Smart locators, root cause analysis |
| **Playwright/Cypress** | Test frameworks | Fast, deterministic — but no AI navigation |
| **FullStory / Ghostery** | Session recording | Real user sessions but reactive only, no simulation |
| **BrowserStack** | Cross-device testing | Real device farms, no AI |

### ColdVisit Key Learnings

ColdVisit is the closest analog to Sniff. Key features we should adopt:
- **Journey replay**: Full visual step-by-step playback (our Session 08)
- **Scheduled runs**: Cron-triggered continuous testing (our Session 06)
- **Natural language summaries**: Human-readable issue reports
- **Baseline regression**: Compare run N to run N-1 (our Session 07)
- **Multi-step funnel definition**: Define checkpoint milestones

**Sniff's advantages over ColdVisit:**
- Persona system (confused/impatient/careful user personas)
- Mobile device emulation (Playwright)
- Severity classification (P0–P3)
- Root cause diagnosis engine

### Potential Customer Segments

| Segment | Pain Point | Why Sniff |
|---|---|---|
| SaaS startups | High signup drop-off, no QA team | Proactive, automated |
| Growth teams | Can't reproduce user-reported friction | Persona-driven simulation |
| Mobile-first companies | Mobile signup ≥40% of traffic | Playwright mobile emulation |
| Enterprise onboarding | Complex multi-step flows | Careful/confused personas |
| Dev agencies | Need to deliver QA for client projects | Persona test reports |
| Product managers | No visibility into signup quality | Scheduled continuous runs |

---

## Architectural Decision: Three-Tier Intelligence

The single most important architectural insight from this session:

> **Current state**: Every navigation step (even trivial ones like "tap the Sign Up button") calls AWS Bedrock Claude. For a 50-step run, that is 50 full LLM invocations.

> **Problem**: Expensive (~$0.30/run), slow (2–5s latency per step), overkill (most decisions don't need deep reasoning).

> **Solution**: Three-tier routing — Deterministic → Jev → Claude

| Tier | Technology | When | Examples |
|---|---|---|---|
| 1 — Deterministic | Pure Python | Signal extraction, guardrail checks | "Is TTFB > 5s?", "Is this a 4xx?" |
| 2 — Jev (System One) | Typesafe AI Jev | Fast navigation decisions | "Which element to tap?", "Is agent stuck?" |
| 3 — Claude (System Two) | AWS Bedrock | Deep reasoning | Root cause diagnosis, persona review narrative |

This was captured in **[ADR-001](../../docs/adr/ADR-001-three-tier-architecture.md)**.

---

## Confirmed Decisions (from user follow-up)

| Question | Decision | Rationale |
|---|---|---|
| Typesafe AI key | Available — implement fully | No need to stub |
| UI vs CI/CD priority | Journey Replay (Session 08) first | Higher user value, ColdVisit parity |
| Tailwind version | Upgrade to v4 | Modern standard, avoid tech debt |
| Sniff Score weights | P0=−50, P1=−25, P2=−12, P3=−5, success=+10 | Severe penalty for blockers |
| Scheduler | APScheduler in-process daemon | Works in Docker/cloud, no OS cron dependency |
| Documentation | ADR files + module docstrings on every change | Traceability for all decisions |
| Security | .gitignore + .bobignore | First sub-task executed |

---

## Outputs

### Files Created

| File | Purpose |
|---|---|
| `sniff-expansion-plan.md` | Full 11-subtask roadmap with intents, expected outcomes, todos |
| `docs/adr/ADR-001-three-tier-architecture.md` | Architectural decision for Tier 1/2/3 model |
| `docs/adr/ADR-002-dependency-updates.md` | Dependency update and Tailwind v4 strategy |
| `docs/adr/ADR-003-scheduler-apscheduler.md` | APScheduler vs OS cron decision |

### Feature Roadmap Identified (11 Sub-Tasks)

```
ST11 (Security)  →  ST1 (Rename)  →  ST2 (Deps)  →  ST3 (Jev)  →  ST4 (Three-Tier)
                                                                            ↓
                                              ST5 (Scheduler) + ST6 (Regression) + ST7 (Replay) + ST9 (Score)
                                                                            ↓
                                                                     ST8 (CI/CD)  →  ST10 (Docs)
```

---

## Deviations from Original User Request

None — all scope items from the original prompt were addressed and planned. The user's clarifying follow-up answers were all incorporated before writing the plan file.

---

## Next Steps

→ Session 02: Full rename (sherlock → sniff)  
→ Session 03: Dependency updates + Tailwind v4 migration
