# Session 08: Bob Methodology — Journey Replay UI

## Bob Mode Used

**Agent Mode**

This session was the highest-priority UI feature in the original plan — ColdVisit parity for journey replay. The prompt explicitly pre-requires reading the existing `sniff-web` structure before writing any new code.

---

## Bob Tools and Techniques

### Pre-Read Before Build (Mandatory Pre-Session Step)
The `prompt.md` has an explicit pre-session checklist item: "Read `sniff-web/app/` and `sniff-web/components/` before starting." This is the standard Bob "investigate before answering" discipline formalised as a session gate.

Reading the existing structure first prevents: duplicating components that already exist, mismatching the naming convention, using the wrong import paths, and building against an assumed Supabase schema that might differ from the real one.

### TypeScript Type Alignment With Python Models
The Supabase query helpers in `sniff-web/lib/supabase/runs.ts` define TypeScript types that mirror the Python `RunReport`, `Observation`, `ActionResult`, and `DiagnosisResult` Pydantic models exactly. Bob reads both the Python models and the TypeScript destination before writing the TypeScript types — not to guess the shape, but to get exact field names and types.

### Server Components by Default
All new pages and components are Next.js Server Components unless they require client-side interactivity. The `ReplayViewer` with keyboard navigation (`ArrowLeft`/`ArrowRight`) requires `"use client"` — a deliberate exception, not a blanket default. Bob applies the Next.js App Router recommendation: push `"use client"` as close to the interactive leaf as possible.

### URL State for Step Navigation
The step navigation uses URL query params (`?step=N`) rather than in-memory state. This means:
- The browser back/forward buttons work naturally
- A specific step can be linked and shared
- The page is bookmarkable at any step

This is a considered choice that was specified in the prompt and follows Next.js best practices for sharable navigation state.

### Tailwind v4 Compatibility
All new utility classes must be Tailwind v4 compatible. Since the migration happened in Session 03, Bob verifies new components against the `@theme` block in `globals.css` to confirm custom token names are referenced correctly (Tailwind v4 treats custom properties differently from v3's `theme.extend`).

---

## Note on Dashboard History

The journey replay UI was planned as a feature of the web dashboard before Sessions 12–14 transformed the dashboard into a real SaaS product surface. The component architecture designed here (`ReplayViewer`, `StepTimeline`, `StepDetail`, `MobileDeviceFrame`) was a foundation that Session 12's UI redesign built on top of.
