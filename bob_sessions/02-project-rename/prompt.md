# Session 02 Prompt: Rename the Project's Original Internal Name to Sniff

**Session Type:** Agent Mode  
**Date:** 2025  
**Coins Used:** ~1.8  
**Output:** All 27 source files, config, docs, env vars renamed

---

## Prompt

> Sub-Task 1 from `sniff-expansion-plan.md`:
>
> The project is internally called by its original internal name in every configuration file, package metadata,
> class names, CLI entry points, environment variables, Slack bot name, and documentation.
> Rename all occurrences to "sniff" to match the public brand.
>
> Requirements:
> - `pyproject.toml` name = `sniff`, entry point = `sniff`
> - `sniff-web/package.json` name = `sniff-web`
> - Main config class renamed to `SniffConfig` in all source files
> - All CLI commands renamed to `sniff`
> - All env vars renamed to the `SNIFF_*` prefix
> - Slack bot name default → "Sniff Alert Bot"
> - Supabase bucket names renamed to the `sniff-*` prefix
> - Config file references updated to `sniff.json`
> - DB path updated to `sniff.db`
> - All markdown documentation files updated
> - CLI guide renamed to `SNIFF_CLI_GUIDE.md`
> - `.env.example` variable names updated, Typesafe AI section added
>
> Also fix any pre-existing test issues found during the rename.
