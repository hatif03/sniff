# Google Cloud Setup for Sniff

This guide explains how to configure Google Cloud Application Default Credentials (ADC) so Sniff can call Gemini via Vertex AI for demos.

## Quick Setup (2 minutes)

### Prerequisites

You need:
1. A Google Cloud project with billing enabled
2. The `gcloud` CLI installed
3. Permission to enable APIs and authenticate on that project (or a project someone on your team has already set up for you)

**Don't have a project?** Contact your GCP administrator or create one in the [Google Cloud Console](https://console.cloud.google.com/).

---

## Step-by-Step Configuration

### Step 1: Install the gcloud CLI

**macOS:**
```bash
brew install --cask google-cloud-sdk
```

**Linux:**
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

**Windows:**
Download from: https://cloud.google.com/sdk/docs/install

**Verify installation:**
```bash
gcloud --version
```

### Step 2: Authenticate with Application Default Credentials

Sniff does **not** use an API key for Gemini - it uses Application Default Credentials, resolved automatically by Google's client libraries.

```bash
gcloud auth application-default login
```

This opens a browser window. Sign in and grant access. Credentials are cached locally for the client libraries to pick up automatically - no key ever goes in `.env`.

### Step 3: Set Your Project

```bash
gcloud config set project <your-project-id>
```

**Verify:**
```bash
gcloud config get-value project
```

### Step 4: Enable the Vertex AI API

```bash
gcloud services enable aiplatform.googleapis.com
```

This can take a minute to propagate the first time.

### Step 5: Configure Sniff

Create a `.env` file in your Sniff working directory (see `.env.example` for the full list of variables):

```bash
cat > .env << EOF
# Gemini (Vertex AI) Configuration
GEMINI_PROJECT_ID=<your-project-id>
GEMINI_REGION=us-central1

# k2-horizon (ifm.ai) Configuration - text-only reasoning
IFM_API_KEY=<your-ifm-api-key>

# Sniff Configuration
SNIFF_ALLOWED_DOMAINS=staging.example.com,deriv.com
PLAYWRIGHT_HEADLESS=false
SNIFF_MAX_STEPS=50
EOF
```

`GEMINI_PROJECT_ID` and `GEMINI_REGION` are the only Gemini-related variables Sniff reads - everything else (auth) comes from the ADC step above. `GEMINI_MODEL_ID`, `GEMINI_FALLBACK_MODEL_ID`, `GEMINI_MAX_TOKENS`, `GEMINI_TEMPERATURE`, and `GEMINI_TIMEOUT_SECONDS` have sane defaults but can be overridden - see `.env.example`.

### Step 6: Test with Sniff

```bash
sniff preflight

# Expected output:
# ✓ Environment Variables
# ✓ Google Cloud Credentials (ADC valid)
# ✓ Network Connectivity
# ✓ Gemini Invocation
# ✓ k2-horizon Invocation
```

---

## Where Are Credentials Stored?

When you run `gcloud auth application-default login`, a credentials file is written to:

- **macOS/Linux:** `~/.config/gcloud/application_default_credentials.json`
- **Windows:** `%APPDATA%\gcloud\application_default_credentials.json`

**Security:** This file is stored outside your project directory and is NOT included in the Sniff package. Treat it like any other credential - never commit it to git.

---

## Getting Access to a GCP Project

### If You Have Google Cloud Console Access

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable billing on the project
4. Note the **Project ID** (not the display name) - this is what goes in `GEMINI_PROJECT_ID`

### If You're a Demo User

Ask the Sniff administrator/organizer for:
- A GCP project ID to use
- Confirmation that `aiplatform.googleapis.com` is already enabled on it
- Either an invite to run `gcloud auth application-default login` yourself, or (less ideally) a service account key they can hand you securely

---

## Troubleshooting

### "gcloud: command not found"

The gcloud CLI is not installed. Follow Step 1 above.

### "Could not automatically determine credentials"

ADC hasn't been set up yet. Run:
```bash
gcloud auth application-default login
```

### "PERMISSION_DENIED" or "Vertex AI API has not been used in project..."

The Vertex AI API isn't enabled on this project yet:
```bash
gcloud services enable aiplatform.googleapis.com
```

### "404" or model-not-found errors from Gemini

The model ID may not be available in your configured region. Try the default region:
```bash
GEMINI_REGION=us-central1
```
or fall back to the model in `GEMINI_FALLBACK_MODEL_ID` (see `.env.example`).

### Sniff can't find my project

Ensure your `.env` file has:
```bash
GEMINI_PROJECT_ID=<your-project-id>
```

And verify it matches your active gcloud config:
```bash
gcloud config get-value project
```

---

## Security Best Practices

✅ **DO:**
- Use `gcloud auth application-default login` for local/demo use (no long-lived key to leak)
- Use least-privilege IAM roles if you do need a service account
- Rotate or revoke service account keys regularly if you use one
- Delete unused credentials with `gcloud auth application-default revoke`

❌ **DON'T:**
- Commit `application_default_credentials.json` or any service account key to git
- Share credentials via email or chat
- Store credentials in plaintext files inside your project directory

---

## Quick Reference Commands

```bash
# Authenticate
gcloud auth application-default login

# Set active project
gcloud config set project <your-project-id>

# Check active project
gcloud config get-value project

# Enable Vertex AI
gcloud services enable aiplatform.googleapis.com

# Revoke ADC (log out)
gcloud auth application-default revoke
```

---

## For Sniff Demo

Once your Google Cloud setup is configured:

1. ✅ gcloud CLI installed
2. ✅ Authenticated: `gcloud auth application-default login`
3. ✅ Project set: `gcloud config set project <your-project-id>`
4. ✅ Vertex AI enabled: `gcloud services enable aiplatform.googleapis.com`
5. ✅ `.env` file created with `GEMINI_PROJECT_ID` and `IFM_API_KEY`
6. ✅ Sniff verified: `sniff preflight`

Now you're ready to run demos:
```bash
sniff run \
  --url https://deriv.com \
  --goal "Complete signup process" \
  --persona impatient_user \
  --device "iPhone 13" \
  --headed
```

---

## Need Help?

- gcloud CLI docs: https://cloud.google.com/sdk/gcloud
- Application Default Credentials: https://cloud.google.com/docs/authentication/application-default-credentials
- Vertex AI setup: See `DEMO_SETUP.md`
