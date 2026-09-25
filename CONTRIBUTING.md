# Contributing to Sniff

> **Sniff** is an autonomous quality assurance system that simulates real user behaviour to continuously test signup and onboarding experiences across mobile and web platforms.

Thank you for contributing. This guide covers how to set up the project locally, the coding conventions we follow, how to document your decisions, and the process for adding new features.

---

## Table of Contents

1. [Repository Structure](#repository-structure)
2. [Local Setup](#local-setup)
3. [Running Tests](#running-tests)
4. [Coding Conventions](#coding-conventions)
5. [Documentation Discipline](#documentation-discipline)
6. [Architecture Decision Records (ADRs)](#architecture-decision-records-adrs)
7. [Security Rules](#security-rules)
8. [Adding a New Feature](#adding-a-new-feature)
9. [Pull Request Checklist](#pull-request-checklist)

---

## Repository Structure

```
sniff/
├── sniff-ai/           # Python backend — autonomous test runner, CLI, AI agents
│   ├── src/            # All source code
│   │   ├── agent/      # AI decision services (Bedrock, Jev, tier routing)
│   │   ├── cli/        # Typer CLI commands
│   │   ├── core/       # Models, orchestrator, state machine, config
│   │   ├── diagnosis/  # Root cause classifier
│   │   ├── evidence/   # Report builder, scorer, comparator
│   │   ├── executor/   # Playwright browser worker
│   │   ├── integrations/ # Supabase client
│   │   ├── personas/   # JSON persona definitions
│   │   └── scheduler/  # APScheduler daemon
│   └── tests/          # pytest test suite
├── sniff-web/          # Next.js frontend — dashboard and journey replay UI
├── sniff-action/       # GitHub Actions integration (CI/CD plugin)
├── docs/
│   └── adr/            # Architecture Decision Records
├── .gitignore          # Repo-wide secret and artifact exclusions
├── .bobignore          # Bob AI agent context exclusions
├── CONTRIBUTING.md     # This file
└── sniff-expansion-plan.md  # Roadmap and sub-task tracker
```

---

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Yarn
- An AWS account with Bedrock access (Claude Sonnet)
- A Typesafe AI account and API key (for Jev)

### Python (sniff-ai)

```bash
cd sniff-ai

# Install dependencies
uv sync

# Copy and fill in environment variables
cp .env.example .env
# Edit .env with your AWS credentials, Typesafe API key, Slack webhook, etc.

# Install Playwright browsers
uv run playwright install chromium

# Verify setup
uv run sniff preflight
```

### Node.js (sniff-web)

```bash
cd sniff-web

# Install dependencies
yarn install

# Copy and fill in environment variables
cp .env.local.example .env.local
# Edit .env.local with your Supabase URL and anon key

# Start the development server
yarn dev
```

---

## Running Tests

### Python tests

```bash
cd sniff-ai

# Run all tests
uv run pytest

# Run a specific test file
uv run pytest tests/test_orchestrator.py -v

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing
```

### Node.js (type check + lint)

```bash
cd sniff-web

# Type check
yarn tsc --noEmit

# Lint
yarn eslint .

# Build (catches compile errors)
yarn build
```

---

## Coding Conventions

### Python

1. **Module docstrings**: Every Python file must begin with a module-level docstring stating:
   - What the module does
   - Where it fits in the architecture
   - Any non-obvious decisions made in the file

   ```python
   """
   src/agent/jev_client.py
   
   Wraps the Typesafe AI API to invoke Jev skills (System One decision model).
   
   Architecture note: This client is Tier 2 in the three-tier intelligence model.
   It handles fast, frequent navigation decisions. Deep reasoning (diagnosis,
   persona review) is handled by the Tier 3 BedrockClient.
   
   Decision: We use httpx (already a project dependency) rather than a dedicated
   Typesafe SDK to avoid adding a new dependency for a simple HTTP wrapper.
   """
   ```

2. **Class docstrings**: Every class must have a docstring explaining its role.
3. **Non-obvious logic**: Add inline `# Reason:` comments explaining *why*, not *what*.
4. **Type hints**: All function signatures must be fully type-annotated.
5. **Pydantic models**: Use `BaseModel` for all data contracts. Never use raw `dict`.
6. **No hardcoded values**: Configuration belongs in `SniffConfig` and sourced from env vars.

### TypeScript (sniff-web)

1. **File headers**: Every new file should have a brief comment block at the top explaining its purpose.
2. **No `any`**: TypeScript strict mode is enabled — avoid `any` types.
3. **Component docstrings**: Every React component should have a JSDoc comment.
4. **Server vs client**: Be explicit about `"use client"` when needed; default to Server Components.

### General

- **No TODO/FIXME without a linked issue**: If you leave a TODO, create a GitHub issue and link it.
- **Keep commits atomic**: One logical change per commit.
- **Commit messages**: `type(scope): description` — e.g. `feat(jev): add navigation_decision skill`.

---

## Documentation Discipline

Every code change must be accompanied by documentation that explains **why** the change was made, not just what changed.

### Levels of documentation

| Level | When | Format |
|---|---|---|
| Inline comment | Non-obvious logic | `# Reason: ...` in-line |
| Function/class docstring | Every public function/class | Docstring |
| Module docstring | Every Python file | Top of file |
| ADR | Major architectural decisions | `docs/adr/ADR-XXX-<topic>.md` |

### What counts as a "major architectural decision" requiring an ADR?

- Choosing one library/framework over another
- Introducing a new external dependency
- Changing the data model in a breaking way
- Changing how two components communicate
- Any decision that if reversed would require significant rework

---

## Architecture Decision Records (ADRs)

ADRs live in `docs/adr/`. They use the format in `docs/adr/ADR-000-template.md`.

**To create a new ADR:**

1. Copy `docs/adr/ADR-000-template.md` to `docs/adr/ADR-XXX-<short-name>.md`
2. Fill in all sections
3. Set status to `Accepted` when the decision is implemented
4. Commit the ADR in the same PR as the code that implements it

**Existing ADRs:**

| # | Title | Status |
|---|---|---|
| [ADR-001](docs/adr/ADR-001-three-tier-architecture.md) | Three-Tier Intelligence Architecture | Accepted |
| [ADR-002](docs/adr/ADR-002-dependency-updates.md) | Dependency Update Strategy and Tailwind v4 Migration | Accepted |
| [ADR-003](docs/adr/ADR-003-scheduler-apscheduler.md) | Scheduler Approach — APScheduler In-Process Daemon | Accepted |

---

## Security Rules

These rules are non-negotiable:

1. **Never commit secrets**: API keys, passwords, webhook URLs, and AWS credentials must only ever exist in `.env` files (which are `.gitignore`d). See `.gitignore` for the full exclusion list.

2. **Never hardcode credentials in source**: Config must come from environment variables via `SniffConfig`.

3. **`.env.example` is the canonical reference**: When adding a new env variable, add it to `.env.example` with a placeholder value and a comment explaining what it is.

4. **Audit before pushing**: Run `git diff --cached` and review every line before committing. If you see an actual key value (not a placeholder), abort and remove it.

5. **If you accidentally commit a secret**: Rotate the credential immediately (before telling anyone the commit exists), then remove it from history with `git filter-branch` or `git rebase`.

6. **`sniff.json` / `sherlock.json` are always ignored**: These files are generated by `sniff init` and contain API keys. They are in `.gitignore` and must never be committed.

---

## Adding a New Feature

1. **Check the roadmap**: Review `sniff-expansion-plan.md` to see if your feature is already planned.
2. **Write an ADR**: If your feature involves an architectural decision, write an ADR first.
3. **Implement with documentation**: Follow the documentation discipline above.
4. **Write tests**: New functionality requires unit tests. Integration tests for new CLI commands.
5. **Update `.env.example`**: If you add new config keys.
6. **Update `SNIFF_CLI_GUIDE.md`**: If you add new CLI commands.

---

## Pull Request Checklist

Before opening a PR, verify:

- [ ] No secrets in the diff (`git diff --cached | grep -i "AKIA\|sk-\|eyJ\|password"`)
- [ ] All new Python files have module docstrings
- [ ] All new/changed functions are type-annotated
- [ ] Tests written for new logic
- [ ] `uv run pytest` passes locally
- [ ] `yarn build` passes (if sniff-web was changed)
- [ ] `.env.example` updated if new env vars were added
- [ ] ADR written if an architectural decision was made
- [ ] `sniff-expansion-plan.md` sub-task status updated if applicable
