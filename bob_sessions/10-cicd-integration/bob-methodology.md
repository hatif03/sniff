# Session 10: Bob Methodology — CI/CD GitHub Actions Integration

## Bob Mode Used

**Agent Mode**

This session packages Sniff as a reusable GitHub Actions step — the only session that produces output outside the `sniff-ai/` and `sniff-web/` directories (the `sniff-action/` directory at repo root).

---

## Bob Tools and Techniques

### GitHub Actions Schema Knowledge
Bob generates the `action.yml` using the standard GitHub Actions composite action schema: `inputs` with `required`/`default` fields, `outputs` with `value` from `${{ steps.run.outputs.* }}`, and a Docker-based `runs` block. This is a well-documented format Bob applies directly.

### Exit Code as Public Contract
The `--exit-on-severity` flag on `sniff run` establishes a formal exit-code contract: exit 1 if the diagnosed severity is at or worse than the specified threshold (P0 is worst, P3 is least severe). This contract is the foundation that makes `sniff-action` work:
- CI pipelines check the process exit code
- The action maps exit code → `failure()` in the workflow

Bob reads `sniff-ai/src/cli/commands/run.py` before adding this flag — to use the exact Typer option syntax and to understand the run result structure that carries the severity value.

### Security: `--output-json` Pattern
The `--output-json <path>` flag writes machine-readable JSON to a file rather than relying on stdout parsing. This is more robust than parsing stdout output (which can contain progress bars, Rich formatting, and other text) and is the standard pattern for GitHub Actions output parsing.

### Documentation as Deliverable
`docs/CI_CD_INTEGRATION.md` is a primary deliverable of this session — a copy-paste-ready GitHub Actions workflow example with all credential secrets named correctly. Bob writes documentation that is immediately usable, not a placeholder.

### Dockerfile for Action Container
The action's `Dockerfile` uses `python:3.11-slim` as the base and installs Playwright with `--with-deps` (Playwright's own flag for installing system dependencies alongside browser binaries). The container includes everything needed to run `sniff run` in a GitHub Actions runner context — no external dependencies.

---

## Note on Deployment Context
The GitHub Actions action was designed before Cloud Run was the deployment target (Sessions 12–13 chose Cloud Run). The Docker container approach for the action is compatible with both local use and a future "trigger Sniff via the API" CI approach where the action calls the deployed FastAPI backend instead of running locally. This flexibility was not a design goal in Session 10 but emerged naturally from the containerised approach.
