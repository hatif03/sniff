# Session 10 Prompt: CI/CD GitHub Actions Integration

**Session Type:** Agent Mode  
**Status:** ⬜ Pending  
**Reference:** Sub-Task 8 in `sniff-expansion-plan.md`

---

## Prompt (to be given when this session starts)

> Sub-Task 8 from `sniff-expansion-plan.md`:
>
> Package Sniff as a GitHub Actions step so engineering teams can run signup flow tests as part of their deployment pipeline.
>
> 1. Create `sniff-action/` directory at the repo root with:
>
>    **`sniff-action/action.yml`** — GitHub Action definition:
>    - `name: "Sniff - Signup Flow QA"`
>    - `description: "Autonomously tests signup flows using AI-driven browser simulation"`
>    - Inputs:
>      * `goal` (required) — the test goal
>      * `url` (required) — target URL to test
>      * `persona` (optional, default: `careful_user`)
>      * `fail_on_severity` (optional, default: `P1`) — exit 1 if severity ≤ this level
>      * `max_steps` (optional, default: `50`)
>      * `slack_webhook_url` (optional) — send alerts to Slack
>    - Outputs:
>      * `run_id` — the Sniff run ID
>      * `severity` — P0/P1/P2/P3/NONE
>      * `sniff_score` — numeric score 0–100
>      * `report_url` — Supabase dashboard URL if uploaded
>    - runs-on: docker
>
>    **`sniff-action/Dockerfile`**:
>    - Base: `python:3.11-slim`
>    - Install: system Playwright deps + Python deps from requirements.txt
>    - Install Playwright browsers: `playwright install chromium --with-deps`
>    - Copy sniff-ai source
>    - Entrypoint: `/entrypoint.sh`
>
>    **`sniff-action/entrypoint.sh`**:
>    - Read inputs from `INPUT_*` env vars (GitHub Actions convention)
>    - Run: `sniff run --goal "$INPUT_GOAL" --url "$INPUT_URL" --persona "$INPUT_PERSONA" --max-steps "$INPUT_MAX_STEPS" --exit-on-severity "$INPUT_FAIL_ON_SEVERITY" --output-json /tmp/sniff-result.json`
>    - Parse `/tmp/sniff-result.json` to set GitHub Actions outputs
>    - Exit code: 1 if severity ≤ fail_on_severity, 0 otherwise
>
> 2. Add `--exit-on-severity` flag to `sniff-ai/src/cli/commands/run.py`:
>    - `--exit-on-severity [P0|P1|P2|P3]` option
>    - If diagnosis severity ≤ threshold: `sys.exit(1)`
>    - If goal succeeds with no diagnosis: `sys.exit(0)`
>    - `--output-json <path>` flag to write machine-readable JSON result
>
> 3. Create `docs/CI_CD_INTEGRATION.md`:
>    - GitHub Actions example workflow (copy-paste ready)
>    - How to configure `SNIFF_ALLOWED_DOMAINS` for staging URLs
>    - How to configure AWS credentials in GitHub Secrets
>    - How to use `fail_on_severity: P0` to allow P1 warnings but block P0 outages
>    - Example badge: `![Sniff Status](https://github.com/org/repo/actions/workflows/sniff.yml/badge.svg)`

---

## Pre-Session Checklist

Before starting this session, verify:
- [ ] Session 08 (Journey Replay UI) is complete
- [ ] `sniff run` CLI command has been reviewed and understood
- [ ] `sniff-ai/src/cli/commands/run.py` read before starting
