# Sniff Distribution Package

This document explains what gets included in the Sniff package and how Gemini/k2-horizon credentials are handled.

## What's in the Package Build

When you run `python -m build`, the following files are packaged:

### Included in Package ✅

```
Sniff/
├── src/
│   ├── __init__.py
│   ├── cli/                    # CLI commands
│   ├── core/                   # Orchestrator, state machine
│   ├── agent/                  # Gemini/k2-horizon agent service
│   ├── executor/               # Playwright worker
│   ├── diagnosis/              # Failure classification
│   ├── evidence/               # Report builder
│   ├── alerts/                 # Slack integration
│   ├── integrations/           # Supabase, etc.
│   └── personas/
│       ├── *.json             # Persona templates
│       └── __init__.py
├── pyproject.toml              # Package metadata
├── README.md                   # Documentation
└── .env.example                # Template (NO credentials)
```

### Excluded from Package ❌

These are in `.gitignore` and NEVER included:

```
.env                           # ❌ Contains the ifm.ai API key
data/                          # ❌ Runtime database
artifacts/                     # ❌ Test run evidence
*.log                          # ❌ Log files
__pycache__/                   # ❌ Python cache
dist/                          # ❌ Build artifacts
*.egg-info/                    # ❌ Package metadata
```

## How Gemini/k2-horizon Credentials Are Handled

### Build Time ⚙️

**NO credentials are included in the package.**

The package contains only:
- Source code
- Persona templates
- `.env.example` with placeholder values

### Installation Time 📦

When users install the package:
```bash
pip install Sniff-0.1.0-py3-none-any.whl
```

They get:
- The `Sniff` CLI command
- Python source code
- Persona templates
- **NO credentials**

### Runtime ⚡

Users must configure their own credentials:

#### Gemini (Vertex AI) - Application Default Credentials, no key in `.env`

```bash
# One-time setup
gcloud auth application-default login
gcloud config set project <your-project-id>
gcloud services enable aiplatform.googleapis.com
```

See `GCLOUD_SETUP.md` for the full walkthrough.

**Advantage:** No long-lived credential stored in plaintext; ADC is cached outside the project directory.

#### k2-horizon (ifm.ai) - API key in `.env`

```bash
cat > .env << EOF
GEMINI_PROJECT_ID=<your-project-id>
GEMINI_REGION=us-central1
IFM_API_KEY=your-ifm-api-key
SNIFF_ALLOWED_DOMAINS=staging.example.com,deriv.com
EOF

chmod 600 .env  # Secure the file
```

**Warning:** This stores the ifm.ai key in plaintext. Never commit `.env` to git!

## For Demo Distribution

### What You Provide to Demo Users

1. **Package file:**
   ```
   Sniff-0.1.0-py3-none-any.whl
   ```

2. **Setup script:**
   ```
   setup_demo.sh
   ```

3. **Documentation:**
   - `README.md`
   - `DEMO_SETUP.md`

### What Demo Users Configure

Users configure their own credentials after installation:

```bash
# Install package
pip install Sniff-0.1.0-py3-none-any.whl
playwright install

# Authenticate for Gemini (Vertex AI)
gcloud auth application-default login
gcloud config set project <your-project-id>
gcloud services enable aiplatform.googleapis.com

# Create .env with GEMINI_PROJECT_ID, GEMINI_REGION, IFM_API_KEY
```

See `GCLOUD_SETUP.md` and `DEMO_SETUP.md` for the full walkthrough.

## Security Best Practices

### ✅ DO

- Use `gcloud auth application-default login` for Gemini (no long-lived key to leak)
- Create `.env` files locally (excluded by `.gitignore`) for `IFM_API_KEY` and Gemini project/region
- Rotate the ifm.ai API key regularly
- Use least-privilege IAM roles if a service account is ever needed

### ❌ DON'T

- Include `.env` in the package
- Commit credentials (ADC file, ifm.ai key) to git
- Hardcode credentials in source code
- Share `.env` files via email/chat
- Store credentials in public repositories

## Credential Lookup Order

Sniff looks for credentials in this order:

1. **Gemini (Vertex AI):**
   - Google Cloud Application Default Credentials, resolved automatically by the client library (set up via `gcloud auth application-default login`)
   - `GEMINI_PROJECT_ID` / `GEMINI_REGION` from `.env` or environment variables select the project/region to call

2. **k2-horizon (ifm.ai):**
   - `IFM_API_KEY` from `.env` or environment variables

## Verification

After setup, verify credentials:

```bash
# Check Sniff can reach Gemini and k2-horizon
Sniff preflight

# Expected output:
# ✓ Environment Variables
# ✓ Google Cloud Credentials (ADC valid)
# ✓ Network Connectivity
# ✓ Gemini Invocation
# ✓ k2-horizon Invocation
```

## Package Distribution Checklist

Before distributing the package:

- [ ] `.env` is in `.gitignore`
- [ ] No credentials in any source files
- [ ] `.env.example` has only placeholder values
- [ ] `README.md` includes credential setup instructions
- [ ] `DEMO_SETUP.md` provided for demo users
- [ ] Package tested with fresh credentials
- [ ] Documentation mentions credential requirements

## Summary

**Key Points:**

1. **Credentials are NEVER in the package**
2. **Users configure their own credentials after installation**
3. **Gemini uses Application Default Credentials (no key in `.env`); k2-horizon uses `IFM_API_KEY`**
4. **`.env.example` provides a template**
5. **Documentation clearly explains credential setup**

This approach ensures:
- Security (no credential leakage)
- Flexibility (users choose their method)
- Compliance (no shared credentials)
- Ease of use (multiple methods, guided setup)

---

**For Questions:**
- See `DEMO_SETUP.md` for demo-specific instructions
- See `DEPLOYMENT_GUIDE.md` for packaging and distribution
- See `README.md` for general usage
