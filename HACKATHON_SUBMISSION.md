# Sniff — Hackathon Submission Materials

---

## 1. Submission Title

**Sniff — The AI Mystery Shopper for Your Website**

---

## 2. Short Description (214 characters)

> Sniff sends an AI agent to click through your signup flow or landing page like a real user, then reports exactly where it got confused, why, and how to fix it — with screenshots and a full conversion audit score.

---

## 3. Long Description — Problem & Solution Statement

**The Problem**

Every founder eventually asks the same question: "Why aren't people signing up?" The honest answer is usually buried in analytics tools that show *what* happened (a 40% drop-off on step 3) but never *why*. Watching real user session recordings doesn't scale, and traditional QA testing only checks whether a flow technically works — not whether a confused, impatient, or first-time visitor can actually get through it. Landing page audit services exist (we studied one, ColdVisit, closely), but they're expensive per-report products that paywall most of their own findings.

**The Solution**

Sniff is an autonomous AI agent that behaves like a real visitor — not a scripted test runner. Point it at a signup flow or a landing page, and it drives a real browser (Playwright) step by step, deciding what to click based on what it actually sees on screen, the same way a person would. It doesn't follow a hardcoded path; a vision-capable model (Gemini) looks at each screenshot and decides the next action, while a separate fast-reasoning tier (Jev) sanity-checks those decisions and catches ambiguous "did we actually succeed?" moments a keyword search would miss.

**Two products in one agent:**

1. *Signup/onboarding testing* — assign the agent a goal ("sign up for an account") and a persona (confused first-timer, impatient power user, careful reader), and it attempts the flow, then classifies exactly why it failed if it did: root cause, severity (P0–P3), and likely owner (Backend/UX/Performance/Integration), escalated via Slack.

2. *Landing-page conversion audit* — point it at any URL and it produces a full product-manager-style teardown: an overall score, a five-dimension breakdown (Message & Clarity, Audience Fit, Action Path, Trust & Credibility, Content Depth), an annotated screenshot showing exactly what it identified as the CTA and clicked, a step-by-step narrative of what it saw and concluded, dominant colors/fonts actually sampled from the page, broken-link checks, copy rewrites, and a prioritized fix list. Every field a paid competitor report locks behind a paywall, Sniff shows in full.

**Who it's for:** founders and PMs who want an honest, evidence-backed answer to "what's wrong with my funnel" without hiring a researcher or paying per report; and engineering teams who want signup-flow regressions caught automatically, with a diagnosis attached instead of just a red X.

**How they interact with it:** a web dashboard — paste a URL, pick a goal or audit mode, and watch the agent work in near-real-time, then read the report with the same screenshots and reasoning trail the agent used.

**What makes it creative and unique:** most "AI testing" tools still follow scripted selectors. Sniff's agent reasons from pixels and text like a human tester, deployed with a genuinely three-tier architecture (vision LLM, fast text LLM, ultra-fast decision model) that keeps it both smart and cheap to run at scale — and it's the only tool in this space that treats conversion auditing and functional QA as the same underlying capability: an agent that understands what it's looking at.

*(494 words)*

---

## 4. YC-Style Pitch Slide

### SNIFF
**The AI mystery shopper for your website**

> An autonomous browser agent that tests signup flows and audits landing pages the way a real, easily-confused human would — then tells you exactly why they left.

---

**The Problem**
"Why aren't people signing up?" has no honest answer today.
- Analytics show *what* (a 40% drop-off), never *why*
- Session recordings don't scale
- Paid conversion-audit tools paywall most of their own findings

**The Solution**
An agent that behaves like a real visitor, not a script.

| Traditional QA | Sniff |
|---|---|
| Hardcoded selectors, breaks on any UI change | Looks at the real screenshot, like a person |
| Pass/fail, never *why* | Diagnoses root cause, severity, owner |
| Can't judge confusing copy or clutter | Scores clarity, trust, and friction directly |

**The Product — two surfaces, one agent**
1. **Signup/Onboarding Testing** — persona-driven agent runs (confused first-timer, impatient power user), root-cause diagnosis (Backend/UX/Performance/Integration), Slack escalation by severity (P0–P3)
2. **Landing-Page Conversion Audit** — full PM-style teardown: overall score, 5-dimension breakdown, annotated screenshot of what it clicked, step-by-step narrative, dominant colors/fonts sampled live, broken-link checks, copy rewrites, prioritized fixes — nothing paywalled

