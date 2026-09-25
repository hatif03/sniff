# Session 01 Prompt: Planning & Market Research

**Session Type:** Plan Mode  
**Date:** 2025  
**Coins Used:** ~1.2  
**Output:** `sniff-expansion-plan.md`, three ADRs, full competitive analysis

---

## User Prompt

> Go through this repo. This is what I have built so far:
> - Sniff is an autonomous quality assurance system that simulates real user behavior to continuously test signup and onboarding experiences across mobile and web platforms.
> - Using AI-driven navigation powered by AWS Bedrock and browser automation through Playwright, Sniff explores signup flows with different user personas (confused first-time users, impatient users, careful users) to uncover issues that traditional testing might miss.
> - When problems are detected, Sniff's diagnosis engine classifies the root cause (backend failures, UX/content issues, performance problems, or integration errors), assigns severity levels (P0-P3), captures comprehensive evidence bundles with screenshots and traces, and immediately escalates critical issues to the right team via Slack with actionable reproduction steps.
> - This enables teams to catch signup-blocking bugs before real users encounter them, reducing customer abandonment and improving conversion rates through proactive, realistic user journey testing.
>
> Now I want you to plan how to expand this further.
> - First I want you to rename the project as 'sniff' everywhere.
> - Then perform market research for this app. Look for similar apps. Compare features. Find who our potential customers could be. What more features could we add.
> - Research this website: https://www.coldvisit.com/ I think this is a similar website and we can learn a lot from this. Here are its docs: https://www.coldvisit.com/docs
> - Then see how do we expand this project.
> - Update all packages to latest versions and see that nothing is breaking.
> - I want you to look into the architecture of our application.
> - We have a new AI model called jev from typesafe ai. First of all set up the skills to use that from here: https://docs.typesafe.ai/agent-skill - and now we have a spectrum - one end is deterministic scripts, the other end is reasoning models, and in between we have System One decision models like Jev. Earlier, we split our skills/instructions into two pieces for efficiency, and now they would be split into three: deterministic, decisions, and reasoning — things that could be moved to decisions will go to system one modes; things that could be purely deterministic will go to traditional code, and the decision will sit with Jev. Look at new architectures and frameworks spawning up.

## User Follow-Up (answering clarifying questions)

> 1. Jev / Typesafe AI access: Yes I already have a typesafe api key.
> 2. ColdVisit features priority: Journey replay UI is a priority. After that go for CI/CD integration.
> 3. Tailwind v4: Update to v4
> 4. Sniff Score weights: Update weights appropriately
> 5. Scheduler approach: I will leave this decision to you.
>
> Something else to add on from my side is that maintain proper documentation throughout the process. For every line of code you change document every decision, reason, motive behind it. Use ".gitignore" and ".bobignore" as well to help prevent the accidental exposure of credentials and other sensitive information. Have all the bob related files in this repository properly maintained.
