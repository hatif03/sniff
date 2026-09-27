# Session 16: Whole-Site Audit (Crawl Every Page, Log In If Given Credentials)

**Session Type:** Agent Mode
**Status:** Complete
**Date:** 2026-09-27

---

## Objectives

The user asked to extend Sniff beyond a single landing page: given a website, analyze the entire application - every reachable page, including pages behind a login if credentials are supplied - with the same per-page proof (screenshots, what was clicked and what wasn't) the single-page audit already produces, surfaced in the dashboard. Explicit instruction: research first, then plan, before writing any code.

---

## What Was Actually Done

### 1. Research before design

Grounded in how real tools handle this, not invented from scratch: OWASP ZAP/Burp Suite and Playwright's own `storageState` all separate *becoming authenticated* from *reusing that session* - log in once, keep the cookie jar, never re-authenticate per page. Site crawlers (Screaming Frog, Scrapy) converge on hybrid discovery (`sitemap.xml` + breadth-first same-origin link-following) with hard guardrails (max pages/depth, same-origin only, a crawl time budget). Credential-handling guidance (AWS Well-Architected, WorkOS, ZAP/Burp) is consistent: use the password once, in-memory, to establish a session, then discard it - never store or log the raw secret, prefer a dedicated test account. Multi-page report tools (Lighthouse CI, Unlighthouse, Sitebulb) converge on an aggregate rollup plus a filterable flat list with drill-down, not a literal site-tree.

### 2. Backend

- `AuditOrchestrator._run_audit_body` split into a thin per-request wrapper plus a reusable `run_audit_on_page(worker, url, observation, ...)` - the entire per-page pipeline (checks, CTA click-testing, screenshots, both LLM syntheses, `AuditReport` assembly), now callable once per crawled page on one shared worker session instead of duplicated.
- New `SiteAuditOrchestrator` (`src/core/site_audit_orchestrator.py`): one `PlaywrightWorker` session for the whole crawl (optionally after `login()` or loading a pasted `storage_state`), discovers via `sitemap.xml` + same-origin link-following (`src/core/site_crawl.py`), audits up to `max_pages`/`max_depth`, and records a `CrawlManifest` - audited/skipped/failed for every URL considered, the literal "what we clicked and what not."
- `PlaywrightWorker` gained `login(url, username, password)` (fills the first password field + nearest text/email field, submits, checks for navigation away as the success signal) and `get_page_links()`; `storage_state` is now accepted at context creation.
- New `POST /site-audits` / `GET /site-audits/{id}` endpoints (same Bearer-auth/background-task pattern as `/audits`). Each crawled page is a completely normal audit row (tagged with a nullable `site_audit_id` FK) - `GET /audits/{audit_id}` and its image endpoint serve individual pages unchanged, no new per-page endpoint needed.
- New `site_audits` Supabase table + `audits.site_audit_id` migration, applied live.
- New `GuardrailsConfig` fields: `max_site_audit_pages` (default 10, ceiling 30), `max_site_audit_depth` (default 3), `site_audit_hard_timeout` (default 1800s - a crawl legitimately takes longer than one page).

### 3. Frontend

- `new-run/page.tsx`: the existing single-URL tab (mislabeled "Full Site Audit") renamed to "Single Page Audit"; a genuinely new "Full Site Audit" tab added with seed URL, max-pages presets, and a collapsible login section (username/password or a pasted `storage_state` session) carrying explicit, non-buried security copy: *"Use a dedicated test/staging account, not your real login. Your password is used once to sign in and is never stored."*
- New `/dashboard/site-audits/[siteAuditId]/page.tsx`: rollup header (status, average score, pages discovered/audited) plus a filterable flat list of every manifest entry, linking audited pages straight into the existing, unchanged audit detail page for full per-page proof.
- New `/api/backend/site-audits` proxy routes, `getRecentSiteAudits()` in `lib/queries.ts`, one new "Site Audits" dashboard nav button.

### 4. Bugs found only by testing against real websites

Unit tests (27 new, all mocked) passed cleanly, but live testing against two real sites - `the-internet.herokuapp.com` (no login) and `practicetestautomation.com` (real login flow, student/Password123) - surfaced four real bugs no mock would have caught:

1. **Progress was invisible mid-crawl.** `SITE_AUDIT_STORE`'s manifest/`pages_audited` were only written once, after the whole crawl returned - a poll while `status: "running"` always showed `manifest: {}`/`pages_audited: 0` regardless of real progress. Fixed by updating the live store inside the `on_page_complete` callback, not just at the end; the final manifest still overwrites it in full on completion. Caught with a deterministic regression test that runs `_execute_site_audit` directly against a pausing fake orchestrator and snapshots the store mid-crawl.
2. **Scheme duplicates wasted the page budget.** The same page reachable as both `https://host` and `http://host/` (a stray absolute link, common on older sites) was treated as two different URLs and audited twice. `normalize_and_filter_links` matched same-site by hostname only, never checking scheme. Fixed by canonicalizing a same-hostname link's scheme to the origin's scheme before it enters the visited/dedup set.
3. **Sitemap index files got audited as if they were pages.** A site's `/sitemap.xml` can itself be a sitemap *index* listing other `.xml` sitemap files (e.g. `image-sitemap-1.xml`) - those entries look identical to a real `<url><loc>` page entry once flattened by namespace-agnostic parsing. Regular link-following already filters `.xml` via `_ASSET_EXTENSIONS`, but sitemap-discovered URLs bypassed that filter entirely. Fixed by applying the same asset-extension filter to sitemap discovery.
4. **The text-synthesis LLM (k2-horizon) sometimes exhausted its whole token budget on chain-of-thought before emitting any JSON at all**, failing the page outright - `response_format=json_object` guarantees syntax, not that reasoning stays inside budget. Reproduced 100% consistently against real content-rich pages. Per explicit follow-up instruction, fixed with a bounded continuation retry: on a JSON-parse failure, one follow-up call resends the original messages plus the truncated response as assistant context and asks specifically for the final JSON - reusing the model's own reasoning instead of discarding it and starting over. Also raised the ceiling itself (4096 → 8192 tokens) as a first line of defense. Covered by two new client-level tests (first response non-JSON, continuation succeeds; both fail → raises).

After all four fixes, a final confirmation run against both real sites completed cleanly: 4/4 pages (45 discovered, zero duplicates) on the no-login site, and - critically - all 3/3 pages on the login site, including the actual protected post-login page (`/logged-in-successfully/`), reached via a real login through the separate login form and scored honestly (avg. ~5.7/10). 38 real screenshots (including per-CTA click-test steps) captured across the login run's 3 pages, each in its own subdirectory.

---

## Why These Specific Decisions

**Reuse, don't duplicate, the per-page pipeline.** `SiteAuditOrchestrator` composes a plain `AuditOrchestrator` and calls its extracted `run_audit_on_page` - domain-allowlist enforcement, persona loading, and the entire audit pipeline stay in one place, exercised identically by both single-page and whole-site audits.

**Reuse the existing `audits` table and detail page entirely unchanged.** A crawled page's `AuditReport` is not a different shape - giving it a nullable `site_audit_id` FK (mirroring `runs` → `observations`/`actions`) means the existing `/dashboard/audits/[auditId]` page, its screenshot serving, and its whole rendering logic needed zero changes to serve as every crawled page's proof view.

**Fix the shared client once, not every caller.** The k2-horizon retry lives inside `K2HorizonClient.invoke_with_json_response` itself, so both the pre-existing single-page audit and the new site audit get the reliability improvement from one change, not two.

**Live testing on real sites was the actual bug-finder, not incidental verification.** All four bugs above passed a fully mocked test suite; none would have been caught without navigating real pages with a real browser and a real (flaky) LLM. Each was then given its own deterministic regression test so the fix doesn't silently regress, but the discovery itself required the live run.

**Don't fix everything a live run surfaces.** The k2-horizon reasoning-overrun issue affects the pre-existing single-page audit pipeline too, not something introduced by this feature - it was deliberately left as a documented, live-discovered finding rather than an unscoped side quest, until the user explicitly asked for it to be handled, at which point it got a real fix and real tests like everything else in this session.

---

## Verification

- `uv run --extra dev pytest`: 193/193 passing (up from 162 before this session) - 27 new tests for the whole-site-audit feature itself, plus regression tests for each of the four live-discovered bugs.
- `yarn build`/`yarn lint` clean for all new/changed frontend files.
- Real end-to-end proof, not just mocks: two real public sites, with and without a real login flow, run to completion multiple times through the debugging process, final confirmation run clean on both.
- Security guarantee automated, not just asserted: `test_create_site_audit_password_never_appears_in_any_response` (backend) confirms a login password never appears in any API response; live-tested the same way (a real password used against a real login form, never logged or echoed).

---

## Next Steps

→ The k2-horizon reasoning-overrun tendency is worth watching in production - the continuation retry and higher token ceiling should substantially reduce it, but it's a model-behavior issue (not fully within this codebase's control) and may need a further look if failure rates stay non-trivial.
→ Sitemap discovery still doesn't distinguish a genuine sitemap *index* from a flat sitemap beyond the `.xml`-extension heuristic - fine for now, but a site with a differently-named nested sitemap file could still slip through; worth a proper `<sitemapindex>`-vs-`<urlset>` root-tag check if it comes up again.
→ `max_site_audit_pages`/`max_site_audit_depth`/`site_audit_hard_timeout` have no env vars set on the deployed Cloud Run service - they fall back to config.py's defaults (10/3/1800s), which is fine, but worth knowing if those defaults ever need production tuning.
