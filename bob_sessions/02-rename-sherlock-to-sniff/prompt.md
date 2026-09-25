# Session 02 Prompt: Rename sherlock → sniff

**Session Type:** Agent Mode  
**Date:** 2025  
**Coins Used:** ~1.8  
**Output:** All 27 source files, config, docs, env vars renamed

---

## Prompt

> Sub-Task 1 from `sniff-expansion-plan.md`:
>
> The project is internally called "sherlock" in every configuration file, package metadata,
> class names, CLI entry points, environment variables, Slack bot name, and documentation.
> Rename all occurrences to "sniff" to match the public brand.
>
> Requirements:
> - `pyproject.toml` name = `sniff`, entry point = `sniff`
> - `sniff-web/package.json` name = `sniff-web`
> - `SherlockConfig` → `SniffConfig` in all source files
> - All CLI commands: `sherlock` → `sniff`
> - All env vars: `SHERLOCK_*` → `SNIFF_*`
> - Slack bot name default → "Sniff Alert Bot"
> - Supabase bucket names: `sherlock-*` → `sniff-*`
> - Config file references: `sherlock.json` → `sniff.json`
> - DB path: `sherlock.db` → `sniff.db`
> - All markdown documentation files updated
> - `SHERLOCK_CLI_GUIDE.md` → `SNIFF_CLI_GUIDE.md`
> - `.env.example` variable names updated, Typesafe AI section added
>
> Also fix any pre-existing test issues found during the rename.
