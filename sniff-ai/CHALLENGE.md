# Autonomous Mystery Shopper

## The Challenge

### How might we automate the detection of signup friction before a real user ever

### encounters it? What if your QA team never slept? What if a bot could feel

### frustration? What if bugs reported themselves to the right person instantly?

## The Problem

The mobile/web signup flow is the "front door" for any platform. Every day, potential users click
ads and land on your signup page. If the "Sign Up" button hangs for a few seconds, or
document upload fails on certain devices, you lose them forever.
Currently, discovering these issues relies on manual QA and in-person product reviews - or
worse, waiting for user complaints. By then, the opportunity is gone.
_"We test what we can, but there are thousands of device/browser/OS combinations. We
can't cover them all manually."
"A signup bug existed for two weeks before a user complained. How many people did
we lose silently?"
"When something breaks, we don't know if it's a server error, a UI glitch, or confusing
copy. Different problems need different teams."
"Our QA team can't test 24/7 across every country and language. Issues slip through."_
The core issue: manual QA doesn't scale to cover every device scenario, network condition, and
user journey. By the time bugs are discovered, users are already lost.

## Why This Matters Now

With the rise of Autonomous Agents and Multimodal AI, we no longer need humans to manually
click through every possible device scenario. We can build intelligent agents that:
● Traverse the app like real humans, using visual cues rather than hard-coded selectors
● Find the cracks in user experience before real users do
● Automatically escalate issues to the right team with full context
● Run continuously, testing different scenarios around the clock
This isn't just a Selenium script that checks if a button exists. This is an AI agent that "looks" at
the screen, attempts to sign up, and intelligently reports failures.

## The Opportunity

Build an Autonomous "Mystery Shopper" for Mobile & Web UX with three core capabilities:

1. Simulation:
    ● AI agent navigates the mobile signup flow purely using visual cues (Computer Vision)
    ● Mimics a confused first-time user rather than following a hard-coded script


```
● Handles dynamic UI elements that would break traditional automation
● Tests across different device types, screen sizes, and network conditions
```
2. Diagnosis:
    ● When the agent gets stuck, it understands WHY
    ● Server error (500)? → Backend issue
    ● UI glitch (button off-screen)? → Frontend/Design issue
    ● Copy ambiguity ("I don't know what to enter here")? → UX/Content issue
    ● Timeout or slow response? → Performance issue
    ● Document upload failure? → Integration issue
3. Escalation:
    ● The magic happens in the reporting
    ● Creates a dedicated channel or thread for the issue
    ● Uploads "evidence" (screenshots, screen recordings, logs)
    ● Tags the specific human responsible for that part of the journey
    ● Includes severity assessment and reproduction steps
The system should catch issues that manual QA would miss and route them to the right team
instantly.

## Constraints

```
Constraint Rationale
Must demo live Show the bot hitting a bug and the alert notification in
real-time.
AI must add value Must use AI (LLM/Vision) to navigate or diagnose. A
hard-coded script is not what we're looking for.
Must run mobile Must simulate a mobile environment (Mobile Web view or
Emulator). Desktop flows are not the priority.
Live alerting Output cannot just be a log file. Must be a live alert
(Slack/Teams) with rich media.
Staging environment only Test on provided staging URL. Do not unleash AI bots on
production.
```
## Questions Worth Considering

```
● Can the AI determine the "severity" of the bug? (A typo is lower priority, a broken Submit
button is critical)
● How does the bot handle CAPTCHA or OTPs?
● Can the bot take a screenshot of the exact moment the error occurred?
● Could this run continuously, testing a different country's flow every hour?
● Can it simulate different user personas (tech-savvy vs. confused first-timer)?
● How does it handle intermittent issues vs. consistent bugs?
```
## What Would Blow Our Minds

```
● Visual intelligence: Agent navigates purely by "looking" at the screen, not by element IDs
● User confusion detection: "The agent spent excessive time on this screen looking for the
next step" → UX issue flagged
```

● Smart severity scoring: Automatic P0/P1/P2/P3 classification based on impact
● Multi-language testing: Same flow tested in different languages, catching localisation
bugs
● Network condition simulation: Testing on slow 3G, intermittent connection, high latency
● 24/7 continuous monitoring: Different country/device combinations tested every hour
automatically
● Root cause intelligence: "This error is similar to Issue #1234 from last week - possibly
related"

---

## Implementation Approach (Current Decision)

- Build a **Python-first CLI** for v1 to minimize integration overhead and maximize shipping speed.
- Use a **modular monolith** architecture with these boundaries:
- CLI (control plane)
- Run Orchestrator (state machine + guardrails)
- Execution Worker (Playwright mobile actions)
- Agent Service (Bedrock decisioning)
- Diagnosis Engine (root cause + severity)
- Alert Service (Slack escalation)
- Keep the worker local and deterministic; the agent returns decisions only.
- Optionally use **Strands Python** in the Agent Service for tool orchestration, RAG, and memory patterns.
- Do not add cross-runtime Bun<->Python IPC in v1 unless Bun UX is a hard requirement.

## Build Priorities

1. End-to-end `sherlock run` with one signup journey.
2. Persona-driven decision loop with strict JSON action schema.
3. Failure diagnosis + P0-P3 severity.
4. Evidence bundle + Slack alert.
5. Deterministic `sherlock demo` path for judges.

## Reference

- Architecture spec: `ARCHITECTURE.md`
- Bedrock/Strands tradeoff research: `STRANDS_BEDROCK_REPORT.md`


