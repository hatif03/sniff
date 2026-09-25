# Sniff CLI Documentation

Welcome to the Sniff CLI documentation. Sniff is a persona-driven testing tool that simulates real user behavior to detect signup flow issues before they impact your users.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands](#commands)
- [Personas](#personas)
- [Devices](#devices)
- [Network Conditions](#network-conditions)
- [Configuration](#configuration)
- [Alert Integration](#alert-integration)
- [Examples](#examples)

## Installation

```bash
# Install Sniff CLI using pip
pip install Sniff-personas

# Or install from source
git clone https://github.com/your-org/Sniff.git
cd Sniff
pip install -e .
```

## Quick Start

Run your first Sniff test in 60 seconds:

```bash
# Basic signup flow test
Sniff run

# Test with a specific persona
Sniff run --persona confused_first_time_user

# Test on a specific device
Sniff run --device iphone13

# Test with network throttling
Sniff run --network 3g
```

## Commands

### `Sniff run`

Execute a persona-driven test run.

**Usage:**
```bash
Sniff run [options]
```

**Options:**
- `--persona <name>` - Select a user persona (default: `standard_user`)
- `--device <device>` - Specify target device (default: `desktop`)
- `--network <speed>` - Set network conditions (default: `4g`)
- `--url <url>` - Target URL to test (default: from config)
- `--headless` - Run in headless mode (default: true)
- `--debug` - Enable debug mode with verbose logging
- `--record` - Record session video and screenshots
- `--slack <webhook>` - Slack webhook URL for alerts

**Example:**
```bash
Sniff run \
  --persona power_user \
  --device iphone13 \
  --network 3g \
  --url https://app.example.com/signup
```

### `Sniff init`

Initialize a new Sniff configuration in your project.

**Usage:**
```bash
Sniff init
```

This creates a `Sniff.config.json` file with default settings.

### `Sniff list`

List available personas, devices, and network profiles.

**Usage:**
```bash
# List all available options
Sniff list

# List personas only
Sniff list --personas

# List devices only
Sniff list --devices

# List network profiles
Sniff list --networks
```

### `Sniff config`

Manage Sniff configuration.

**Usage:**
```bash
# View current configuration
Sniff config view

# Set a configuration value
Sniff config set <key> <value>

# Reset to defaults
Sniff config reset
```

## Personas

Sniff includes built-in personas that simulate different user behaviors:

### Standard User
**ID:** `standard_user`
- Familiar with web applications
- Normal reading speed
- Minimal mistakes
- Good network literacy

### Confused First-Time User
**ID:** `confused_first_time_user`
- First time using the app
- Slower interaction speed
- May click wrong buttons
- Hesitates before submitting forms
- Re-reads instructions

### Power User
**ID:** `power_user`
- Very fast interactions
- Uses keyboard shortcuts
- Minimal mouse usage
- Expects instant responses

### Mobile-First User
**ID:** `mobile_first_user`
- Primarily uses mobile devices
- Thumb-based navigation
- Expects mobile-optimized UI
- Impatient with slow loading

### Accessibility-Focused User
**ID:** `accessibility_focused`
- Uses screen readers
- Keyboard-only navigation
- Needs high contrast
- Sensitive to motion

## Devices

Test across different devices and viewports:

| Device | Viewport | User Agent |
|--------|----------|------------|
| `desktop` | 1920×1080 | Chrome Desktop |
| `laptop` | 1440×900 | Chrome Laptop |
| `iphone13` | 390×844 | iOS Safari |
| `iphone13pro` | 428×926 | iOS Safari |
| `ipad` | 768×1024 | iOS Safari |
| `pixel7` | 412×915 | Chrome Android |
| `galaxys22` | 360×800 | Chrome Android |

## Network Conditions

Simulate various network speeds:

| Profile | Download | Upload | Latency | Packet Loss |
|---------|----------|--------|---------|-------------|
| `5g` | 20 Mbps | 10 Mbps | 20ms | 0% |
| `4g` | 4 Mbps | 3 Mbps | 50ms | 0% |
| `3g` | 1.5 Mbps | 750 Kbps | 200ms | 1% |
| `2g` | 250 Kbps | 50 Kbps | 600ms | 2% |
| `slow-3g` | 400 Kbps | 400 Kbps | 400ms | 1% |
| `offline` | 0 Mbps | 0 Mbps | ∞ | 100% |

## Configuration

Create a `Sniff.config.json` in your project root:

```json
{
  "baseUrl": "https://app.example.com",
  "timeout": 30000,
  "retries": 3,
  "defaultPersona": "standard_user",
  "defaultDevice": "desktop",
  "defaultNetwork": "4g",
  "slack": {
    "webhookUrl": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    "channel": "#eng-alerts",
    "mentionOnCritical": ["@engineering"]
  },
  "alerts": {
    "enabled": true,
    "severityLevels": ["P0", "P1", "P2", "P3"],
    "minSeverity": "P2"
  },
  "recording": {
    "enabled": true,
    "videoFormat": "mp4",
    "screenshotOnFailure": true,
    "retainSuccessful": false
  },
  "diagnosis": {
    "enabled": true,
    "aiProvider": "bedrock",
    "model": "anthropic.claude-3-sonnet"
  }
}
```

## Alert Integration

### Slack Integration

Configure Slack alerts to get notified instantly when issues are detected:

```bash
Sniff run --slack https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

**Alert Format:**
```
🚨 Signup Flow Blocked [P0]

Issue: Submit button unresponsive on iPhone 13 with 3G network
Root Cause: JavaScript event listener not attached due to slow bundle load
Impact: 100% of signup attempts failing on slower connections
Device: iPhone 13
Network: 3G
Persona: confused_first_time_user

View Full Diagnosis →
```

### Custom Webhooks

Send alerts to any webhook endpoint:

```json
{
  "webhooks": [
    {
      "url": "https://api.example.com/alerts",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      },
      "severityFilter": ["P0", "P1"]
    }
  ]
}
```

## Examples

### Example 1: Basic Signup Flow Test

```bash
Sniff run \
  --url https://app.example.com/signup \
  --persona standard_user
```

### Example 2: Mobile Performance Test

```bash
Sniff run \
  --persona mobile_first_user \
  --device iphone13 \
  --network 3g \
  --record
```

### Example 3: Accessibility Audit

```bash
Sniff run \
  --persona accessibility_focused \
  --device desktop \
  --debug
```

### Example 4: Power User Flow

```bash
Sniff run \
  --persona power_user \
  --device laptop \
  --network 5g
```

### Example 5: Comprehensive Test Suite

```bash
# Test multiple personas in sequence
for persona in standard_user confused_first_time_user power_user; do
  Sniff run \
    --persona $persona \
    --device iphone13 \
    --network 3g \
    --record
done
```

### Example 6: CI/CD Integration

```yaml
# .github/workflows/Sniff.yml
name: Sniff E2E Tests

on:
  push:
    branches: [main, staging]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Sniff
        run: pip install Sniff-personas

      - name: Run Signup Tests
        run: |
          Sniff run \
            --persona confused_first_time_user \
            --device iphone13 \
            --network 3g \
            --slack ${{ secrets.SLACK_WEBHOOK }}
```

## Troubleshooting

### Common Issues

**Issue: "Command not found: Sniff"**
```bash
# Solution: Install using pip and ensure it's in your PATH
pip install Sniff-personas

# Verify installation
Sniff --version
```

**Issue: "Timeout waiting for element"**
```bash
# Solution: Increase timeout in config
Sniff config set timeout 60000
```

**Issue: "Network throttling not working"**
```bash
# Solution: Ensure you have proper permissions
# Run with sudo if needed (not recommended for production)
```

## Support

- **Documentation:** https://docs.Sniff.dev
- **GitHub Issues:** https://github.com/Sniff/cli/issues
- **Discord Community:** https://discord.gg/Sniff
- **Email:** support@Sniff.dev

## License

MIT License - see LICENSE file for details

---

Built with ❤️ by the Sniff team
