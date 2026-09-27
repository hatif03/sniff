# Video Script: How We Built Sniff with IBM Bob 2.0

**Format:** Talking head + screen recording cut-ins  
**Target length:** 90–120 seconds  
**Tone:** Direct, confident, technically honest

---

## [0:00–0:12] — Hook

*(On screen: the Sniff dashboard loading in a browser)*

> "This is Sniff — an autonomous AI agent that tests your website like a real, confused user would. We built the entire product using IBM Bob 2.0. Not just the code. The architecture, the market research, the database, the deployment — all of it. Here's how."

---

## [0:12–0:30] — The Starting Point and Plan Mode

*(On screen: the `sniff-expansion-plan.md` file open in Bob, then cut to the `bob_sessions/01-planning-and-market-research/` folder)*

> "We started with a rough prototype and one prompt to Bob in **Plan mode**. Bob audited the codebase, researched our competitors — including browsing ColdVisit's live docs — identified the feature gaps, and produced a complete product roadmap with Architecture Decision Records before a single line of new code was written."

> "Plan mode is specifically designed for this: it cannot write files, so it's forced to think first. That one session gave us the entire expansion plan and three accepted architectural decisions — including the three-tier AI reasoning stack that became the product's core differentiator."

---

## [0:30–0:55] — Agent Mode: Building in Sessions

*(On screen: quick cuts — Bob's Agent mode interface, a session-summary.md, `tier_router.py` opening, the FastAPI `main.py`)*

> "Then we switched to **Agent mode** for 15 implementation sessions. Each session had a clear goal from the plan. Bob read the existing code before changing anything — a discipline it enforces itself — then wrote, tested, and verified the change."

> "One example: integrating Typesafe AI's Jev model as our middle reasoning tier. Bob read the actual API docs, made a **live call with the real API key**, discovered the documented endpoint shape was wrong, fixed it, and verified a 200 OK before calling it done. That kind of live verification — not just trusting documentation — was how we caught bugs before they shipped."

---

## [0:55–1:20] — MCP Servers and Sub-Agents

*(On screen: Supabase dashboard showing the provisioned project, then a Bob session showing three parallel sub-agents)*

> "Two capabilities made the biggest difference. First: the **Supabase MCP server**. Bob provisioned our actual production database, applied schema migrations, and even caught a PostgreSQL syntax bug in our schema that had never been run against a real database before — all without us touching the Supabase dashboard."

> "Second: **sub-agents**. When we needed to rebuild seven marketing sections and wire up a new backend at the same time, Bob spawned a parallel agent for the frontend work while the main session handled the database. Two independent workstreams, no conflicts, running simultaneously."

---

## [1:20–1:45] — The Result

*(On screen: the live deployed product — dashboard, audit report, site audit rollup)*

> "Across 17 sessions and two IBM organisations, Bob took us from a CLI prototype with no public name to a fully deployed SaaS — FastAPI backend on Cloud Run, Next.js frontend on Vercel, three product surfaces, a real Supabase database, scheduled runs via GCP Cloud Scheduler, and 193 passing tests."

> "Every architectural decision is documented. Every session has a record of exactly what Bob was asked, what it did, and why. You can read the whole build diary in the `bob_sessions/` folder in the repo."

---

## [1:45–2:00] — Close

*(On screen: back to the Sniff homepage)*

> "IBM Bob didn't just write code for us. It was the architect, the researcher, the reviewer, and the deployment engineer. That's what an AI coding agent looks like when you actually use it end to end — not as a code autocomplete, but as a genuine technical partner."

> "That's Sniff. Built with IBM Bob."

---

## Screen Recording Cues (Summary)

| Timestamp | What to Show |
|---|---|
| 0:00–0:12 | Sniff dashboard in browser |
| 0:12–0:30 | `sniff-expansion-plan.md` in Bob; `bob_sessions/01/` folder |
| 0:30–0:55 | Bob Agent mode interface; `tier_router.py`; `jev_client.py` test output |
| 0:55–1:20 | Supabase dashboard (real project); Bob session with sub-agent output |
| 1:20–1:45 | Live site: dashboard overview → audit report → site audit rollup |
| 1:45–2:00 | Sniff landing page / hero |

---

## Notes

- Keep each section tight — the script reads at ~150 wpm, which lands at ~110 seconds spoken.
- The screen cuts are suggested; adjust to what you have available.
- The `bob_sessions/` folder, `agents.md`, and `bob_sessions/architecture.md` are all real, committed files that can be shown on screen.
