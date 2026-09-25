# ADR-002: Dependency Update Strategy and Tailwind v4 Migration

## Status
Accepted

## Date
2025-01-01

## Context

The project dependencies have accumulated minimum-version lower bounds that are 12–18 months behind current stable releases. Running on outdated dependencies creates:

1. **Security exposure**: Older versions of packages may have known CVEs
2. **Compatibility drift**: As AWS SDK, Pydantic, and Playwright release breaking changes, staying on old versions increases the cost of future upgrades
3. **Missing features**: Playwright 1.52+ includes improved mobile emulation; Pydantic 2.11+ has better performance

Additionally, `sniff-web` uses Tailwind CSS v3. Tailwind v4 was released with significant architectural changes:
- CSS-first configuration replaces `tailwind.config.js`
- `@import "tailwindcss"` replaces the three `@tailwind` directives
- Some utility class names changed (e.g. `shadow-sm` → `shadow-xs`)
- The PostCSS plugin is now `@tailwindcss/postcss`

The question was whether to upgrade to Tailwind v4 now (breaking migration cost now) or later (accumulating tech debt). Decision: upgrade now while the project is young and the component surface area is manageable.

## Decision

1. Update all Python dependencies in `sniff-ai/pyproject.toml` to latest stable versions with exact lower bounds
2. Update all Node dependencies in `sniff-web/package.json` to latest stable versions
3. Migrate `sniff-web` from Tailwind v3 to v4:
   - Remove `tailwind.config.ts`
   - Replace `@tailwind` directives in `globals.css` with `@import "tailwindcss"`
   - Update PostCSS config to use `@tailwindcss/postcss`
   - Run the official `npx @tailwindcss/upgrade` codemod
   - Manually audit and fix any utilities renamed in v4

## Rationale

| Option | Considered | Rejected because |
|---|---|---|
| Update all packages + Tailwind v4 (chosen) | ✅ | — |
| Update packages, hold Tailwind v3 | ✅ | Tech debt grows; v4 migration cost only increases as more components are added |
| Hold all packages | ✅ | Security and compatibility risk; incompatible with newer SDK features needed |
| Tailwind v4 only, no Python update | ✅ | Partial — doesn't address the Python security/compatibility risk |

## Consequences

**Positive:**
- Dependencies at latest stable; security exposure minimized
- Tailwind v4 CSS-native config is simpler and faster (no Node.js config file)
- Tailwind v4 removes the JIT compilation overhead at build time
- All future component work starts on the modern Tailwind v4 API

**Negative / Trade-offs:**
- Tailwind v4 migration requires manual audit of renamed utilities
- `rich >=14.0.0` may have API changes for console formatting in the CLI
- `typer >=0.16.0` has API changes for some decorators — test all CLI commands after upgrade

**Neutral:**
- `uv.lock` will be regenerated from scratch (expected behavior)
- `yarn.lock` will be regenerated

## Implementation Notes

Python package update order:
1. Update `pyproject.toml` with new version bounds
2. Run `uv lock --upgrade` to regenerate lock
3. Run `uv run pytest tests/` to verify no regressions

Tailwind v4 migration steps:
1. `yarn add tailwindcss@^4 @tailwindcss/postcss@^4`
2. `yarn remove autoprefixer` (no longer needed in v4)
3. Update `postcss.config.mjs`: replace `tailwindcss` plugin with `@tailwindcss/postcss`
4. Update `globals.css`: replace directives with `@import "tailwindcss"`
5. Delete `tailwind.config.ts`
6. Move theme customizations to CSS `@theme` block in `globals.css`
7. Run `yarn build` and fix any renamed utility errors
