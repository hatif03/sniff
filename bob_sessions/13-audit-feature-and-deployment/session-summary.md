# Session 13: Landing-Page Conversion Audit + Public Deployment

**Session Type:** Agent Mode
**Status:** Complete
**Date:** 2026-09-26

---

## Objectives

1. Add a second product surface: a full landing-page conversion audit ("what a product manager would check"), matching the metric set of a real competitor report (ColdVisit) the user provided.
2. Deploy the whole stack publicly for a hackathon, explicitly skipping signup/billing/abuse-prevention per direct instruction (documented as deferred, not forgotten, in `docs/product/SAAS_ROADMAP.md`).

---

## What Was Actually Done

### 1. Real-schema audit engine

The target schema was extracted from a saved HTML file of a real (paid, since-dead-linked) ColdVisit report — Next.js ships page data as JSON inside `self.__next_f.push(...)` script chunks, parsed directly rather than guessed from rendered markup. `src/core/audit_models.py` mirrors that schema field-for-field (score, verdict, 5 named dimensions, growth sub-report, visual teaser, browsing evidence, fixes/rewrites, images, persona) with nothing paywall-gated, unlike the source report.

`src/evidence/audit_checks.py` does the deterministic, free work: computed-style color/font sampling, interactive-element enumeration with real bounding boxes, footer/nav link liveness (httpx HEAD/GET), Core Web Vitals via `performance.getEntriesByType`, and basic SEO/meta DOM queries. `src/evidence/screenshot_annotator.py` overlays labeled boxes on the live page before capture, so annotation coordinates are exact rather than post-hoc guesses. `src/core/audit_orchestrator.py` wires one Playwright session through checks → CTA click-testing (reusing `PlaywrightWorker.tap()`) → Gemini vision synthesis (score/verdict/story/persona) → k2-horizon text synthesis (copy rewrites, SEO/nav findings).

`src/api/main.py` got `POST /audits` / `GET /audits/{audit_id}`, same in-process-store + background-task pattern as `/runs`, plus `GET /audits/{audit_id}/images/{filename}` (added after the frontend flagged it was missing) with a fixed filename allowlist to prevent path traversal. Frontend: proxy routes under `app/api/backend/audits/**`, a report page at `/dashboard/audits/[auditId]`, and a mode toggle on `/dashboard/new-run`.

### 2. Public deployment

Backend to Cloud Run (`gcloud run deploy --source .`, Cloud Build remote build — Docker Desktop wasn't running locally). Key flags: `--no-cpu-throttling` (required — BackgroundTasks would otherwise freeze the instant the HTTP response returns), `--min-instances=1` (keeps the in-process run/audit store alive between requests), `--allow-unauthenticated` (app has its own Bearer-token gate). Frontend to Vercel with `BACKEND_URL`/`SNIFF_API_TOKEN` as server-only env vars.

**A long false alarm**: the deployed backend returned a generic Google-branded 404 on `/healthz` externally, despite the service reporting healthy internally. Extensive elimination (DNS, IAM, org policies, load balancers, deploy flags, port, region, image size, clean redeploy — including the user checking their own GCP Console) ruled out every real misconfiguration. Root cause: `/` and `/healthz` are reserved paths on Cloud Run's default `*.run.app` domain, intercepted at Google's edge before reaching any app, regardless of config. Every other path (including genuinely unregistered ones) correctly reached FastAPI. Fixed by renaming the liveness endpoint to `/status` — nothing was actually broken.

`sniff-web/lib/supabase.ts` got placeholder fallback values (the Supabase client throws at construction time on empty strings, which broke Vercel builds when env vars weren't set at build time).

---

## Why These Specific Decisions

**Show everything ColdVisit paywalls**: the source report gates most fields behind $3.99+; this version shows all of it, a real differentiator rather than a design choice needing justification.

**Never assume a platform-reported 404 is the platform lying** — cross-check with paths that should and shouldn't work before concluding the deploy itself is broken. The eventual fix was a one-line rename; the eliminated-first list was long because "it's healthy per the control plane but the edge disagrees" doesn't have an obvious first suspect.

---

## Verification

- `uv run --extra dev pytest`: 153/153 passing, `ruff check` clean.
- Live end-to-end against the deployed stack (not just localhost): a real run against `example.com` completed with a correct AI diagnosis; a real audit against `example.com` completed with a full populated report (score, verdict, context, etc.).

---

## Next Steps

→ `docs/product/SAAS_ROADMAP.md` Phase 2 (real auth, billing, job queue, abuse prevention) before accepting real outside users past the hackathon window.
