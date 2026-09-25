# Sniff Distribution Package

This document explains what gets included in the Sniff package and how AWS credentials are handled.

## What's in the Package Build

When you run `python -m build`, the following files are packaged:

### Included in Package ✅

```
Sniff/
├── src/
│   ├── __init__.py
│   ├── cli/                    # CLI commands
│   ├── core/                   # Orchestrator, state machine
│   ├── agent/                  # Bedrock agent service
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
.env                           # ❌ Contains AWS credentials
data/                          # ❌ Runtime database
artifacts/                     # ❌ Test run evidence
*.log                          # ❌ Log files
__pycache__/                   # ❌ Python cache
dist/                          # ❌ Build artifacts
*.egg-info/                    # ❌ Package metadata
```

## How AWS Credentials Are Handled

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
- **NO AWS credentials**

### Runtime ⚡

Users must configure their own credentials using one of these methods:

#### Method 1: AWS Profile (Recommended for Demo)

```bash
# One-time setup
aws configure --profile Sniff
# Enter: Access Key, Secret Key, Region

# Create .env
cat > .env << EOF
AWS_PROFILE=Sniff
AWS_DEFAULT_REGION=us-west-2
BEDROCK_MODEL_ID=nvidia.nemotron-nano-12b-v2
BEDROCK_REGION=us-west-2
SHERLOCK_ALLOWED_DOMAINS=staging.example.com,deriv.com
EOF
```

**Advantage:** Credentials stored securely by AWS CLI, not in plaintext

#### Method 2: Environment Variables (Session-based)

```bash
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-west-2

Sniff run --goal "Complete signup"
```

**Advantage:** No files to manage, credentials only in current session

#### Method 3: .env File (Persistent, Local)

```bash
cat > .env << EOF
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-west-2
BEDROCK_MODEL_ID=nvidia.nemotron-nano-12b-v2
BEDROCK_REGION=us-west-2
EOF

chmod 600 .env  # Secure the file
```

**Advantage:** Persistent across sessions, local to project directory

**Warning:** This stores credentials in plaintext. Never commit to git!

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

Users configure their own AWS credentials after installation:

```bash
# Install package
pip install Sniff-0.1.0-py3-none-any.whl
playwright install

# Run setup script
./setup_demo.sh

# Or configure manually
aws configure --profile Sniff
```

## Security Best Practices

### ✅ DO

- Use AWS profiles whenever possible
- Store credentials in `~/.aws/credentials` (AWS CLI)
- Create `.env` files locally (excluded by `.gitignore`)
- Use IAM roles for EC2/ECS deployments
- Rotate credentials regularly
- Use temporary credentials (STS) for CI/CD

### ❌ DON'T

- Include `.env` in the package
- Commit AWS credentials to git
- Hardcode credentials in source code
- Share `.env` files via email/chat
- Use root AWS account credentials
- Store credentials in public repositories

## Credential Lookup Order

Sniff looks for credentials in this order:

1. **Environment variables:**
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_SESSION_TOKEN` (optional)

2. **`.env` file in current directory:**
   - `AWS_PROFILE=Sniff` (then looks up profile)
   - OR `AWS_ACCESS_KEY_ID=...` (direct credentials)

3. **AWS Profile:**
   - `~/.aws/credentials`
   - Profile specified by `AWS_PROFILE` env var

4. **Default AWS credentials:**
   - `~/.aws/credentials` (default profile)
   - EC2 instance metadata (if running on EC2)
   - ECS task role (if running on ECS)

## Demo Setup Script

The `setup_demo.sh` script guides users through credential setup:

```bash
./setup_demo.sh
```

This script:
1. Checks Python version
2. Verifies Sniff installation
3. Installs Playwright browsers
4. Helps configure AWS credentials (choose method)
5. Creates `.env` file with chosen method
6. Runs `Sniff preflight` to verify
7. Provides demo commands

## Verification

After setup, verify credentials:

```bash
# Check Sniff can access AWS
Sniff preflight

# Expected output:
# ✓ AWS credentials configured
# ✓ Bedrock access verified
# ✓ Model nvidia.nemotron-nano-12b-v2 available
```

## Package Distribution Checklist

Before distributing the package:

- [ ] `.env` is in `.gitignore`
- [ ] No AWS credentials in any source files
- [ ] `.env.example` has only placeholder values
- [ ] `README.md` includes credential setup instructions
- [ ] `DEMO_SETUP.md` provided for demo users
- [ ] `setup_demo.sh` script is executable
- [ ] Package tested with fresh credentials
- [ ] Documentation mentions credential requirements

## Summary

**Key Points:**

1. **AWS credentials are NEVER in the package**
2. **Users configure their own credentials after installation**
3. **Multiple configuration methods supported**
4. **`setup_demo.sh` script simplifies demo setup**
5. **`.env.example` provides a template**
6. **Documentation clearly explains credential setup**

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
