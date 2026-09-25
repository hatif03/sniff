# Sniff Demo Setup Guide

This guide helps you quickly set up Sniff for a demo or presentation.

## Prerequisites

- Python 3.11+
- AWS account with Bedrock access
- AWS credentials (Access Key ID and Secret Access Key)

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

### Step 2: Configure AWS Credentials

Choose one of the following methods:

#### Method A: AWS Profile (Recommended)

```bash
# Configure AWS CLI
aws configure --profile Sniff

# When prompted, enter:
# - AWS Access Key ID: [Your key]
# - AWS Secret Access Key: [Your secret]
# - Default region: us-west-2
# - Default output format: json
```

Create `.env` file:
```bash
AWS_PROFILE=Sniff
AWS_DEFAULT_REGION=us-west-2
BEDROCK_MODEL_ID=nvidia.nemotron-nano-12b-v2
BEDROCK_REGION=us-west-2
SHERLOCK_ALLOWED_DOMAINS=staging.example.com,deriv.com
```

#### Method B: Environment Variables

Set environment variables directly:
```bash
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-west-2
export BEDROCK_MODEL_ID=nvidia.nemotron-nano-12b-v2
export BEDROCK_REGION=us-west-2
export SHERLOCK_ALLOWED_DOMAINS=staging.example.com,deriv.com
```

#### Method C: .env File with Credentials

Create `.env` file in your working directory:
```bash
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-west-2
BEDROCK_MODEL_ID=nvidia.nemotron-nano-12b-v2
BEDROCK_REGION=us-west-2
SHERLOCK_ALLOWED_DOMAINS=staging.example.com,deriv.com
```

**WARNING: Never commit this file to git!**

### Step 3: Verify Setup

```bash
# Test AWS/Bedrock connectivity
Sniff preflight

# Expected output:
# ✓ AWS credentials configured
# ✓ Bedrock access verified
# ✓ Model nvidia.nemotron-nano-12b-v2 available
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

### AWS Credentials Not Found

```bash
# Check AWS configuration
aws sts get-caller-identity --profile Sniff

# If this fails, reconfigure:
aws configure --profile Sniff
```

### Bedrock Access Denied

Ensure your AWS account has:
1. Bedrock service enabled in your region
2. Model access granted (nvidia.nemotron-nano-12b-v2)
3. Appropriate IAM permissions

Check model access:
```bash
aws bedrock list-foundation-models --region us-west-2 --query 'modelSummaries[?modelId==`nvidia.nemotron-nano-12b-v2`]'
```

### Domain Not Allowed

Add domains to `.env`:
```bash
SHERLOCK_ALLOWED_DOMAINS=staging.example.com,deriv.com,your-domain.com
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

- [ ] AWS credentials configured and tested (`Sniff preflight`)
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
2. Verify AWS credentials: `aws sts get-caller-identity`
3. Check model access in Bedrock console
4. Review logs in artifacts directory

---

Ready to demo! 🚀
