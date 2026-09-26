# Session 14: UI Reimagine, Shared Persistent Data, Web-First Messaging

**Session Type:** Agent Mode
**Status:** Complete
**Date:** 2026-09-27

---

## Objectives

The user looked at the deployed app and found the UI "awful" - the marketing landing page was still 7 hand-rolled `<div>` sections from before any redesign ever actually touched them (an earlier pass had only fixed colliding CSS color tokens, never rebuilt the markup). Three explicit asks: (1) reimagine the UI properly using a real component/animation/chart library, (2) make every run/audit visible to everyone since there's no auth yet, (3) stop presenting the product as CLI-first - it's web-first now. Also asked to research whether native mobile app testing needs anything like WebGPU before deciding how far to take that.

---

## What Was Actually Done

### 1. Investigation before writing any code

Three findings shaped the whole session, each confirmed by reading the actual code rather than assumed:

- **No new libraries were needed.** `sniff-web/package.json` already had shadcn/ui (Radix), `framer-motion` (already used throughout all 7 marketing sections), `gsap` (installed but imported nowhere - dead weight), and Recharts (already used correctly in two dashboard viz components). The actual gap: the marketing sections never adopted shadcn primitives, they were hand-rolled `<div>`s reimplementing what `Card`/`Badge`/`Button` already do.
- **"Show everything to everyone" was blocked by persistence, not auth.** The dashboard already read a public-read Supabase view for runs - but no real Supabase project had ever been created (`SUPABASE_ENABLED=false`, no `SUPABASE_URL` anywhere). Audits were worse: no `audits` table existed at all, and the frontend's "audit history" was an explicit `ponytail:`-commented localStorage workaround, visible only to the browser that created it.
- **Native mobile app testing needs no WebGPU.** Researched live: today's "mobile" testing is Playwright's device-emulation of a *responsive website*, not a native app - already 100% browser-visible. Real native-app testing (Appium + device/emulator streaming) is a materially bigger feature the project's own docs already flag as post-MVP. Presented the user three real options (skip / managed device cloud / self-hosted `android-emulator-webrtc`); they chose to skip it for now.

### 2. Made data real and shared

Provisioned an actual Supabase project (`xpzcpsjjmubxfmbpfnvn`, via the already-authenticated `supabase` CLI) and applied `docs/supabase_schema.sql` to it - which surfaced a real, previously-undetected bug: the schema used MySQL-style inline `INDEX name (...)` clauses inside `CREATE TABLE`, which is invalid PostgreSQL. It had silently never been run against a real database before. Fixed to separate `CREATE INDEX` statements, applied cleanly.

Added an `audits` table (public-read RLS, same pattern as the existing `runs` table, full report stored as JSONB rather than normalizing every nested field into columns - the report shape is rich and mostly read as a whole). Added `SupabaseUploader.upload_audit()` mirroring the existing `upload_run()`, wired into `_execute_audit` in `main.py`. On the frontend, added `getRecentAudits()` to `lib/queries.ts` and rewrote `AuditHistoryList` to query it directly instead of reading `window.localStorage` - deleted the now-dead localStorage functions from `lib/audits.ts` (kept its type definitions, still used by the audit report page). Set `SUPABASE_ENABLED=true` plus real `SUPABASE_URL`/`SUPABASE_KEY` (service_role) on Cloud Run, and `NEXT_PUBLIC_SUPABASE_URL`/`NEXT_PUBLIC_SUPABASE_ANON_KEY` (anon key) on Vercel, then redeployed both.

### 3. Rebuilt the UI on what was already installed

Delegated the mechanical rebuild to a subagent with an exact per-file spec (kept in the approved plan): all 7 marketing sections (`HeroSection`, `ProblemSection`, `HowItWorksSection`, `ReplaySection`, `DifferentiatorsSection`, `ArchitectureSection`, `FooterCTA`) converted from hand-rolled markup onto shadcn `Card`/`Badge`/`Button`, keeping the existing framer-motion reveal/hover patterns rather than inventing new ones. `gsap` removed from `package.json` as unused weight rather than adopting a second animation system.

`ReplaySection`'s fake CLI-terminal-typing animation was deleted entirely and replaced with a dashboard-preview card (persona/URL/diagnosis), since there's no CLI-first story left to tell. `HeroSection`'s "View CLI Documentation" CTA became "Run an Audit" linking straight to `/dashboard/new-run`. `app/docs/page.tsx` reframed to lead with the web dashboard, keeping the CLI reference material intact but no longer as the hero framing. `DifferentiatorsSection`'s stale "Bedrock-Powered Decisions" card and "Why Judges Will Love It" hackathon-only heading were both updated to reflect the real current three-tier architecture and evergreen copy.

---

## Why These Specific Decisions

**Investigate before building**: all three major decisions this session (no new libraries, persistence not auth, no WebGPU needed) came from reading the actual code/researching the actual mechanism rather than trusting the framing in the request - each one changed the scope of what actually needed to happen.

**Parallelize independent work**: the marketing-page rebuild (frontend-only, well-specified) ran as a background agent while the Supabase provisioning + backend wiring happened directly, since the two didn't touch the same files.

**Fix the real bug found along the way rather than working around it**: the invalid-PostgreSQL-syntax schema would have failed silently again on the next attempt to use it; fixing the syntax was less work than debugging around it.

---

## Verification

- `uv run --extra dev pytest`: 153/153 passing after the Supabase wiring changes.
- `yarn build` and `yarn lint` clean after the full marketing-page rebuild.
- Live end-to-end: triggered a fresh audit against the redeployed stack, confirmed it completed AND landed in the shared Supabase `audits` table via a direct REST query - proving persistence and shared visibility actually work, not just "no crash."

---

## Next Steps

→ `docs/product/SAAS_ROADMAP.md` Phase 2 (real per-user auth via Supabase Auth + RLS scoped to `auth.uid()`) before accepting real outside users past this public/no-auth phase.
→ An unused Fly.io app (`sniff-api`, status "pending", never successfully deployed) is still sitting in the account from an earlier fallback plan that was never needed - flagged for the user to delete, not deleted automatically.
