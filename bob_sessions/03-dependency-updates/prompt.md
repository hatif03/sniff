# Session 03 Prompt: Dependency Updates + Tailwind v4 Migration

**Session Type:** Agent Mode  
**Date:** 2025  
**Coins Used:** ~1.5  
**Output:** Updated `pyproject.toml`, `package.json`, `globals.css`, Tailwind v4 migration

---

## Prompt

> Sub-Task 2 from `sniff-expansion-plan.md`:
>
> Bring all Python and Node packages to their latest stable versions. Tailwind v4 is a confirmed upgrade.
>
> Python packages to update (sniff-ai/pyproject.toml):
> - playwright ≥1.40.0 → latest stable
> - boto3 ≥1.34.0 → latest stable
> - pydantic ≥2.5.0 → latest stable
> - typer ≥0.9.0 → latest stable
> - rich ≥13.7.0 → latest stable
> - httpx ≥0.25.0 → latest stable
> - supabase ≥2.3.0 → latest stable
> - pytest ≥7.4.0 → latest stable
> - pytest-asyncio ≥0.21.0 → latest stable
> - ruff ≥0.1.0 → latest stable
> - Add: apscheduler (for Session 06), fastapi, uvicorn
>
> Node packages to update (sniff-web/package.json):
> - next ^15.1.6 → latest
> - react/react-dom ^19.0.0 → latest
> - @supabase/supabase-js ^2.95.3 → latest
> - tailwindcss ^3.4.0 → ^4.0.0 (BREAKING — migrate)
>
> Tailwind v4 migration:
> - Remove tailwind.config.ts
> - Update postcss.config.mjs: replace tailwindcss plugin with @tailwindcss/postcss
> - Update globals.css: replace @tailwind directives with @import "tailwindcss" + @theme block
> - Remove autoprefixer (v4 handles it natively)
>
> Also fix any pre-existing test issues found (pytest path resolution, deprecated APIs).
> All 67 tests must pass after the upgrade.
