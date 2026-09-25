# Sherlock CLI - Complete Usage Guide

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

Sherlock is an autonomous testing system that simulates real users navigating mobile and web signup flows. It uses AI-driven decision-making to detect friction points, diagnose root causes, and escalate issues via Slack alerts.

**Key Features:**
- 🤖 AI-powered autonomous navigation using AWS Bedrock
- 📱 Mobile device emulation with Playwright
- 🎭 Configurable user personas (confused, impatient, careful)
- 🔍 Automatic failure diagnosis with P0-P3 severity classification
- 📊 Rich evidence collection (screenshots, traces, timing)
- 🔔 Slack integration for real-time alerting

---

## Installation

### Prerequisites

- Python 3.11+
- AWS account with Bedrock access
- Playwright browser binaries

### Install Sherlock

```bash
# Clone repository
cd /path/to/sherlock

# Install with pip/uv
pip install -e .
# OR
uv pip install -e .

# Install Playwright browsers
playwright install
```

### Verify Installation

```bash
sherlock --help
```

---

## Quick Start

Complete setup in 3 steps:

### 1. Initialize Configuration

```bash
sherlock init
```

This interactive wizard will configure:
- **AWS Credentials** - Access key/secret or CLI profile
- **Bedrock Model** - AI model for decision-making
- **Slack Alerts** - Optional webhook for notifications
- **Security** - Domain allowlist and safety settings
- **Defaults** - Device profile, network speed, personas

### 2. Validate Setup

```bash
sherlock preflight
```

Checks:
- ✅ Environment variables loaded
- ✅ AWS credentials valid
- ✅ Bedrock service accessible
- ✅ Model access enabled
- ✅ Network connectivity
- ✅ Model invocation working

### 3. Run Your First Test

```bash
sherlock run --goal "Complete signup with email verification"
```

---

## Commands Reference

### `sherlock init`

**Interactive configuration setup**

```bash
sherlock init [OPTIONS]
```

**Options:**
- `--config PATH` - Config file path (default: `./data/sherlock.json`)
- `--force` - Overwrite existing configuration

**What It Configures:**

**AWS Credentials (4 methods):**
1. **Manual Entry** - Enter access key/secret (password-masked)
2. **AWS CLI Profile** - Use existing `~/.aws/credentials` profile
3. **IAM Role** - For EC2/Lambda (no credentials stored)
4. **Skip** - Configure later manually

**Bedrock Configuration:**
- Model ID (e.g., `anthropic.claude-sonnet-4-5-20250929-v1:0`)
- AWS region (e.g., `us-west-2`)
- Optional fallback model for redundancy

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
sherlock init
# Follow prompts...
✓ Initialization complete!
```

---

### `sherlock preflight`

**Validate AWS and Bedrock setup**

```bash
sherlock preflight [OPTIONS]
```

**Options:**
- `--verbose` - Show detailed check output

**Checks Performed:**
1. Environment variables (AWS_REGION, BEDROCK_MODEL_ID, etc.)
2. AWS credentials validity (calls `sts:GetCallerIdentity`)
3. Bedrock service access (lists available models)
4. Specific model access enabled
5. Network connectivity to Bedrock endpoints
6. Model invocation test

**Example:**
```bash
sherlock preflight --verbose

Preflight Check Results
┌────────────────────────┬─────────┬──────────────────────┐
│ Check                  │ Status  │ Details              │
├────────────────────────┼─────────┼──────────────────────┤
│ Environment Variables  │ ✅ PASS │ All required present │
│ AWS Credentials        │ ✅ PASS │ Account: 982744...   │
│ Bedrock Service Access │ ✅ PASS │ 135 models available │
│ Model Access           │ ✅ PASS │ Model enabled        │
│ Network Connectivity   │ ✅ PASS │ Endpoints reachable  │
│ Model Invocation       │ ✅ PASS │ Success              │
└────────────────────────┴─────────┴──────────────────────┘

