# Session 02: Rename the Project's Original Internal Name to Sniff

**Session Type:** Agent Mode  
**Status:** ✅ Complete  
**Coins Used:** ~1.8  
**Date:** 2025

---

## Objectives

Rename every reference to the project's original internal name (in any casing) to "sniff/Sniff/SNIFF" across the entire monorepo, matching the public brand name.

---

## Scope of Changes

### Python Source Files Changed (27 files)

All files in `sniff-ai/src/` and `sniff-ai/tests/`:

| Pattern Changed | Before | After |
|---|---|---|
| Main config class | *(previous codename)* | `SniffConfig` |
| All env var reads | *(previous codename prefix)* | `os.getenv('SNIFF_ENV', ...)` |
| DB path default | *(previous codename)* | `./data/sniff.db` |
| Config file default | *(previous codename)* | `./data/sniff.json` |
| Supabase buckets | *(previous codename prefix)* | `sniff-screenshots` |
| Slack bot name | *(previous codename)* | `"Sniff Alert Bot"` |
| All docstrings/comments | *(previous codename)* | "Sniff" |
| CLI command text | *(previous codename)* | `sniff run ...` |

### Config & Package Files

| File | Change |
|---|---|
| `sniff-ai/pyproject.toml` | `name = "sniff"`, entry point `sniff = "src.cli.main:app"`, description updated, keywords updated, URLs updated |
| `sniff-web/package.json` | `name = "sniff-web"` |
| `sniff-ai/.env.example` | All vars renamed to the `SNIFF_*` prefix; Typesafe AI section added; AWS profile comment updated |
| CLI guide file | **Renamed** to `SNIFF_CLI_GUIDE.md` |

### Markdown Documentation (17 files)

All `.md` files in `sniff-ai/` and `sniff-web/` updated:
- `README.md` (both projects)
- `ARCHITECTURE.md`, `PRODUCT_REQUIREMENTS.md`
- `AWS_PROFILE_SETUP.md`, `DEPLOYMENT_GUIDE.md`
- `DEMO_SETUP.md`, `DISTRIBUTION_PACKAGE.md`
- All files in `sniff-ai/docs/`

### Pre-existing Bug Fixed

**Issue**: `tests/test_integration.py` imported `PersonaManager` which did not exist in `src/core/persona.py` — this was a dead import that caused collection failure.

**Fix**: Removed the unused import. This was a pre-existing issue unrelated to the rename.

**Root cause**: The class was probably planned but never implemented; the import was left in.

---

## Why These Specific Decisions

### Decision: PowerShell bulk replacement vs file-by-file editing

Using PowerShell `Set-Content` with regex replacement across all 27 files simultaneously was chosen over editing each file individually. Rationale: the rename is purely mechanical — no logic changes — and bulk replacement is faster and less error-prone than manual per-file edits.

### Decision: Keep `src.*` internal import paths unchanged

The Python package structure uses `from src.core.config import ...`. These were intentionally NOT changed from `src` to any other prefix, because:
1. `src.*` is the Python package path, not a brand name
2. Changing it would require restructuring the entire package

### Decision: Add Typesafe AI section to `.env.example` during rename

Since the rename session touched `.env.example` anyway, the Typesafe AI config variables (`TYPESAFE_API_KEY`, `TYPESAFE_MODEL_ID`, `SNIFF_JEV_ENABLED`) were added at the same time to avoid a second touch of the file.

---

## Verification

**Method**: PowerShell `Select-String` grep for remaining occurrences of the project's original internal name (in any casing) in all `.py` files after changes.

**Result**: **0 remaining occurrences** in Python source files or pyproject.toml.

**67 tests pass** after the rename (run with `uv run pytest`).

---

## Files Summary

| Category | Count | Status |
|---|---|---|
| Python source files | 27 | ✅ All renamed |
| Test files | 4 | ✅ All renamed (+ 1 bug fixed) |
| Config files | 2 | ✅ `pyproject.toml`, `package.json` |
| Environment template | 1 | ✅ `.env.example` |
| CLI guide | 1 | ✅ Renamed file |
| Markdown docs | 17 | ✅ All renamed |

---

## Next Steps

→ Session 03: Dependency updates + Tailwind v4 migration
