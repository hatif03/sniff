# Session 14: Bob Methodology — UI Reimagine, Shared Persistent Data, Web-First Messaging

## Bob Mode Used

**Agent Mode**

This session demonstrates the "investigate before building" principle most clearly of any session in the project. Three major decisions were changed by reading the actual code before proposing any solution.

---

## Bob Tools and Techniques

### Three Investigate-Before-Build Findings

All three major decisions this session came from reading the actual code, not from accepting the framing in the user's request:

**Finding 1 — No new libraries needed.**
The user noticed the UI was "awful" and might expect new libraries to be installed. Bob read `sniff-web/package.json` first. All needed libraries were already there:
- `shadcn/ui` (Radix): already installed
- `framer-motion`: already used throughout all 7 marketing sections
- `gsap`: installed but imported **nowhere** — dead weight
- Recharts: already used correctly in two dashboard components

The real gap was that the marketing sections had never adopted shadcn primitives — they were hand-rolled `<div>`s reimplementing `Card`/`Badge`/`Button`. The fix was using what was already installed, not adding new dependencies. Bob removed `gsap` as dead weight rather than adopting a second animation library.

**Finding 2 — "Show everything to everyone" was blocked by persistence, not auth.**
The user asked why runs/audits were not visible to everyone. Bob read the code: the dashboard already read a public-read Supabase view for runs — but no real Supabase project had ever been created (`SUPABASE_ENABLED=false`, no `SUPABASE_URL` anywhere). Audits were worse: the `audits` table did not exist at all, and the frontend's audit history was an `localStorage` workaround.

The problem was not auth design — it was that the database had never been provisioned. The solution was to provision it, not to redesign auth.

**Finding 3 — No WebGPU or new libraries needed for mobile testing.**
The user asked whether native mobile app testing needed anything like WebGPU. Bob researched the actual mechanism: today's "mobile" testing is Playwright's device emulation of a *responsive website* — already 100% browser-visible, no special capabilities needed. Real native-app testing (Appium) is a larger post-MVP feature. Bob presented three options; the user chose to skip it.

### Supabase MCP: Real Database Provisioning
Bob used the Supabase MCP to:
1. Provision a real Supabase project (`xpzcpsjjmubxfmbpfnvn`)
2. Apply `docs/supabase_schema.sql` as a migration

This surfaced a real, previously-undetected bug: the schema used MySQL-style inline `INDEX name (...)` clauses inside `CREATE TABLE`, which is invalid PostgreSQL. It had never been run against a real database before. Bob fixed to separate `CREATE INDEX` statements and applied cleanly.

**This bug could not have been found without the Supabase MCP.** The schema existed as a SQL file but had never been executed — a static analysis pass would not have caught the MySQL/PostgreSQL incompatibility. Only running it against a real Postgres database revealed it.

### Sub-Agent Delegation for the Marketing Rebuild
The marketing-page rebuild was well-specified (7 named sections, each with a defined target component set) and frontend-only. Bob delegated this to a sub-agent, keeping a precise per-file spec as the delegation contract:
- `HeroSection`, `ProblemSection`, `HowItWorksSection`, `ReplaySection`, `DifferentiatorsSection`, `ArchitectureSection`, `FooterCTA`
- All using `shadcn Card/Badge/Button` + existing `framer-motion` reveal patterns
- No new animation libraries

While the sub-agent ran the rebuild, the main session handled Supabase provisioning, backend wiring, and deployment — two independent streams, no shared file conflicts.

### Fixing Stale Product Copy
The marketing sections contained stale content that no longer reflected the product:
- `ReplaySection` had a fake CLI terminal animation — deleted, replaced with a dashboard preview card (no CLI-first story left to tell)
- `HeroSection` CTA "View CLI Documentation" → "Run an Audit" (links to `/dashboard/new-run`)
- `DifferentiatorsSection`'s "Bedrock-Powered Decisions" card updated to reflect the real current three-tier stack
- "Why Judges Will Love It" hackathon-only heading replaced with evergreen copy

Bob identifies and fixes stale content as a natural part of a UI rebuild — not as scope creep, but as part of making the product accurately represent itself.

---

## Supabase MCP Usage Details

The Supabase MCP (Model Context Protocol server for Supabase) was used in this session as the primary database provisioning tool. Bob did not ask the user to manually create tables or run migrations — it handled the entire provisioning workflow:
1. `mcp__supabase__create_project` — provisioned the project
2. `mcp__supabase__apply_migration` — applied the schema SQL
3. `mcp__supabase__get_publishable_keys` — retrieved the anon key for the frontend
4. Deployed backend with `SUPABASE_URL`/`SUPABASE_KEY` (service_role) set on Cloud Run
5. Deployed frontend with `NEXT_PUBLIC_SUPABASE_URL`/`NEXT_PUBLIC_SUPABASE_ANON_KEY` on Vercel

This is MCP servers being used as they are intended: giving Bob the ability to act on infrastructure that would otherwise require manual steps from the user.

---

## Key Bob Discipline Applied

**Read before proposing.** All three major decisions changed because Bob read the actual code instead of accepting the framing in the request. The user said "the UI is awful" — the right response was to find out *why* (marketing sections never converted to shadcn, despite shadcn being installed), not to propose installing more libraries.