✅ All checks passed! (6/6)
```

---

### `sherlock personas`

**Manage user behavior personas**

```bash
sherlock personas <COMMAND> [OPTIONS]
```

**Subcommands:**

#### `list` - Show all personas

```bash
sherlock personas list
```

Shows table of available personas with traits.

#### `show` - Display persona details

```bash
sherlock personas show <NAME>
```

Example:
```bash
sherlock personas show confused_first_time_user
```

#### `add` - Create new persona (LLM-assisted)

```bash
sherlock personas add
```

Interactive wizard:
1. Describe persona in natural language
2. LLM expands to normalized JSON
3. Preview and confirm/edit
4. Save to `src/personas/`

Example:
```bash
sherlock personas add
? Describe the persona: An elderly user who is not tech-savvy
# LLM generates complete persona profile
? Looks good? Yes
✓ Created persona: elderly_user
```

#### `test` - Validate persona file

```bash
sherlock personas test <NAME>
```

Validates JSON schema and required fields.

---

### `sherlock run`

**Execute autonomous test run**

```bash
sherlock run [OPTIONS]
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
sherlock run --goal "Complete signup with document upload"
```

With persona and device:
```bash
sherlock run \
  --persona confused_first_time_user \
  --goal "Create account and verify email" \
  --device "iPhone 14" \
  --network 3g
```

Headed mode (visible browser):
```bash
sherlock run \
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
Running Sherlock Test Run...

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

### `sherlock report`

**Display run results**

```bash
sherlock report [OPTIONS] <RUN_ID>
```

**Options:**
- `--format FORMAT` - Output format (pretty|json) (default: pretty)

**Examples:**

Pretty terminal output:
```bash
sherlock report run_abc123
```

JSON output:
```bash
sherlock report run_abc123 --format json
```

List all runs:
```bash
sherlock report --list
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

### `sherlock alert`

**Manage Slack alerts**

```bash
sherlock alert <COMMAND>
```

**Subcommands:**

#### `test` - Send test alert

```bash
sherlock alert test
```

Validates webhook and sends sample alert.

#### `configure` - Update Slack settings

```bash
sherlock alert configure
```

Interactive update of webhook URL, channel, bot name.

---

### `sherlock demo`

**Deterministic demo mode**

```bash
sherlock demo [OPTIONS]
```

**Options:**
- `--scenario NAME` - Demo scenario to run

Runs pre-scripted path with known failure for judge presentations.

**Example:**
```bash
sherlock demo --scenario backend_timeout
```

---

## Configuration

### Configuration Files

**Primary Config:** `./data/sherlock.json`
- Structured settings (nested objects)
- Feature flags
- Paths and defaults

**Environment Variables:** `.env`
- AWS credentials
- Bedrock model ID
- Region
- Slack webhook
- Sensitive values

### Environment Variables Reference

**Required:**
```bash
AWS_ACCESS_KEY_ID=AKIA...          # OR use AWS_PROFILE
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-5-20250929-v1:0
```

**Optional:**
```bash
AWS_PROFILE=default                 # Use AWS CLI profile
AWS_SESSION_TOKEN=...               # For temporary credentials
BEDROCK_MODEL_FALLBACK=...          # Fallback model ID
SLACK_WEBHOOK_URL=https://...       # Slack webhook
SLACK_CHANNEL=#alerts               # Override channel
SHERLOCK_MAX_STEPS=50               # Max steps per run
SHERLOCK_HARD_TIMEOUT=600           # Timeout in seconds
```

### Manual Configuration

Edit `.env` directly:
```bash
vi .env
```

Or set environment variables:
```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_REGION="us-west-2"
export BEDROCK_MODEL_ID="anthropic.claude-sonnet-4-5-20250929-v1:0"
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
sherlock personas add
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
sherlock init

# 2. Validate setup
sherlock preflight

# 3. Run test
sherlock run --goal "Complete signup"

