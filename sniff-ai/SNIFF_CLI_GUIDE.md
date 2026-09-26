# Sniff CLI - Complete Usage Guide

**Autonomous Mystery Shopper for Mobile/Web Signup Flows**

Version: 1.0.0
Date: February 7, 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Commands Reference](#commands-reference)
5. [Configuration](#configuration)
6. [Personas](#personas)
7. [Running Tests](#running-tests)
8. [Troubleshooting](#troubleshooting)
9. [Advanced Usage](#advanced-usage)

---

## Overview

Sniff is an autonomous testing system that simulates real users navigating mobile and web signup flows. It uses AI-driven decision-making to detect friction points, diagnose root causes, and escalate issues via Slack alerts.

**Key Features:**
- 🤖 AI-powered autonomous navigation using Gemini (Vertex AI) and k2-horizon (ifm.ai)
- 📱 Mobile device emulation with Playwright
- 🎭 Configurable user personas (confused, impatient, careful)
- 🔍 Automatic failure diagnosis with P0-P3 severity classification
- 📊 Rich evidence collection (screenshots, traces, timing)
- 🔔 Slack integration for real-time alerting

---

## Installation

### Prerequisites

- Python 3.11+
- A Google Cloud project with the Vertex AI API enabled (for Gemini)
- An ifm.ai API key (for k2-horizon)
- Playwright browser binaries

### Install Sniff

```bash
# Clone repository
cd /path/to/Sniff

# Install with pip/uv
pip install -e .
# OR
uv pip install -e .

# Install Playwright browsers
playwright install
```

### Verify Installation

```bash
Sniff --help
```

---

## Quick Start

Complete setup in 3 steps:

### 1. Initialize Configuration

```bash
Sniff init
```

This interactive wizard will configure:
- **Gemini (Vertex AI)** - GCP project ID, region, model ID (auth via `gcloud auth application-default login`, not a key)
- **k2-horizon (ifm.ai)** - API key and model ID
- **Slack Alerts** - Optional webhook for notifications
- **Security** - Domain allowlist and safety settings
- **Defaults** - Device profile, network speed, personas

### 2. Validate Setup

```bash
Sniff preflight
```

Checks:
- ✅ Environment variables loaded (`GEMINI_PROJECT_ID`, `IFM_API_KEY`)
- ✅ Google Cloud Application Default Credentials valid
- ✅ Network connectivity to Gemini/k2-horizon endpoints
- ✅ Gemini invocation working
- ✅ k2-horizon invocation working
- ✅ Jev invocation working (if `TYPESAFE_ENABLED=true`)

### 3. Run Your First Test

```bash
Sniff run --goal "Complete signup with email verification"
```

---

## Commands Reference

### `Sniff init`

**Interactive configuration setup**

```bash
Sniff init [OPTIONS]
```

**Options:**
- `--config PATH` - Config file path (default: `./data/Sniff.json`)
- `--force` - Overwrite existing configuration

**What It Configures:**

**Gemini (Vertex AI) Configuration:**
- GCP project ID (`GEMINI_PROJECT_ID`)
- Vertex AI region (`GEMINI_REGION`, e.g., `us-central1`)
- Model ID and fallback model ID
- Auth is Application Default Credentials (`gcloud auth application-default login`), checked but not entered interactively - there's no key to type in

**k2-horizon (ifm.ai) Configuration:**
- API key (password-masked, saved as `IFM_API_KEY`)
- Model ID

**Security Settings:**
- Allowed domains (comma-separated)
- Domain allowlist enforcement (yes/no)

**Slack Integration (Optional):**
- Webhook URL
- Channel override
- Bot display name

**Guardrails:**
- Max steps per run (default: 50)
- Hard timeout in seconds (default: 600)

**Defaults:**
- Device profile (iPhone 13, Pixel 5, etc.)
- Network speed (4g, 3g, slow3g)

**Example:**
```bash
Sniff init
# Follow prompts...
✓ Initialization complete!
```

---

### `Sniff preflight`

**Validate the Gemini/k2-horizon/Jev setup**

```bash
Sniff preflight [OPTIONS]
```

**Options:**
- `--verbose` - Show detailed check output

**Checks Performed:**
1. Environment variables (`GEMINI_PROJECT_ID`, `IFM_API_KEY`, etc., from config + `.env`)
2. Google Cloud Application Default Credentials validity
3. Network connectivity to Gemini/k2-horizon endpoints
4. Gemini invocation (real Vertex AI call)
5. k2-horizon invocation (real ifm.ai call)
6. Jev invocation, only if `TYPESAFE_ENABLED=true`

**Example:**
```bash
Sniff preflight --verbose

Preflight Check Results
┌──────────────────────────┬─────────┬────────────────────────────────┐
│ Check                    │ Status  │ Details                        │
├──────────────────────────┼─────────┼────────────────────────────────┤
│ Environment Variables    │ ✅ PASS │ Gemini + k2-horizon configured  │
│ Google Cloud Credentials │ ✅ PASS │ ADC valid                      │
│ Network Connectivity     │ ✅ PASS │ Endpoints reachable            │
│ Gemini Invocation        │ ✅ PASS │ Success                        │
│ k2-horizon Invocation    │ ✅ PASS │ Success                        │
│ Jev Invocation           │ ✅ PASS │ Success                        │
└──────────────────────────┴─────────┴────────────────────────────────┘

✅ All checks passed! (6/6)
```

---

### `Sniff personas`

**Manage user behavior personas**

```bash
Sniff personas <COMMAND> [OPTIONS]
```

**Subcommands:**

#### `list` - Show all personas

```bash
Sniff personas list
```

Shows table of available personas with traits.

#### `show` - Display persona details

```bash
Sniff personas show <NAME>
```

Example:
```bash
Sniff personas show confused_first_time_user
```

#### `add` - Create new persona (LLM-assisted)

```bash
Sniff personas add
```

Interactive wizard:
1. Describe persona in natural language
2. LLM expands to normalized JSON
3. Preview and confirm/edit
4. Save to `src/personas/`

Example:
```bash
Sniff personas add
? Describe the persona: An elderly user who is not tech-savvy
# LLM generates complete persona profile
? Looks good? Yes
✓ Created persona: elderly_user
```

#### `test` - Validate persona file

```bash
Sniff personas test <NAME>
```

Validates JSON schema and required fields.

---

### `Sniff run`

**Execute autonomous test run**

```bash
Sniff run [OPTIONS]
```

**Required:**
- `--goal TEXT` - User-defined test goal (REQUIRED)

**Options:**
- `--persona NAME` - Persona to use (default: from config)
- `--url URL` - Starting URL (overrides config)
- `--device NAME` - Device profile (e.g., "iPhone 13")
- `--network SPEED` - Network speed (4g|3g|slow3g)
- `--headless/--headed` - Browser visibility (default: headless)
- `--max-steps INT` - Override max steps guardrail

**Examples:**

Basic run:
```bash
Sniff run --goal "Complete signup with document upload"
```

With persona and device:
```bash
Sniff run \
  --persona confused_first_time_user \
  --goal "Create account and verify email" \
  --device "iPhone 14" \
  --network 3g
```

Headed mode (visible browser):
```bash
Sniff run \
  --goal "Test signup flow" \
  --headed
```

**What Happens:**
1. Loads configuration and validates
2. Initializes Playwright with device emulation
3. Starts autonomous decision loop
4. Agent observes screen → makes decision → worker executes
5. Continues until goal complete or stuck
6. If stuck: diagnoses issue, captures evidence, sends alert
7. Generates run report with artifacts

**Output:**
```
Running Sniff Test Run...

Step 1: Navigate to signup page
Step 2: Tap "Create Account" button
Step 3: Type email into field
Step 4: Tap "Continue" button
...

✓ Goal completed in 12 steps
Run ID: run_abc123
Report: ./artifacts/run_abc123/report.json
```

---

### `Sniff report`

**Display run results**

```bash
Sniff report [OPTIONS] <RUN_ID>
```

**Options:**
- `--format FORMAT` - Output format (pretty|json) (default: pretty)

**Examples:**

Pretty terminal output:
```bash
Sniff report run_abc123
```

JSON output:
```bash
Sniff report run_abc123 --format json
```

List all runs:
```bash
Sniff report --list
```

**Report Contents:**
- Run metadata (ID, timestamp, duration)
- Goal and persona used
- Step-by-step action timeline
- Screenshots and traces
- Diagnosis (if failed)
- Severity and root cause
- Reproduction steps

---

### `Sniff alert`

**Manage Slack alerts**

```bash
Sniff alert <COMMAND>
```

**Subcommands:**

#### `test` - Send test alert

```bash
Sniff alert test
```

Validates webhook and sends sample alert.

#### `configure` - Update Slack settings

```bash
Sniff alert configure
```

Interactive update of webhook URL, channel, bot name.

---

### `Sniff demo`

**Deterministic demo mode**

```bash
Sniff demo [OPTIONS]
```

**Options:**
- `--scenario NAME` - Demo scenario to run

Runs pre-scripted path with known failure for judge presentations.

**Example:**
```bash
Sniff demo --scenario backend_timeout
```

---

## Configuration

### Configuration Files

**Primary Config:** `./data/Sniff.json`
- Structured settings (nested objects)
- Feature flags
- Paths and defaults

**Environment Variables:** `.env`
- Gemini project ID/region/model ID
- k2-horizon API key/model ID
- Slack webhook
- Sensitive values

### Environment Variables Reference

**Required:**
```bash
GEMINI_PROJECT_ID=your-gcp-project-id   # Auth via `gcloud auth application-default login`, not a key
GEMINI_REGION=us-central1
IFM_API_KEY=your-ifm-api-key
```

**Optional:**
```bash
GEMINI_MODEL_ID=gemini-3.5-flash-lite      # Primary Gemini model
GEMINI_FALLBACK_MODEL_ID=gemini-2.5-flash-lite  # Used if primary unavailable in region
IFM_MODEL_ID=IFM/K2-Horizon-375B-A23B      # k2-horizon model ID
SLACK_WEBHOOK_URL=https://...       # Slack webhook
SLACK_CHANNEL=#alerts               # Override channel
SNIFF_MAX_STEPS=50               # Max steps per run
SNIFF_HARD_TIMEOUT=600           # Timeout in seconds
```

See `.env.example` for the complete reference, including `TYPESAFE_*` variables for the optional Jev (Typesafe AI) Tier 2 model.

### Manual Configuration

Edit `.env` directly:
```bash
vi .env
```

Or set environment variables:
```bash
export GEMINI_PROJECT_ID="your-gcp-project-id"
export GEMINI_REGION="us-central1"
export IFM_API_KEY="your-ifm-api-key"
```

---

## Personas

### Built-in Personas

**confused_first_time_user**
- High exploration tendency
- May misinterpret labels
- Hesitates before actions
- Tests unclear UX patterns

**impatient_user**
- Low patience level
- Quick to abandon on delays
- Minimal exploration
- Sensitive to performance issues

**careful_user**
- Reads all labels thoroughly
- Validates before submit
- Thorough exploration
- Catches content issues

### Persona Schema

```json
{
  "name": "persona_id",
  "display_name": "Human Readable Name",
  "description": "Detailed persona description",
  "patience_level": 0.5,           // 0.0-1.0
  "technical_proficiency": 0.5,    // 0.0-1.0
  "exploration_tendency": 0.5      // 0.0-1.0
}
```

### Creating Custom Personas

**Option 1: CLI (LLM-assisted)**
```bash
Sniff personas add
? Describe the persona: A power user who knows exactly what they want
```

**Option 2: Manual JSON**
```bash
vi src/personas/my_persona.json
```

```json
{
  "name": "power_user",
  "display_name": "Power User",
  "description": "Expert user who navigates quickly and expects efficiency",
  "patience_level": 0.3,
  "technical_proficiency": 0.95,
  "exploration_tendency": 0.2
}
```

---

## Running Tests

### Basic Workflow

```bash
# 1. Initialize (first time only)
Sniff init

# 2. Validate setup
Sniff preflight

# 3. Run test
Sniff run --goal "Complete signup"

# 4. View results
Sniff report <run-id>
```

### Advanced Workflows

**Test different personas:**
```bash
for persona in confused_first_time_user impatient_user careful_user; do
  Sniff run --persona $persona --goal "Complete signup"
done
```

**Test different devices:**
```bash
Sniff run --goal "Signup" --device "iPhone 13"
Sniff run --goal "Signup" --device "Pixel 5"
```

**Test different network conditions:**
```bash
Sniff run --goal "Signup" --network 4g
Sniff run --goal "Signup" --network 3g
Sniff run --goal "Signup" --network slow3g
```

### Interpreting Results

**Success:**
```
✓ Goal completed in 12 steps
Severity: None
Evidence: ./artifacts/run_abc123/
```

**Failure with Diagnosis:**
```
✗ Stuck after 8 steps
Root Cause: Backend (P0)
Diagnosis: Server error 500 on /api/signup
Evidence: ./artifacts/run_abc123/
  - screenshots/
  - trace.json
  - execution.log
Slack Alert: Sent to #Sniff-alerts
```

---

## Troubleshooting

### Common Issues

#### "Google Cloud Credentials" check fails

**Solution:**
```bash
# Option 1: Run init again
Sniff init

# Option 2: Authenticate directly
gcloud auth application-default login
gcloud config set project <your-project-id>

# Option 3: Set the project in .env
echo "GEMINI_PROJECT_ID=<your-project-id>" >> .env
```

#### "IFM_API_KEY not set"

**Solution:**
```bash
# Add to .env
echo "IFM_API_KEY=your-ifm-api-key" >> .env
```

#### Preflight fails: "Gemini Invocation" or "PERMISSION_DENIED"

**Solution:**
1. Confirm the Vertex AI API is enabled: `gcloud services enable aiplatform.googleapis.com`
2. Confirm `GEMINI_PROJECT_ID` matches your active gcloud project
3. Try the default region (`GEMINI_REGION=us-central1`) if your model isn't available in the configured one
4. Run `Sniff preflight` again

#### "No module named 'src'"

**Solution:**
```bash
# Install in editable mode
pip install -e .
```

#### Run fails immediately

**Check:**
```bash
# 1. Validate config
Sniff preflight --verbose

# 2. Check .env exists
cat .env

# 3. Check logs
tail -f ./artifacts/latest/execution.log
```

### Debug Mode

**Verbose output:**
```bash
Sniff run --goal "Test" --headed
```

**Check trace logs:**
```bash
# Execution timeline
cat ./artifacts/<run-id>/trace.jsonl

# Each line is a JSON event:
# - observation
# - decision
# - action_result
# - diagnosis
```

---

## Advanced Usage

### Custom Configuration Path

```bash
Sniff init --config /custom/path/Sniff.json
Sniff run --config /custom/path/Sniff.json --goal "Test"
```

### Override Guardrails

```bash
Sniff run \
  --goal "Complex multi-step flow" \
  --max-steps 100
```

### Headed Mode for Debugging

Watch the browser in real-time:
```bash
Sniff run --goal "Debug signup" --headed
```

### JSON Reports for CI/CD

```bash
Sniff run --goal "Nightly test" > /dev/null
Sniff report <run-id> --format json > report.json

# Parse results
if jq -e '.outcome == "success"' report.json; then
  echo "Test passed"
  exit 0
else
  echo "Test failed"
  exit 1
fi
```

### Slack Alert Testing

```bash
Sniff alert test
# Sends sample alert to configured webhook
```

---

## Best Practices

### Goal Definition

**Good goals:**
- ✅ "Complete signup with email verification"
- ✅ "Upload document and submit application"
- ✅ "Create account and reach dashboard"

**Bad goals:**
- ❌ "Test the app" (too vague)
- ❌ "Click buttons" (not outcome-focused)
- ❌ "See if it works" (ambiguous success criteria)

### Persona Selection

- **confused_first_time_user** - Test UX clarity and help text
- **impatient_user** - Test performance and loading states
- **careful_user** - Test validation and error messages

### Domain Allowlist

Always configure allowed domains:
```bash
Sniff init
# When asked for allowed domains:
example.com,staging.example.com
```

This prevents autonomous actions on unintended sites.

### Regular Validation

```bash
# Run preflight before important test runs
Sniff preflight
```

---

## File Structure

```
Sniff/
├── .env                          # Environment variables (gitignored)
├── data/
│   ├── Sniff.json            # Main configuration
│   └── Sniff.db              # Run history
├── artifacts/
│   └── run_<id>/                # Per-run evidence
│       ├── screenshots/
│       ├── trace.jsonl
│       ├── execution.log
│       └── report.json
├── src/
│   └── personas/                # Persona JSON files
│       ├── confused_first_time_user.json
│       ├── impatient_user.json
│       └── careful_user.json
└── SNIFF_CLI_GUIDE.md        # This file
```

---

## Support

### Check Documentation

- `Sniff --help` - Command overview
- `Sniff <command> --help` - Command-specific help
- This guide - Complete reference

### Common Commands

```bash
# Show version
Sniff --version

# Get help
Sniff --help
Sniff run --help

# Validate setup
Sniff preflight --verbose

# List personas
Sniff personas list

# View recent runs
Sniff report --list
```

---

## Appendix

### Supported Models

**Gemini (Vertex AI)** - per-step vision-capable navigation decisions:
- `gemini-3.5-flash-lite` (default primary)
- `gemini-2.5-flash-lite` (default fallback)

**k2-horizon (ifm.ai)** - text-only goal enhancement, planning, persona review:
- `IFM/K2-Horizon-375B-A23B` (default)

**Jev (Typesafe AI, optional Tier 2)** - fast decision model:
- `jev-latest` (default, only used if `TYPESAFE_ENABLED=true`)

### Device Profiles

- iPhone 13, iPhone 14, iPhone 14 Pro
- Pixel 5, Galaxy S21
- Custom viewport sizes supported

### Network Profiles

- **4g** - Fast mobile (9 Mbps down, 1.6 Mbps up, 150ms RTT)
- **3g** - Standard mobile (1.6 Mbps down, 768 Kbps up, 300ms RTT)
- **slow3g** - Poor connection (400 Kbps down, 400 Kbps up, 2000ms RTT)

---

**Sniff CLI v1.0.0**
Autonomous Mystery Shopper System
Built for hackathon demo - February 2026
