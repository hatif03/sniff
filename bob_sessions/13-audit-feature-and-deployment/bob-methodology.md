# Session 13: Bob Methodology — Landing-Page Conversion Audit + Public Deployment

## Bob Mode Used

**Agent Mode**

This session added the second product surface (landing-page conversion audit) and deployed the entire stack publicly for the first time. Bob used real deployment tooling and made a real security-relevant architecture decision.

---

## Bob Tools and Techniques

### Schema Extraction From a Real Competitor Report
The audit schema was derived from a saved HTML file of a real ColdVisit paid report. Bob did not guess what fields a conversion audit should have — it read the real competitor's data structure.

ColdVisit's Next.js app ships page data inside `self.__next_f.push(...)` script chunks. Bob parsed these chunks to extract the exact schema field-for-field. `src/core/audit_models.py` mirrors that schema: score, verdict, five named dimensions (Message & Clarity, Audience Fit, Action Path, Trust & Credibility, Content Depth), growth sub-report, visual teaser, browsing evidence, copy rewrites, and persona.

**The differentiator**: the ColdVisit report locks most fields behind a $3.99+ paywall. Sniff shows everything. This was a product decision informed by reading the competitor's actual paywall structure, not assumed.

### `screenshot_annotator.py` — Coordinates Before Capture
`src/evidence/screenshot_annotator.py` overlays labeled boxes on the live page *before* capturing the screenshot. This is architecturally significant: annotation coordinates are exact because they come from the live DOM's real bounding boxes, not from post-hoc guesses applied to an already-captured image.

Bob's rationale: a post-hoc annotation on a static image would require coordinate mapping between the screenshot's pixel dimensions and the original viewport — fragile and approximate. Live annotation from real bounding boxes is exact.

### Path-Traversal Security on Image Endpoint
`GET /audits/{audit_id}/images/{filename}` was added after the frontend flagged a missing endpoint. Bob added a fixed filename allowlist to prevent path traversal — an attacker cannot use `../../etc/passwd` as a filename because only known audit screenshot filenames pass the allowlist.

This security check was added by Bob without being asked — it noticed the endpoint was serving files from a user-supplied path and applied the standard mitigation.

### Cloud Run Deployment With Shell Tools
Bob ran `gcloud run deploy --source .` to deploy the backend to Cloud Run, using Cloud Build for the remote build (Docker Desktop was not running locally). Key flags:
- `--no-cpu-throttling`: required because `BackgroundTasks` would otherwise freeze when the HTTP response returns (Cloud Run suspends container CPU outside request handling by default)
- `--min-instances=1`: keeps the in-process run/audit store alive between requests
- `--allow-unauthenticated`: the app has its own Bearer-token gate, so Cloud Run's IAM check is redundant

### Debugging the False Alarm: Reserved Paths on Cloud Run
The deployed backend returned a Google-branded 404 on `/healthz` externally, despite the service being healthy. Bob's debugging methodology:
1. Checked DNS — not the issue
2. Checked IAM policies — not the issue  
3. Checked org policies — not the issue
4. Checked `--port`, region, image size — not the issue
5. Tested other paths — all worked correctly
6. Root cause: `/` and `/healthz` are **reserved paths** on Cloud Run's default `*.run.app` domain, intercepted at Google's edge

**Fix**: rename the liveness endpoint from `/healthz` to `/status` — a one-line change. The session summary captures the full elimination list so the next person debugging a similar Cloud Run 404 has a starting point.

**Lesson**: "it works internally but fails externally" on Cloud Run has a known cause (reserved edge paths). Do not spend time on infrastructure hypotheses when a one-line rename fixes it.

### Frontend Build Fix for Supabase
`sniff-web/lib/supabase.ts` was updated to use placeholder fallback values when env vars are not set at build time. The Supabase client throws at construction time on empty strings — which broke Vercel builds where `NEXT_PUBLIC_SUPABASE_URL` is not available during the build phase. Bob fixed this as a side effect of the deployment, not as a separate task.

---

## Key Bob Discipline Applied

**Extract real schemas, do not invent them.** The audit schema came from a real competitor's data, parsed from their actual output, not from guessing what a "good audit report" should contain. This produced a schema that matches real-world expectations rather than internal assumptions.

**Security is not optional, even in prototype sessions.** The path-traversal guard on the image endpoint was added without being asked. Bob's general principle: when writing code that serves user-supplied filenames from the filesystem, add the allowlist by default.
