# Session 03: Dependency Updates + Tailwind v4 Migration

**Session Type:** Agent Mode
**Status:** ✅ Complete
**Date:** 2026-09-26

---

## Objectives

Bring Python and Node dependencies to current latest stable versions, migrate `sniff-web` to Tailwind v4, and fix any pre-existing test breakage found along the way.

---

## What Actually Happened (across two passes)

### Pass 1: Python already current, Node bumped

Live registry checks (PyPI/npm, not assumed) found the Python floors in `pyproject.toml`/`requirements.txt` were **already at that day's latest** (playwright 1.63, boto3 1.43, pydantic 2.13, httpx 0.28, supabase 2.31, pytest 9.1, ruff 0.16) — no changes needed there in this pass.

`sniff-web` was behind: bumped `next` 15.3→16.3, `react`/`react-dom` 19.1→19.3, `tailwindcss`/`@tailwindcss/postcss` 4.0→4.3, `@supabase/supabase-js` 2.50→2.117, `framer-motion` 12.33→13.x, `gsap`, `lenis`.

**Deviation from the original prompt**: `typescript` and `eslint` were deliberately **pinned back** from their absolute latest (7.0/10.x) rather than bumped all the way — `typescript-eslint` (pulled in by `eslint-config-next`) hard-blocks TypeScript 7.0, and ESLint 10 removed an API (`context.getFilename()`) that `eslint-config-next`'s bundled `eslint-plugin-react` still calls. Landed on `typescript@6.0.3` / `eslint@9.39.5` — the newest versions that actually build and lint clean. `next lint` was also removed in Next 16; the `lint` script now calls `eslint .` directly against a new flat `eslint.config.mjs` (the old `.eslintrc.json` doesn't work without the Next CLI shim).

Also deleted `sniff-web/tailwind.config.ts` (dead weight — `app/globals.css`'s v4 `@theme` block already mirrored every token) and cleaned up a redundant `package-lock.json` a dependency-bump pass introduced despite this project using `yarn.lock` as its real lockfile.

### Pass 2 (this session): removed boto3, added the two new provider SDKs

As part of the provider swap (see the architecture ADR and this session's bigger summary), `boto3`/`botocore` came out entirely (no more AWS Bedrock calls anywhere) and two new dependencies went in: `google-genai>=2.25,<3` (Vertex AI Gemini SDK) and `openai>=1.50.0` (used as an OpenAI-compatible client against k2-horizon/ifm.ai, per ifm.ai's own docs recommending exactly that reuse rather than a bespoke client) plus `google-auth` for Application Default Credentials.

---

## Why These Specific Decisions

**Pin back over force-upgrade**: A "latest" that doesn't build is worse than a working one-minor-version-back. Documented the exact incompatibility (not just "it broke") so a future re-check has something concrete to verify against before trying to bump further.

**Reuse `openai` for k2-horizon rather than hand-roll an HTTP client**: ifm.ai's own docs literally say `pip3 install openai` and use the standard client with a custom `base_url` — following the vendor's documented pattern rather than reinventing it.

---

## Verification

- `uv run --extra dev pytest` and `yarn build && yarn lint` both green after each pass.
- Live-tested the real k2-horizon endpoint with a real API key (see Session 12) to confirm the `openai`-package approach actually works against ifm.ai, not just against mocks.

---

## Next Steps

→ Session 04: Jev client (real API, not the originally-planned skill-file design — see that session's summary for why)
