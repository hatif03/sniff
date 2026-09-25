# Session 01: Architecture — Three-Tier Intelligence Model

This document captures the architectural design produced during the planning session. It supplements [ADR-001](../../docs/adr/ADR-001-three-tier-architecture.md) with fuller context and diagrams.

---

## Current Architecture (Before Expansion)

```
┌─────────────────────────────────────────────────┐
│                  Sniff CLI (Typer)               │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│           RunOrchestrator (State Machine)        │
│  SETUP → NAVIGATE → ACTION_EXECUTION →           │
│  EVALUATE_PROGRESS → (loop) → DIAGNOSE →        │
│  ALERT → REPORT → DONE                          │
└──────────┬────────────────────────┬─────────────┘
           │                        │
           ▼                        ▼
┌──────────────────┐    ┌──────────────────────────┐
│ PlaywrightWorker │    │   DecisionService         │
│ (Executor)       │    │   (Agent — Bedrock only)  │
│ - Navigate       │◄───│   - Every step → Claude   │
│ - Tap/Type/Scroll│    │   - ~50 Claude calls/run  │
│ - Screenshots    │    │   - Expensive + slow      │
└──────────────────┘    └──────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────┐
│  DiagnosisClassifier → SlackAlert → ReportBuilder │
└──────────────────────────────────────────────────┘
```

**Problem with current state:**
- 50-step run = ~50 Claude invocations = ~$0.30/run
- 2–5 seconds per step just in model latency
- 80% of decisions are trivial navigation (tap button, fill field) — don't need Claude

---

## Target Architecture (Three-Tier Intelligence)

```
┌─────────────────────────────────────────────────────────┐
│                    Sniff CLI (Typer)                     │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              RunOrchestrator (State Machine)             │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│           TieredDecisionService                          │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              TierRouter                           │   │
│  │  route(observation, context) → Tier              │   │
│  │  Rules:                                           │   │
│  │  - Deterministic signal? → Tier 1                │   │
│  │  - Simple navigation? → Tier 2 (Jev)             │   │
│  │  - Diagnosis / narrative? → Tier 3 (Claude)      │   │
│  │  - Jev confidence < 0.75? → Tier 3 fallback      │   │
│  └───────────┬──────────────┬──────────────────────┘   │
│              │              │              │              │
│              ▼              ▼              ▼              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │
│  │   Tier 1     │ │   Tier 2     │ │   Tier 3     │     │
│  │ Deterministic│ │    Jev       │ │   Claude     │     │
│  │ Pure Python  │ │ Typesafe AI  │ │ AWS Bedrock  │     │
│  │              │ │ Fast heuristic│ │ Deep reasoning│    │
│  │ ~0ms, $0     │ │ ~200ms, ~$0  │ │ ~3s, ~$0.006 │     │
│  └──────────────┘ └──────────────┘ └──────────────┘     │
└─────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│           PlaywrightWorker (unchanged)                   │
└─────────────────────────────────────────────────────────┘
```

---

## Decision Routing Matrix

| Situation | Tier | Why |
|---|---|---|
| "Is TTFB > 5000ms?" | 1 — Deterministic | Pure arithmetic |
| "Has step count exceeded max?" | 1 — Deterministic | Pure arithmetic |
| "Is this HTTP 4xx?" | 1 — Deterministic | Pure string/int check |
| "Which element should I tap next?" | 2 — Jev | Fast pattern matching, no deep reasoning needed |
| "Is this the email field?" | 2 — Jev | Pattern recognition |
| "Is the agent stuck in a loop?" | 2 — Jev | Heuristic based on recent action history |
| "Which form field maps to this input?" | 2 — Jev | Fast matching |
| "What is the root cause of this failure?" | 3 — Claude | Requires synthesis of many signals |
| "Write the persona's experience narrative" | 3 — Claude | Open-ended generation |
| "Is this P0 or P1?" | 3 — Claude | Ambiguous severity judgement |

---

## Expected Cost/Latency Impact

| Scenario | Before (Claude only) | After (Tiered) | Saving |
|---|---|---|---|
| 50-step run, all navigation | ~50 Claude calls | ~40 Jev + 10 Claude | ~80% cost reduction |
| Run latency (model only) | ~150s model time | ~30s model time | ~80% faster |
| Diagnosis (1 Claude call) | 1 call | 1 call | No change |
| Persona review narrative | 1 call | 1 call | No change |

---

## Jev Skill Definitions (Planned for Session 04)

Three skills to be defined in `sniff-ai/src/agent/skills/`:

### 1. `navigation_decision.skill`
**Input:** Observation (screenshot, visible text, URL, goal)  
**Output:** Action type + target (tap/type/scroll/wait/abort)  
**Used:** Every navigation step where context is sufficient

### 2. `stuck_detector.skill`
**Input:** Last N action results + current observation  
**Output:** `is_stuck: bool`, `stuck_reason: str`, `confidence: float`  
**Used:** At EVALUATE_PROGRESS state to detect loops

### 3. `element_selector.skill`
**Input:** Visible text list + goal + action type  
**Output:** Best matching element selector + confidence  
**Used:** When a tap or type action needs to pick from multiple candidates

---

## New Component Map

After all sessions are complete, the component map will be:

```
sniff-ai/src/
├── agent/
│   ├── bedrock_client.py       # Tier 3 (unchanged)
│   ├── decision_service.py     # → TieredDecisionService (Session 05)
│   ├── jev_client.py           # Tier 2 (Session 04)
│   ├── tier_router.py          # Routing logic (Session 05)
│   └── skills/                 # Jev skill definitions (Session 04)
│       ├── navigation_decision.skill
│       ├── stuck_detector.skill
│       └── element_selector.skill
├── core/
│   ├── config.py               # SniffConfig + TypesafeConfig (Sessions 02, 04)
│   └── ...
├── evidence/
│   ├── report_builder.py       # + SniffScore (Session 09)
│   ├── scorer.py               # New: SniffScore formula (Session 09)
│   └── comparator.py           # New: RunComparator (Session 07)
├── scheduler/                  # New: APScheduler daemon (Session 06)
│   └── scheduler.py
└── cli/commands/
    ├── daemon.py               # New: sniff daemon (Session 06)
    ├── schedule.py             # New: sniff schedule (Session 06)
    ├── compare.py              # New: sniff compare (Session 07)
    └── score.py                # New: sniff score (Session 09)

sniff-web/
└── app/
    └── runs/
        └── [run_id]/
            └── replay/         # New: Journey replay UI (Session 08)

sniff-action/                   # New: GitHub Actions plugin (Session 10)
├── action.yml
├── Dockerfile
└── entrypoint.sh
```
