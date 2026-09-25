# Session 08 Prompt: Journey Replay UI

**Session Type:** Agent Mode  
**Status:** ⬜ Pending  
**Reference:** Sub-Task 7 in `sniff-expansion-plan.md` (highest priority UI feature — ColdVisit parity)

---

## Prompt (to be given when this session starts)

> Sub-Task 7 from `sniff-expansion-plan.md`:
>
> Build the Journey Replay UI — a visual step-by-step replay of what the Sniff agent did during a run, showing screenshot, action taken, agent reasoning, and any errors per step.
> This is the #1 priority feature for the dashboard (matches ColdVisit's journey replay feature).
>
> Pre-read the existing sniff-web structure:
> - `sniff-web/app/` — understand current pages
> - `sniff-web/components/` — understand existing components
>
> 1. Create Supabase query helpers in `sniff-web/lib/supabase/runs.ts`:
>    - `getRunById(run_id)` — fetch run metadata from `runs` table
>    - `getObservationsByRunId(run_id)` — fetch all observations ordered by step
>    - `getActionsByRunId(run_id)` — fetch all action results ordered by step
>    - `getDiagnosisByRunId(run_id)` — fetch diagnosis result
>    - TypeScript types matching the Python `RunReport`, `Observation`, `ActionResult`, `DiagnosisResult` Pydantic models
>
> 2. Build `sniff-web/app/runs/[run_id]/page.tsx` — Run Overview page:
>    - Shows: status badge, severity badge, goal text, persona name, step count, duration, Sniff Score (if available), "View Replay" button
>    - `RunOverviewCard` component
>    - `DiagnosisBadge` component: P0/P1/P2/P3 color + root cause icon (⚙️ Backend, 🎨 UX, ⚡ Perf, 🔌 Integration)
>    - Uses Tailwind v4 utility classes (from the migrated globals.css)
>
> 3. Build `sniff-web/app/runs/[run_id]/replay/page.tsx` — Replay page:
>    - Left panel: scrollable step timeline (thumbnail screenshots + action summary)
>    - Right panel: `StepDetail` — full screenshot in mobile device frame, action details, reasoning summary, errors/console output
>    - Mobile device frame: SVG wrapper that looks like an iPhone frame around the screenshot
>    - Step navigation: ← → keyboard shortcuts (ArrowLeft/ArrowRight)
>    - URL updates on step change: `/runs/[id]/replay?step=N`
>
> 4. Components to build (in `sniff-web/components/replay/`):
>    - `ReplayViewer.tsx` — main layout (timeline + detail panel)
>    - `StepTimeline.tsx` — scrollable list of step thumbnails
>    - `StepDetail.tsx` — expanded view of single step
>    - `MobileDeviceFrame.tsx` — SVG iPhone/Android frame for screenshots
>    - `ReasoningBubble.tsx` — shows agent's `reasoningSummary` as a callout
>    - `ActionBadge.tsx` — color-coded badge for action type (tap/type/scroll/wait/abort)
>
> 5. Update `sniff-web/app/page.tsx` (home/dashboard):
>    - Add a list/grid of recent runs linking to `/runs/[id]`
>    - Each card shows: run_id, status, severity, goal (truncated), date
>
> Constraints:
> - All components must be Tailwind v4 compatible (no v3-only classes)
> - Server Components by default; use "use client" only where interactivity is needed
> - TypeScript strict mode (no `any`)
> - Follow existing component style in `sniff-web/components/`

---

## Pre-Session Checklist

Before starting this session, verify:
- [ ] Session 03 Node build completed (`yarn install` + `yarn build` passed)
- [ ] Supabase has the correct schema (runs, observations, actions, diagnoses tables)
- [ ] `sniff-web/.env.local` has `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- [ ] Read `sniff-web/app/` and `sniff-web/components/` before starting
