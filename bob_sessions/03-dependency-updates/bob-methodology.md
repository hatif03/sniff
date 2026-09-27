# Session 03: Bob Methodology — Dependency Updates + Tailwind v4

## Bob Mode Used

**Agent Mode**

This session ran in two passes, as documented in the session summary. The Bob methodology differed between the two passes.

---

## Bob Tools and Techniques

### Live Registry Lookups (Not Assumed Versions)
Bob did not assume what "latest stable" meant. It queried PyPI and npm registries live to find the actual latest versions for each package. This is critical for a dependency update session: pinning to a version you looked up 6 months ago is not the same as pinning to the version that is current today.

Finding: the Python floors in `pyproject.toml` were already at that day's latest versions. Bob reported this honestly — "no changes needed on Python" — rather than bumping versions that did not need bumping.

### Breaking-Change Analysis Before Writing
For Node packages, Bob did not blindly bump all versions to latest. It specifically investigated:
- `typescript@7.0` — rejected because `typescript-eslint` hard-blocks it
- `eslint@10.x` — rejected because it removed `context.getFilename()` which `eslint-config-next` still calls

Bob landed on the highest versions that actually build and lint clean (`typescript@6.0.3`, `eslint@9.39.5`), not the absolute latest numbers. This is the correct engineering discipline: **a version that does not build is worse than a one-minor-version-back**.

### Build Verification After Every Change
After each package change, Bob ran:
- `uv run --extra dev pytest` — to verify Python tests
- `yarn build` — to verify Next.js build
- `yarn lint` — to verify linting

Both had to be clean before the session was called done. This catch-and-verify loop is essential for dependency updates, where breakage is often silent until you actually build.

### Tailwind v4 Migration
Bob executed the Tailwind v4 migration as specified in the plan:
1. Deleted `tailwind.config.ts` (dead weight; the `@theme` block in `globals.css` already had all tokens)
2. Updated `postcss.config.mjs` to use `@tailwindcss/postcss`
3. Updated `globals.css` to use `@import "tailwindcss"` with an `@theme` block

Bob verified the migration via the compiled CSS output, not just the source file. This is the right approach: Tailwind v4's token system is processed at build time, and the real test is whether the compiled output contains the expected utility classes.

### Intentional Deviation: Not Following the Exact Version Numbers in the Prompt
The original prompt specified specific version numbers to upgrade to. Bob deviated from these where the version numbers were outdated (e.g., `next ^15.3.0` in the prompt vs the actual current `next@16.3` at the time). Bob documented this deviation and its reasoning rather than silently following the prompt's outdated numbers.

### Pass 2: Provider Swap Dependencies
The second pass in this session (documented in the session summary as happening during Session 12) removed `boto3`/`botocore` and added:
- `google-genai>=2.25,<3` (Vertex AI Gemini SDK)
- `openai>=1.50.0` (reused as OpenAI-compatible client for k2-horizon/ifm.ai)
- `google-auth` (for Application Default Credentials)

The decision to reuse the `openai` package for k2-horizon rather than writing a custom HTTP client came from reading ifm.ai's own documentation: their docs literally say `pip3 install openai` and use the standard client with a custom `base_url`. Following the vendor's documented pattern is always preferable to inventing an equivalent.

---

## Key Bob Discipline Applied

**Pin back over force-upgrade.** Bob documented each compatibility block explicitly — not just "it broke" but the exact incompatibility (which package, which API, which version constraint). This gives a future session something concrete to check against when attempting to bump further. Bob did not hide deviations from the prompt; it documented them.
