# Session 05: Bob Methodology — Three-Tier Intelligence Architecture

## Bob Mode Used

**Agent Mode**

This session is the most technically sophisticated in the project. Bob did not invent the routing design — it grounded the design in real, published patterns from academic and industry sources.

---

## Bob Tools and Techniques

### Research-Grounded Design (Not Invented Architecture)
Before writing any routing code, Bob researched existing named patterns for multi-tier AI routing. Two sources reviewed:
- Google Developers Blog's "4 Engineering Patterns Behind the Strongest AI Agents Challenge Submissions"
- Google Cloud's "Choose a design pattern for your agentic AI system"

Plus Typesafe's own documented patterns:
- "Speculative Fan-Out" — batch multiple questions in one Jev call; adding more barely changes latency
- "Confidence-Gated Routing" — escalate to a more powerful model when confidence is below threshold

**Important attribution note captured in the session summary**: Typesafe's own docs don't claim a three-tier architecture. The three-tier framing (with deterministic code as its own tier) is this project's synthesis, informed by the 2025-2026 model-cascade/routing literature. Bob explicitly flagged what to attribute to Typesafe vs what was the project's own design.

### Minimal Diff Principle
The original prompt asked Bob to rename `DecisionService` to `TieredDecisionService`. Bob rejected this change: it would have broken all existing callers and tests unnecessarily. Instead, `TierRouter` was injected into the existing `DecisionService` as an optional constructor parameter defaulting to `None`/disabled. Same effect, smaller diff, all existing callers keep working.

This is the engineering discipline principle applied: **produce the minimal change that solves the problem**. Bob justified the deviation from the prompt with the reason, not just the decision.

### Reading Existing Code Before Writing New Code
A key finding emerged from reading `DiagnosisClassifier` before writing the `_classify_ambiguous_root_cause_jev()` method the prompt requested: the class was *already* 100% deterministic rule trees with zero LLM involvement, despite its own docstring claiming "hybrid... optional LLM interpretation."

Bob's response: **fix the docstring, don't add a new code path**. Adding a Jev branch to code that already works correctly as pure deterministic rules would have been speculative complexity — a new mechanism to reason about, maintain, and test, solving a problem that does not exist.

### Named Pattern Application: Three Jev Roles
Rather than one generic `route() → Tier` dispatcher, Bob implemented Jev in three distinct roles, each mapped to a named pattern:

- **Role D (ReAct Observation interpreter)**: `check_goal_reached()` — the old keyword-search false-negative bug (missed "Welcome aboard!" because it's not literally "success"). Keyword match still short-circuits for free; Jev decides when it's weak. This maps to the ReAct agent observation interpretation pattern.
- **Role B (Speculative Fan-Out / Parallel Context Enrichment)**: Before the expensive Gemini call, one batched Jev call pre-classifies screen type / error-visibility / clutter, folded into the Gemini prompt as pre-digested context. This is Typesafe's own "Speculative Fan-Out" pattern.
- **Role C (Generator-Critic Gate)**: After Gemini returns a decision, a cheap Jev `noul()` sanity-checks it. Low confidence triggers `DecisionService`'s existing repair-retry loop (not a new mechanism). This is the Generator-Critic pattern from the Google agents research.

### Reuse of Existing Mechanisms
The critic gate (Role C) reuses `DecisionService`'s existing repair-retry loop — the same loop already used for JSON schema validation failures. Rather than building a second retry path, Bob plugged the new critique trigger into the existing bounded-retry policy. One retry policy to reason about instead of two.

### Documented Gap: Tiered Routing Shortcut Deliberately Deferred
The Google blog described a "Tiered Routing" shortcut (~40% of decisions resolved before any model call in their reported case). Bob identified this as worth doing but deliberately deferred it, with explicit reasoning: it requires Jev to name a concrete target element, which requires structured candidate-element list exposure that `Observation` does not yet provide (`visibleText` is just strings). This is not silently dropped — it is documented as a real prerequisite, and `TierRouter` is structured so the feature slots in later.

### Live End-to-End Verification
Bob verified the routing with real credentials:
- `TierRouter.enrich_context()` correctly classified a signup form screen (confidence 1.0)
- `check_goal_reached()` correctly recognised "Welcome aboard! Your account is ready" as goal-reached via Jev where the old keyword-only check would have missed it (the false-negative bug being fixed)

---

## Key Bob Discipline Applied

**Fix the docstring, not the code.** When the existing code is correct but the documentation is wrong, the correct action is to fix the documentation. Adding a new code path to code that already works would have created complexity without solving a real problem.

**Name your patterns.** Using published names (ReAct, Speculative Fan-Out, Generator-Critic, Confidence-Gated Routing) makes architectural decisions reviewable and reproducible. Someone reading this codebase later can look up the named pattern and understand the design intent.
