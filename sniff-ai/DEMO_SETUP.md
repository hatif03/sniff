# Sniff Demo Setup Guide

This guide helps you quickly set up Sniff for a demo or presentation.

## Prerequisites

- Python 3.11+
- A Google Cloud project with the Vertex AI API enabled (for Gemini)
- An ifm.ai API key (for k2-horizon)

## Quick Setup (5 minutes)

### Step 1: Install Sniff

```bash
pip install Sniff-0.1.0-py3-none-any.whl
playwright install
```

Or from PyPI:
```bash
pip install Sniff
playwright install
```

### Step 2: Configure Gemini and k2-horizon

Gemini (Vertex AI) auth is via Application Default Credentials, not an API key:

```bash
gcloud auth application-default login
gcloud config set project <your-project-id>
gcloud services enable aiplatform.googleapis.com
```

See `GCLOUD_SETUP.md` for the full walkthrough.

Create `.env` file:
```bash
GEMINI_PROJECT_ID=<your-project-id>
GEMINI_REGION=us-central1
IFM_API_KEY=<your-ifm-api-key>
SNIFF_ALLOWED_DOMAINS=staging.example.com,deriv.com
```

See `.env.example` for the full list of variables (model IDs, timeouts, temperature, etc.) and their defaults.

**WARNING: Never commit `.env` to git!**

### Step 3: Verify Setup

```bash
# Test Gemini/k2-horizon connectivity
Sniff preflight

# Expected output:
# ✓ Environment Variables
# ✓ Google Cloud Credentials (ADC valid)
# ✓ Network Connectivity
# ✓ Gemini Invocation
# ✓ k2-horizon Invocation
```

### Step 4: Run Demo Test

```bash
Sniff run \
  --url https://deriv.com \
  --goal "Complete signup process" \
  --persona impatient_user \
  --device "iPhone 13" \
  --network 3g \
  --headed
```

## Demo Scenarios

### Scenario 1: Impatient User (Shows Friction Detection)

```bash
Sniff run \
  --persona impatient_user \
  --goal "Complete signup with email" \
  --device "iPhone 13" \
  --network 3g
```

**Expected outcome:** Detects OAuth permission friction, generates P1 alert

### Scenario 2: Confused First-Time User

```bash
Sniff run \
  --persona confused_first_time_user \
  --goal "Create account and verify" \
  --device "iPhone 14"
```

**Expected outcome:** Shows hesitation patterns, unclear UX detection

### Scenario 3: Network Performance Testing

```bash
Sniff run \
  --persona impatient_user \
  --goal "Complete signup" \
  --network slow3g \
  --device "iPhone 13"
```

**Expected outcome:** Performance-related abandonment, timeout detection

## Viewing Results

```bash
# View latest run report
Sniff report

# View specific run with artifacts
Sniff report run_20260207_134429_45c8c7ec

# Artifacts are stored in:
# ./artifacts/<run_id>/
```

## Troubleshooting

### Google Cloud Credentials Not Found

```bash
# Check ADC is set up
gcloud auth application-default print-access-token

# If this fails, reconfigure:
gcloud auth application-default login
```

### Gemini Access Denied / Vertex AI Not Enabled

Ensure your GCP project has:
1. Billing enabled
2. The Vertex AI API enabled: `gcloud services enable aiplatform.googleapis.com`
3. `GEMINI_PROJECT_ID` in `.env` matching your active project (`gcloud config get-value project`)

### k2-horizon Errors

Check `IFM_API_KEY` is set in `.env` and valid at https://platform.ifm.ai/api-keys.

### Domain Not Allowed

Add domains to `.env`:
```bash
SNIFF_ALLOWED_DOMAINS=staging.example.com,deriv.com,your-domain.com
```

## Clean Demo Environment

For a clean demo every time:

```bash
# Remove previous run artifacts
rm -rf artifacts/*

# Remove database history
rm -f data/Sniff.db

# Run fresh test
Sniff run --goal "Your demo goal"
```

## Presentation Tips

1. **Run in headed mode** (`--headed`) so judges can see the browser
2. **Use slower network** (`--network 3g`) to show performance detection
3. **Choose impatient_user** to maximize friction detection
4. **Pre-select a known friction point** in your target site
5. **Have artifacts open** in a separate window to show evidence

## Demo Checklist

Before your demo:

- [ ] Gemini/k2-horizon configured and tested (`Sniff preflight`)
- [ ] Playwright browsers installed (`playwright install`)
- [ ] .env file configured with allowed domains
- [ ] Test run completed successfully (rehearsal)
- [ ] Artifacts directory cleaned for fresh demo
- [ ] Terminal font size increased for visibility
- [ ] Browser window size appropriate for screen sharing
- [ ] Backup demo scenario prepared (in case of network issues)

## Quick Reference Commands

```bash
# Preflight check
Sniff preflight

# Run demo
Sniff run --goal "Your goal" --persona impatient_user --headed

# View results
Sniff report

# List personas
Sniff personas list

# Test Slack alerts (if configured)
Sniff alert test
```

## Support

If you encounter issues during setup:
1. Check `Sniff preflight` output
2. Verify Google Cloud ADC: `gcloud auth application-default print-access-token`
3. Verify `IFM_API_KEY` at https://platform.ifm.ai/api-keys
4. Review logs in artifacts directory

---

Ready to demo! 🚀
