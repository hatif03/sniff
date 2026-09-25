# Session 03: Dependency Updates + Tailwind v4 Migration

**Session Type:** Agent Mode  
**Status:** 🔄 In Progress (Python ✅ done, Node ⬜ yarn install pending)  
**Coins Used:** ~1.5  
**Date:** 2025

---

## Objectives

1. Update all Python dependencies to latest stable
2. Add new dependencies: `apscheduler`, `fastapi`, `uvicorn`
3. Update all Node dependencies to latest stable
4. Migrate Tailwind CSS v3 → v4 (breaking change)
5. Fix pre-existing issues discovered during upgrade
6. Verify all 67 tests pass

---

## Python Dependencies (sniff-ai) — ✅ COMPLETE

### Version Updates Applied

| Package | Was | Now | Breaking Changes |
|---|---|---|---|
| `playwright` | ≥1.40.0 | ≥1.63.0 | None for our usage |
| `boto3` | ≥1.34.0 | ≥1.43.0 | None |
| `pydantic` | ≥2.5.0 | ≥2.13.0 | None (we already use v2 API) |
| `typer` | ≥0.9.0 | ≥0.27.0 | CLI decorator style changed; tested OK |
| `rich` | ≥13.7.0 | ≥15.0.0 | New color system; no breaking changes for our console usage |
| `httpx` | ≥0.25.0 | ≥0.28.0 | None |
| `supabase` | ≥2.3.0 | ≥2.31.0 | None for our usage |
| `Pillow` | ≥10.0.0 | ≥11.0.0 | None |
| `pytest` | ≥7.4.0 | ≥9.1.0 | `asyncio_mode` config required (see below) |
| `pytest-asyncio` | ≥0.21.0 | ≥1.4.0 | Strict mode default changed |
| `ruff` | ≥0.1.0 | ≥0.16.0 | None |

### New Dependencies Added

| Package | Version | Reason |
|---|---|---|
| `apscheduler` | ≥3.11.0 | Scheduler daemon for Session 06 (ADR-003) |
| `fastapi` | ≥0.115.0 | Webhook trigger endpoint for scheduler |
| `uvicorn` | ≥0.34.0 | ASGI server for FastAPI webhook |

### `uv sync` Result

Resolved and installed 74 packages cleanly. Lock file regenerated.

---

## Pre-existing Issues Fixed

### Issue 1: `src` module not found in tests

**Problem**: All 4 test files failed collection with `ModuleNotFoundError: No module named 'src'` because no pytest `pythonpath` configuration existed.

**Fix**: Added `[tool.pytest.ini_options]` section to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
pythonpath = ["."]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Reason for `pythonpath = ["."]`**: This is the modern pytest-recommended approach over `conftest.py` sys.path manipulation. It adds the project root to Python's path, making `from src.xxx import yyy` work in tests.

### Issue 2: `datetime.utcnow()` deprecated in Python 3.13

**Problem**: 64 deprecation warnings across 4 source files and 1 test file using `datetime.utcnow()`, which is removed in Python 3.14.

**Files fixed**:
- `src/core/state_machine.py`
- `src/core/models.py`
- `src/diagnosis/classifier.py`
- `src/agent/decision_service.py`
- `tests/test_orchestrator.py`

**Fix**: Changed all `datetime.utcnow()` → `datetime.now(timezone.utc)` and added `timezone` to imports.

**Why fix now**: Running with `-W error::DeprecationWarning` to prevent warnings from accumulating. Clean is better.

### Issue 3: `PersonaManager` import in test_integration.py

**Problem**: `tests/test_integration.py` imported `PersonaManager` from `src.core.persona`, which doesn't exist.

**Fix**: Removed the unused import.

**Root cause**: Pre-existing dead import — the class was likely planned but never implemented.

---

## Test Results After Fixes

```
67 tests passed | 0 warnings | 0 failures
```

Run command: `uv run pytest tests/test_orchestrator.py tests/test_agent_service.py tests/test_agent_worker_contract.py -W error::DeprecationWarning`

*(test_integration.py excluded — requires Playwright browser which needs `uv run playwright install` first)*

---

## Tailwind v4 Migration (sniff-web) — ✅ Files Updated

### What Tailwind v4 Changes

| Aspect | v3 | v4 |
|---|---|---|
| Config file | `tailwind.config.ts` | Removed — CSS-native config |
| CSS directives | `@tailwind base/components/utilities` | `@import "tailwindcss"` |
| PostCSS plugin | `tailwindcss` | `@tailwindcss/postcss` |
| Autoprefixer | Required | Built-in — no longer needed |
| Theme customization | `tailwind.config.ts` theme.extend | `@theme { }` block in CSS |

### Files Changed

| File | Change |
|---|---|
| `sniff-web/package.json` | `tailwindcss: ^4.0.0`, `@tailwindcss/postcss: ^4.0.0` added; `autoprefixer` removed |
| `sniff-web/postcss.config.mjs` | Plugin changed from `tailwindcss` to `@tailwindcss/postcss` |
| `sniff-web/app/globals.css` | `@tailwind` directives → `@import "tailwindcss"`; theme colors/fonts moved to `@theme {}` block |
| `sniff-web/tailwind.config.ts` | **Deleted** — config now lives in `globals.css` |

### Design Tokens Migrated to `@theme` Block

```css
@theme {
  --color-background: #F7F8FA;
  --color-surface: #FFFFFF;
  --color-accent: #4F46E5;
  --color-soft-accent: #7C83FD;
  --color-warning: #D97706;
  --color-critical: #DC2626;
  --color-text: #111827;
  --color-muted: #6B7280;
  --font-display: var(--font-space-grotesk), sans-serif;
  --font-body: var(--font-inter), sans-serif;
  --font-mono: var(--font-jetbrains-mono), monospace;
}
```

These automatically generate Tailwind utility classes: `bg-background`, `text-accent`, `font-display`, etc.

---

## Pending (Not Yet Run)

⬜ `yarn install` in `sniff-web/` — `node_modules` does not exist yet  
⬜ `yarn build` to verify Tailwind v4 compiles clean  
⬜ Audit component files for renamed utilities (e.g. `shadow-sm` → `shadow-xs` in some v4 versions)

**Why not yet run**: User requested documentation session before continuing. Will be completed in the next agent session.

---

## Deviations from Plan

None — all planned changes were applied. The three pre-existing bug fixes were bonus improvements found during the upgrade process (not originally scoped but correct to fix).

---

## Next Steps

⬜ Run `yarn install` + `yarn build` in `sniff-web/` to complete this session  
→ Session 04: Typesafe AI Jev client setup  
→ Session 05: Three-tier architecture implementation
