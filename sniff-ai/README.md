# Sniff

**Autonomous mystery shopper for mobile/web signup flow testing**

Sniff is an AI-powered testing system that simulates real user behavior to test signup flows, detect friction points, diagnose root causes, and escalate issues via Slack alerts.

---

**📊 View Test Dashboards**: Check out the [Sniff Website](https://github.com/abbasali-sariya-thg/sherlock_website) to view run history, visualize test results, and explore insights from your Sniff tests in a beautiful web interface.

---

## Features

- **AI-Driven Navigation**: Uses AWS Bedrock to make intelligent decisions during signup flows
- **Persona-Based Testing**: Test with different user profiles (impatient, confused, careful users)
- **Mobile Emulation**: Full Playwright-based mobile device simulation with network throttling
- **Automated Diagnosis**: Classifies failures by root cause (Backend, UX/Content, Performance, Integration)
- **Evidence Collection**: Screenshots, traces, and detailed observation logs for every run
- **Slack Integration**: Real-time alerts with severity classification (P0-P3)
- **Supabase Storage**: Optional cloud storage for artifacts and run history

## Requirements

- Python 3.11 or higher
- AWS account with Bedrock access
- Playwright browsers (installed automatically)

## Installation

### From PyPI

```bash
pip install Sniff
playwright install
```

### From Source

```bash
git clone <repository-url>
cd Sniff
pip install -e .
playwright install
```

### From Wheel

```bash
pip install Sniff-0.1.0-py3-none-any.whl
playwright install
```

## AWS Credentials Setup

Sniff requires AWS credentials for Bedrock access. Choose one of these methods:

### Option 1: AWS Profile (Recommended)

```bash
# Configure AWS CLI
aws configure --profile Sniff

# Enter your credentials when prompted
# Then create .env file:
echo "AWS_PROFILE=Sniff" > .env
```

### Option 2: Environment Variables

```bash
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-west-2
```

### Option 3: .env File

```bash
# Create .env file (never commit this!)
cat > .env << EOF
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-west-2
EOF
```

### Verify Setup

```bash
Sniff preflight
```

**For demo setup, use the included script:**
```bash
./setup_demo.sh
```

## Quick Start

### 1. Initialize Configuration

```bash
Sniff init
```

This interactive setup will configure:
- Primary staging URL
- Allowed domains (security allowlist)
- AWS Bedrock region/model
- Slack webhook (optional)
- Default persona and device settings

### 2. Run Your First Test

```bash
Sniff run --goal "Complete signup with document upload" \
             --persona impatient_user \
             --device "iPhone 13" \
             --network 3g
```

### 3. View Results

```bash
# View latest run report
Sniff report

# View specific run
Sniff report run_20260207_134429_45c8c7ec
```

## Configuration

### Environment Variables

Create a `.env` file in your project directory:

```bash
# AWS Credentials
AWS_PROFILE=Sniff
# Or use explicit credentials:
# AWS_ACCESS_KEY_ID=AKIA...
# AWS_SECRET_ACCESS_KEY=...

# AWS Region
AWS_DEFAULT_REGION=us-west-2

# Bedrock Configuration
BEDROCK_MODEL_ID=nvidia.nemotron-nano-12b-v2
BEDROCK_REGION=us-west-2

# Security
SHERLOCK_ALLOWED_DOMAINS=staging.example.com,test.example.com
SHERLOCK_MAX_RUN_DURATION=300

# Slack Integration (Optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Supabase Integration (Optional)
SUPABASE_ENABLED=true
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

See `.env.example` for all available configuration options.

## Usage Examples

### Basic Signup Test

```bash
Sniff run --goal "Complete account creation"
```

### Test with Specific Persona

```bash
Sniff run --persona confused_first_time_user \
             --goal "Sign up and verify email"
```

### Mobile Device Testing

```bash
Sniff run --device "iPhone 14" \
             --network 3g \
             --goal "Complete onboarding"
```

### Override Starting URL

```bash
Sniff run --url https://staging.acme.com/signup \
             --goal "Complete signup form"
```

### Run in Headed Mode (Visible Browser)

```bash
Sniff run --goal "Complete signup" --headed
```

## Personas

Sniff includes built-in personas that shape testing behavior:

- **confused_first_time_user**: Explores more, hesitates, may misinterpret copy
- **impatient_user**: Low tolerance for delays, early abandonment risk
- **careful_user**: Reads labels thoroughly, validates before submit
- **power_user**: Experienced, expects efficiency

### Create Custom Personas

```bash
Sniff personas add
```

This launches an LLM-assisted builder that helps you create personas from natural language descriptions.

### List Available Personas

```bash
Sniff personas list
```

## Commands

### `Sniff init`
Initialize configuration interactively

### `Sniff run`
Execute autonomous test run
- `--goal` (required): Test objective
- `--persona`: User behavior profile
- `--url`: Override starting URL
- `--device`: Device profile (e.g., "iPhone 13")
- `--network`: Network throttling (4g, 3g, slow3g)
- `--headless/--headed`: Browser visibility
- `--max-steps`: Override step limit

### `Sniff report [run_id]`
Display test run results and artifacts

### `Sniff personas`
Manage user personas
- `add`: Create new persona
- `list`: Show all personas
- `show <name>`: Display persona details

### `Sniff alert test`
Validate Slack webhook configuration

### `Sniff demo`
Run deterministic demo mode with known failure paths

### `Sniff preflight`
Validate AWS/Bedrock setup

## Architecture

Sniff uses a modular monolith architecture:

```
CLI → Run Orchestrator → Agent Service (Bedrock)
                       → Execution Worker (Playwright)
                       → Diagnosis Engine
                       → Alert Service (Slack)
```

**Key Principles:**
- Agent Service returns decisions only (no direct browser control)
- Run Orchestrator maintains state machine authority
- Execution Worker owns Playwright session lifecycle
- Guardrails prevent infinite loops (max steps, retries, timeouts)

## Artifacts

Each run generates:
- **Screenshots**: Step-by-step visual evidence
- **Trace files**: Full Playwright execution trace
- **Observations**: Browser state at each step
- **Agent reasoning**: Decision-making timeline
- **Persona review**: User experience narrative
- **Report**: Run summary with metrics

Artifacts are stored in `artifacts/<run_id>/`

## Diagnosis & Severity

Sniff classifies failures by:

**Root Cause:**
- Backend (server errors, API failures)
- UX/Content (confusing copy, unclear labels)
- Performance (timeouts, slow responses)
- Integration (third-party failures)

**Severity:**
- **P0**: Blocking signup completion
- **P1**: Major friction, likely abandonment
- **P2**: Noticeable issue, workaround exists
- **P3**: Minor UX annoyance

## Slack Alerts

When enabled, Sniff posts rich alerts with:
- Severity indicator
- Root cause classification
- Evidence links
- Reproduction steps
- Owner tags for routing

## Security

- **Domain Allowlist**: Prevents accidental production testing
- **PII Redaction**: Sanitizes logs
- **Action Whitelist**: Limits risky autonomous actions
- **Timeout Guardrails**: Hard limits on run duration

## Development

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest tests/
```

### Build Package

```bash
python -m build
```

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

[Specify your license here - e.g., MIT, Apache 2.0]

## Support

- GitHub Issues: [repository-url]/issues
- Documentation: [docs-url]

## Roadmap

- Real device testing (Appium/BrowserStack)
- Multi-locale support
- CI/CD integration
- Multi-agent orchestration
- Hosted dashboard for team triage

---

Built with AWS Bedrock, Playwright, and Python.