**How it works — three-tier reasoning stack**
- **Tier 1 (deterministic):** free DOM/CSS checks — colors, fonts, link health, Core Web Vitals
- **Tier 2 (Jev, ultra-fast):** goal-reached checks, context enrichment, decision sanity-gate
- **Tier 3 (Gemini + k2-horizon):** vision-grounded navigation decisions, scoring, narrative, copy rewrites

**Why now**
- Vision-capable LLMs finally cheap and fast enough to run *every step* of a browser session, not just a final summary
- Playwright + real browser automation is mature and cloud-deployable
- "AI agents that use a computer like a person" went from research demo to production-viable this year

**Traction (hackathon build)**
- Fully working end-to-end: real Gemini + k2-horizon + Jev calls, not mocks
- 153/153 tests passing
- Live and public: backend on Cloud Run, frontend on Vercel — judges can use it right now, no signup required
- Both products (signup testing + conversion audit) verified working against the live deployment

**The Ask**
Try it live — paste any URL and watch the agent work.

---

## 5. Demo Video Script (3 minutes)

**[0:00–0:15] Hook**
*(On screen: Sniff landing page / hero section)*

> "Every founder asks 'why aren't people signing up?' — and every analytics tool answers with a number, never a reason. Sniff is an AI agent that finds out why, by actually browsing your site like a confused first-time user would."

**[0:15–0:40] The problem, fast**
*(On screen: quick cuts — a funnel chart with a drop-off, a session-recording tool, a paywalled competitor report)*

> "Session recordings don't scale. Analytics show what happened, not why. And the audit tools that do explain *why* — lock most of their findings behind a paywall. We built something that shows everything, and does it autonomously."

**[0:40–1:20] Demo 1 — Signup flow test**
*(On screen: navigate to /dashboard/new-run, fill in a URL + goal "Sign up for an account" + pick a persona)*

> "Here's Sniff testing a real signup flow. I give it a goal and a persona — let's say a confused first-time user — and hit run."

*(Cut to: live progress view, agent stepping through screenshots)*

> "It's not clicking pre-recorded selectors. Each step, it looks at the actual screenshot and decides what a real person would do next — click the button, fill the field, scroll to find what's missing."

*(Cut to: completed run detail page showing diagnosis)*

> "When it can't complete the goal, it doesn't just say 'failed.' It gives you a diagnosis: root cause, severity, and who probably owns the fix — the same triage a human QA engineer would write, generated automatically."

**[1:20–2:10] Demo 2 — Landing page conversion audit**
*(On screen: switch to audit mode, paste a URL)*

> "The bigger feature: point Sniff at any landing page, and it audits it like a product manager would."

*(Cut to: completed audit report page — score hero, 5-dimension chart, annotated screenshot)*

> "It scores the page across five dimensions — message clarity, audience fit, action path, trust, and content depth. Here's the annotated screenshot showing exactly what it identified as the primary call-to-action, and what happened when it clicked it."

*(Scroll to: story timeline, strengths/gaps, copy rewrites)*

> "It narrates what it saw, step by step — what worked, what confused it, and where visitors are likely to bounce. Then it gives concrete fixes: not just 'improve your copy,' but the actual before-and-after rewrite."

**[2:10–2:40] How it works**
*(On screen: simple architecture diagram or the docs/architecture page)*

> "Under the hood, this runs on a three-tier reasoning stack. Deterministic checks handle the free stuff — colors, fonts, broken links, Core Web Vitals. A fast model, Jev, handles quick sanity checks and goal-reached decisions. And a vision-capable model, Gemini, paired with k2-horizon for text reasoning, handles the actual judgment calls — what to click, how to score the page, what to rewrite."

**[2:40–3:00] Close**
*(On screen: back to the dashboard / URL bar)*

> "It's live right now — backend on Cloud Run, frontend on Vercel, no signup required. Paste any URL, and watch an AI agent tell you the truth about your website. That's Sniff."

*(End card: URL + project name)*
