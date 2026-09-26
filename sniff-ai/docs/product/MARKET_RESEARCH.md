# Sniff Market Research

Competitive landscape, customer segments, and a prioritized feature backlog.
Findings below come from live research (fetched competitor sites/docs and
searched current positioning) - not assumptions carried over from an
earlier draft of this doc's ideas.

## Competitive landscape

| Product | What it actually does | Key differentiator | Gap vs. Sniff |
|---|---|---|---|
| **ColdVisit** | PR-preview-deploy regression testing: a browser agent runs user-defined "flows" against Vercel/Railway/Render preview URLs as a GitHub check, with selector auto-healing and pass/fail/couldn't-run outcomes. **Not** a persona-driven mystery-shopper tool - no personas, no scheduling beyond PR-trigger, no funnel/regression-baseline comparison, no journey-replay UI in its public docs. | Ships as a GitHub check gating merges | No persona system, no root-cause/severity diagnosis, no continuous/scheduled runs, no onboarding-funnel focus |
| **Momentic** (YC W24, ~$19.2M raised) | Natural-language E2E/visual/API/accessibility test authoring; agents read the DOM + accessibility tree + screenshots + network + console to judge correctness instead of relying on selectors. | Closest architectural analog to Sniff - non-selector-based agent judgment | No persona/behavioral simulation, no mobile-network-condition emulation, not focused on signup/onboarding specifically |
| **Mabl** | "AI-native" enterprise continuous-testing platform: web/mobile/API/accessibility/performance in one product; claims large reductions in test-maintenance work via auto-healing. | Broad enterprise coverage in one product | No persona modeling, no onboarding-specific root-cause diagnosis |
| **Rainforest QA** | No-code AI testing for teams without dedicated QA engineering; AI generates test plans and self-healing E2E tests. | Low setup effort for non-technical teams | Deterministic once authored; no autonomous exploration or persona behavior |
| **Testim** (now part of Tricentis) | Acquired by Tricentis in 2022, fully folded into the Tricentis portfolio as of 2026 (Testim Web/Mobile/Salesforce); pricing is contact-sales only. | Salesforce-specific testing | Enterprise-sales-motion product, not self-serve; no persona/signup focus |
| **BrowserStack** | Cloud cross-browser/real-device execution grid; publishes an annual "State of AI Testing" report. | Massive device/browser coverage | Requires scripted tests; AI layer is additive, not the core product |
| **QA Wolf** | Fully-managed automated browser testing service with a "zero-flake" guarantee. | Outsourced/managed-service model - QA Wolf runs and maintains the tests | Not self-serve; no persona-driven exploration |
| **Applitools** | Visual-AI regression testing, designed to plug into existing Selenium/Cypress/Playwright test suites rather than replace them. | Visual diffing precision | Requires an existing test suite; not autonomous |

**Positioning takeaway**: Sniff's persona-driven (confused/impatient/careful
user), scheduled-capable, Slack-alerting, root-cause-and-severity-diagnosing
approach *specifically for signup/onboarding* is more differentiated than
any single competitor above covers end-to-end. The closest real competitor
on agent architecture (non-selector-based judgment) is Momentic; the
closest on "runs against your app automatically" is ColdVisit - but neither
combines persona simulation with automated severity/root-cause triage and
team-routed Slack escalation.

## Customer segments and purchase triggers

- **Mid-market SaaS growth/product teams** - past a recent signup-flow
  incident or embarrassment, or growing deploy velocity outpacing manual QA
  capacity. This is the sweet spot most competitors above also target
  (Testim/Rainforest/Momentic).
- **Teams without dedicated QA engineering** - the value is catching
  signup-blocking bugs *before* a real user does, without hiring a QA org.
- **Mobile-first products** - mobile signup often carries the highest
  device/network fragmentation and the highest cost of a broken flow.

Overall market context: SaaS-testing-tooling is sized around $4B and
growing at roughly 14% CAGR per aggregated industry estimates (directional,
not traced to one primary source - treat as context, not a precise figure).

## Feature backlog (not built this pass)

Each item below is a real gap relative to the competitive landscape, listed
with rationale and a rough effort note. None of these were implemented in
this pass - the priority was getting the rename, dependency refresh, and
three-tier decision architecture (see `ARCHITECTURE.md` Section 7A) right
first, rather than diluting that work across a dozen small features.

| Feature | Rationale | Rough effort |
|---|---|---|
| Scheduled/continuous runs | `apscheduler`, `fastapi`, and `uvicorn` are already dependencies (anticipated, unused) - a daemon that re-runs a goal on a schedule and diffs against the last result | Medium - mostly wiring already-installed deps |
| Baseline/regression comparison | Compare a run against the previous run for the same goal to flag new failures, not just failures in isolation | Medium - needs a run-history store, which Supabase integration already provides |
| Journey-replay UI | Step-by-step visual playback of a run in `sniff-web`, closest analog to what ColdVisit and session-replay tools show | Larger - needs a dashboard view over stored screenshots/trace data |
| "Sniff Score" | A single 0-100 UX-health number per run, trended over time, for a fast at-a-glance status | Small-medium - a scoring function over existing `DiagnosisResult`/step data |
| CI/CD GitHub Action | Run Sniff against a PR preview URL as a merge gate, the same wedge ColdVisit uses | Medium-large - needs a packaged action, exit-code contract, and a preview-URL discovery step |
