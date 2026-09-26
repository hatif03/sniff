# Sniff SaaS Roadmap

What it takes to go from "one integrated product with a shared-secret gate"
(this pass - see `ARCHITECTURE.md` Section 7B) to a real multi-tenant SaaS
anyone can sign up and pay for. Each item below needs a decision or an
account only you can make/provision, which is why it's written up here
rather than built.

## 1. Real multi-tenant auth

Replace the Phase-1 shared bearer-token gate with Supabase Auth (already an
installed, unused-for-auth dependency in `sniff-web`):
- Email/password or magic-link sign-in via `supabase.auth.signInWithOtp`/`signInWithPassword`.
- Every table the API writes to (`runs`, `observations`, `actions`,
  `diagnoses`, `agent_reasoning`, `persona_reviews`, `audits`) gets a
  `user_id` column and its existing public-read RLS policy (`USING (true)`,
  intentionally public for this pass - see `ARCHITECTURE.md` Section 7B)
  replaced with one scoping reads/writes to `auth.uid() = user_id` - today
  every row is readable by anyone with the (necessarily client-side) anon
  key, which is by design for now, not an oversight.
- The FastAPI backend verifies the Supabase JWT on every request
  (`supabase.auth.get_user(token)` or local JWT verification against
  Supabase's JWKS) instead of the shared secret.

## 2. Billing

- Stripe Checkout + Customer Portal for subscription management - simplest
  integration path for a small team, well-documented, handles card storage/
  PCI compliance for you.
- Plan tiers gated by: runs/month, concurrent runs, personas per run,
  data retention window. Ties into the per-run LLM cost/latency panel
  (`MARKET_RESEARCH.md` backlog item) for usage-based add-ons later.
- Requires: a Stripe account, choosing price points, and deciding whether
  to meter by run count or by a computed "cost" (LLM tokens + Playwright
  compute time).

## 3. Job queue / worker pool

Phase 1's `BackgroundTasks` approach (FastAPI's built-in in-process
background execution) is fine for one demo run at a time on one machine.
It is not fine for concurrent paying customers - a single slow/stuck
Playwright run blocks the same process's other work, and a process
restart drops in-flight runs silently.

Real version: a proper queue (Celery+Redis, or the already-installed
`apscheduler` promoted from "unused dependency" to an actual worker
scheduler) with:
- One worker pool sized to your concurrency budget (Playwright + a
  browser process per run is not cheap - expect to need real limits here).
- Per-tenant rate limiting/fair queueing so one customer's burst of runs
  doesn't starve everyone else.
- Persisted run state (not just in-memory dict) so a worker crash/restart
  doesn't lose a run silently - the API's `GET /runs/{id}` needs to survive
  a backend restart.

## 4. Abuse prevention

This is the one that matters most before going public, not just for you:
- **Domain-ownership verification** before letting a run target a URL -
  at minimum a DNS TXT record challenge or a well-known file check,
  similar to how domain-verification works for ownership-gated APIs
  generally. Without this, Sniff is a general-purpose "make an AI agent
  hit any URL repeatedly" service, which is a real abuse vector (scraping,
  credential stuffing via the "type" action, hammering someone else's site).
- Rate limiting per account and per target domain.
- A clear acceptable-use policy and a way to report/block abuse.
- Consider requiring a manual review step before a new account's first
  few runs go out unsupervised.

## 5. Actual hosting

Recommendation, not provisioning (needs your accounts):
- **Backend (FastAPI + Playwright)**: a platform that runs a long-lived
  container, not serverless functions - Playwright needs real compute time
  and browser binaries. Fly.io or Railway both support this cleanly and
  are cheap to start. Use Playwright's own published Docker base image
  (has browser binaries baked in) rather than installing them yourself in
  a generic Python image.
- **Frontend (Next.js)**: Vercel is the path of least resistance and pairs
  well with the Next.js rewrite that proxies `/api/*` to the backend
  (see `ARCHITECTURE.md` Section 7B) - the rewrite target just needs to be
  the backend's public URL once it's hosted, so the two can live on
  different platforms and still present as one domain to visitors.
- **DNS/domain**: point your domain at Vercel, no separate subdomain
  needed for the API since the rewrite hides it.
- **Stripe** account for #2, needs business details on file before going
  live with real payments.

None of this is code Claude can run on your behalf - it needs your
decisions on budget/platform and your accounts to provision.
