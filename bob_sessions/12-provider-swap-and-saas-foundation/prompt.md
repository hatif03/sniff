# Session 12 Prompt: Provider Swap + SaaS Foundation

**Session Type:** Agent Mode
**Date:** 2026-09-26

---

## Prompt (paraphrased from the actual request)

> Remove any existence of the previous internal codename from the repo entirely (including inside these session folders - update them honestly instead of leaving them alone).
>
> Stop using AWS Bedrock. Use k2-horizon (ifm.ai) as the reasoning model, with a real API key. As a fallback for anything vision-related, use Gemini via Google Cloud (a `gcloud` CLI was already authenticated on this machine) - use the cloud for anything needed. Here's a real Jev (Typesafe AI) API key too.
>
> Now think about how to actually serve this to anyone - how do we deploy this so anyone can use it as a SaaS product? The website and the backend should not be a separate entity, they should work together.
>
> Make the UI look like a professional, high-end SaaS people could pay for - use something like Radix/shadcn for a consistent design system, a good chart library, a distinguished color palette, and real animation/micro-animation work (framer-motion/gsap, already installed).
>
> Expand what the analysis can provide - more metrics, more analysis, more tests - look at competitors and at PostHog's AI feature set for inspiration.
>
> Make a plan for all of this and only then start making changes.

---

## Pre-Session Context

This session followed directly after Sessions 03-05 (dependency updates, Jev client, three-tier architecture) and the earlier rename work. Two real API keys were provided this session (k2-horizon/ifm.ai and Jev/Typesafe) and stored immediately in the gitignored `.env` - never printed again in full after that.
