# Session 16: Bob Methodology — Whole-Site Audit

## Bob Mode Used

**Agent Mode**

This is the final and most methodologically disciplined session in the project. It demonstrates every major Bob principle simultaneously: research before design, live testing as the actual bug-finder (not just verification), Supabase MCP for production schema changes, and the correct response to out-of-scope bugs discovered mid-session.

---

## Bob Tools and Techniques

### Research Before Design (Explicit User Instruction)
The user instruction was explicit: "research first, then plan, before writing any code." Bob researched four categories before proposing the architecture:

**Authentication separation** (OWASP ZAP, Playwright `storageState`, WorkOS, Burp Suite): consistent guidance — log in once, reuse the session cookie jar, never re-authenticate per page. Use a dedicated test account, not a real login. Use the password once to establish a session, discard it immediately.

**Site discovery** (Screaming Frog, Scrapy): hybrid discovery — `sitemap.xml` + breadth-first same-origin link-following with hard guardrails (max pages, max depth, time budget, same-origin only).

**Report structure** (Lighthouse CI, Unlighthouse, Sitebulb): aggregate rollup + filterable flat list with drill-down, not a literal site tree.

The research findings shaped every design decision before a line of code was written.

### Supabase MCP: Production Migration
Bob used the Supabase MCP to apply two migration statements to the live production Supabase project:
1. New `site_audits` table
2. `audits.site_audit_id` nullable FK column

These were applied via `mcp__supabase__apply_migration` against the live project, not a local dev instance. The same idempotent migration approach used in Sessions 14 and 15.

### Reuse-Over-Duplicate Principle (Two Applications)

**Application 1 — Per-page audit pipeline**: `AuditOrchestrator._run_audit_body` was split into a thin wrapper and a reusable `run_audit_on_page(worker, url, observation, ...)` function. `SiteAuditOrchestrator` calls this function once per crawled page — it does not duplicate the pipeline. Domain-allowlist enforcement, persona loading, and the entire audit logic stay in one place, exercised identically by single-page and whole-site audits.

**Application 2 — Report storage**: A crawled page's `AuditReport` is not a different shape from a single-page audit's. It gets a nullable `site_audit_id` FK on the `audits` row. The existing `/dashboard/audits/[auditId]` detail page, screenshot serving, and rendering logic needed **zero changes** to serve as every crawled page's proof view.

### Live Testing as the Actual Bug-Finder (Not Just Verification)
Unit tests (27 new, all mocked) passed cleanly before live testing began. Live testing against two real sites found four bugs that no mock would have caught:

**Bug 1 — Progress invisible mid-crawl**: `SITE_AUDIT_STORE`'s manifest/`pages_audited` were only written once, after the whole crawl returned. A poll while `status: "running"` always showed `manifest: {}`/`pages_audited: 0`. Fixed by updating the live store inside `on_page_complete` callback.

**Bug 2 — Scheme duplicates wasted page budget**: The same page reachable as both `https://host` and `http://host/` was treated as two different URLs. Fixed by canonicalising same-hostname links to the origin's scheme before dedup.

**Bug 3 — Sitemap index files audited as pages**: A site's `/sitemap.xml` can be a sitemap *index* listing other `.xml` files. These looked identical to real `<url><loc>` page entries once flattened. Fixed by applying the same asset-extension filter to sitemap discovery.

**Bug 4 — k2-horizon token budget exhaustion**: The text-synthesis LLM sometimes exhausted its whole token budget on chain-of-thought before emitting any JSON. `response_format=json_object` guarantees JSON syntax, not that reasoning stays within budget. Reproduced 100% consistently against real content-rich pages. Fixed with bounded continuation retry: on JSON-parse failure, one follow-up call resends the original messages plus the truncated response as assistant context, asking for the final JSON only. Also raised the token ceiling from 4096 → 8192 as a first line of defence.

**All four bugs were fixed inside the session**, each given its own deterministic regression test.

### Correct Handling of Out-of-Scope Bugs
Bug 4 (k2-horizon token exhaustion) also affected the pre-existing single-page audit pipeline — it was not a new bug introduced by this feature. Bob's initial response: **document it as a live-discovered finding, not an unscoped side quest** — until the user explicitly asked for it to be handled, at which point it got a full fix and real tests.

This is the correct boundary: notice out-of-scope issues, document them, do not silently fix them without user awareness (scope change), but do fix them properly when asked.

### Security Test Automated
`test_create_site_audit_password_never_appears_in_any_response` — Bob wrote an automated test that confirms a login password never appears in any API response. This covers the exact credential-handling requirement established during the research phase: "use the password once to establish a session, never store or log it." The security guarantee is verified mechanically, not just asserted in documentation.

### Two Real Websites Used for Verification
- `the-internet.herokuapp.com` — no login, link-following test
- `practicetestautomation.com` — real login flow (`student`/`Password123`), post-login page verification

Final confirmation run: 4/4 pages (45 discovered, zero duplicates) on the no-login site; 3/3 pages on the login site including the actual protected post-login page, reached via a real login form. 38 real screenshots captured across the login run's 3 pages.

---

## Key Bob Discipline Applied

**Live testing is the real test suite for browser automation.** A fully mocked test suite gives confidence that the code does what it is specified to do. A real browser session against real websites finds what the specification missed. Both are required. The correct order: write mocked tests first (fast feedback loop), then run against real sites (reality check), then write regression tests for anything the real sites found.