# 4. View results
sherlock report <run-id>
```

### Advanced Workflows

**Test different personas:**
```bash
for persona in confused_first_time_user impatient_user careful_user; do
  sherlock run --persona $persona --goal "Complete signup"
done
```

**Test different devices:**
```bash
sherlock run --goal "Signup" --device "iPhone 13"
sherlock run --goal "Signup" --device "Pixel 5"
```

**Test different network conditions:**
```bash
sherlock run --goal "Signup" --network 4g
sherlock run --goal "Signup" --network 3g
sherlock run --goal "Signup" --network slow3g
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
Slack Alert: Sent to #sherlock-alerts
```

---

## Troubleshooting

### Common Issues

#### "AWS credentials not configured"

**Solution:**
```bash
# Option 1: Run init again
sherlock init

# Option 2: Set in .env
echo "AWS_ACCESS_KEY_ID=AKIA..." >> .env
echo "AWS_SECRET_ACCESS_KEY=..." >> .env

# Option 3: Use AWS CLI profile
export AWS_PROFILE=default
```

#### "BEDROCK_MODEL_ID not set"

**Solution:**
```bash
# Add to .env
echo "BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-5-20250929-v1:0" >> .env
```

#### Preflight fails: "Model access denied"

**Solution:**
1. Go to AWS Bedrock console
2. Navigate to Model access
3. Request access to Claude models
4. Wait for approval (usually instant)
5. Run `sherlock preflight` again

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
sherlock preflight --verbose

# 2. Check .env exists
cat .env

# 3. Check logs
tail -f ./artifacts/latest/execution.log
```

### Debug Mode

**Verbose output:**
```bash
sherlock run --goal "Test" --headed
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
sherlock init --config /custom/path/sherlock.json
sherlock run --config /custom/path/sherlock.json --goal "Test"
```

### Override Guardrails

```bash
sherlock run \
  --goal "Complex multi-step flow" \
  --max-steps 100
```

### Headed Mode for Debugging

Watch the browser in real-time:
```bash
sherlock run --goal "Debug signup" --headed
```

### JSON Reports for CI/CD

```bash
sherlock run --goal "Nightly test" > /dev/null
sherlock report <run-id> --format json > report.json

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
sherlock alert test
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
sherlock init
# When asked for allowed domains:
example.com,staging.example.com
```

This prevents autonomous actions on unintended sites.

### Regular Validation

```bash
# Run preflight before important test runs
sherlock preflight
```

---

## File Structure

```
sherlock/
├── .env                          # Environment variables (gitignored)
├── data/
│   ├── sherlock.json            # Main configuration
│   └── sherlock.db              # Run history
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
└── SHERLOCK_CLI_GUIDE.md        # This file
```

---

## Support

### Check Documentation

- `sherlock --help` - Command overview
- `sherlock <command> --help` - Command-specific help
- This guide - Complete reference

### Common Commands

```bash
# Show version
sherlock --version

# Get help
sherlock --help
sherlock run --help

# Validate setup
sherlock preflight --verbose

# List personas
sherlock personas list

# View recent runs
sherlock report --list
```

---

## Appendix

### Supported Bedrock Models

- `anthropic.claude-sonnet-4-5-20250929-v1:0` (recommended)
- `anthropic.claude-3-5-sonnet-20241022-v2:0` (fallback)
- `anthropic.claude-opus-4-6` (premium)

### Device Profiles

- iPhone 13, iPhone 14, iPhone 14 Pro
- Pixel 5, Galaxy S21
- Custom viewport sizes supported

### Network Profiles

- **4g** - Fast mobile (9 Mbps down, 1.6 Mbps up, 150ms RTT)
- **3g** - Standard mobile (1.6 Mbps down, 768 Kbps up, 300ms RTT)
- **slow3g** - Poor connection (400 Kbps down, 400 Kbps up, 2000ms RTT)

---

**Sherlock CLI v1.0.0**
Autonomous Mystery Shopper System
Built for hackathon demo - February 2026
