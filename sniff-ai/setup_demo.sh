#!/bin/bash
# Sniff Demo Setup Script
# This script helps configure Sniff for demos without storing credentials in the package

set -e

echo "╔════════════════════════════════════════╗"
echo "║  Sniff Demo Environment Setup         ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Check Python version
echo "🔍 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo "❌ Python 3.11+ required. Found: $python_version"
    exit 1
fi
echo "✓ Python $python_version detected"
echo ""

# Check if sniff is installed
echo "🔍 Checking Sniff installation..."
if command -v sniff &> /dev/null; then
    echo "✓ Sniff is installed"
else
    echo "⚠️  Sniff not found in PATH"
    echo "   Install with: pip install sniff"
    echo "   Or: pip install -e . (from source)"
    exit 1
fi
echo ""

# Check Playwright
echo "🔍 Checking Playwright browsers..."
if playwright --version &> /dev/null; then
    echo "✓ Playwright is installed"
    read -p "Install/update Playwright browsers? (y/n): " install_browsers
    if [ "$install_browsers" = "y" ]; then
        echo "Installing Playwright browsers..."
        playwright install
        echo "✓ Browsers installed"
    fi
else
    echo "⚠️  Playwright not found"
    echo "   Install with: pip install playwright && playwright install"
fi
echo ""

# Provider Configuration (Gemini via Vertex AI + k2-horizon via ifm.ai)
echo "╔════════════════════════════════════════╗"
echo "║  Provider Configuration                ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "Gemini (Tier 3 vision-capable reasoning) uses Google Cloud Application"
echo "Default Credentials, not an API key."
echo ""

if ! command -v gcloud &> /dev/null; then
    echo "⚠️  gcloud CLI not found. Install the Google Cloud SDK first:"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

read -p "GCP project ID: " gcp_project

echo ""
echo "Logging in with Application Default Credentials (opens a browser)..."
gcloud auth application-default login
gcloud config set project "$gcp_project"

echo ""
echo "Enabling the Vertex AI API (safe to re-run if already enabled)..."
gcloud services enable aiplatform.googleapis.com --project "$gcp_project"

echo ""
echo "k2-horizon (Tier 3 text-only reasoning) uses an ifm.ai API key."
read -sp "ifm.ai API key: " ifm_key
echo ""

cat > .env << EOF
# Gemini (Vertex AI) - auth via Application Default Credentials, not a key
GEMINI_PROJECT_ID=$gcp_project
GEMINI_REGION=us-central1
GEMINI_MODEL_ID=gemini-3.5-flash-lite
GEMINI_FALLBACK_MODEL_ID=gemini-2.5-flash-lite

# k2-horizon (ifm.ai)
IFM_API_KEY=$ifm_key

# Sniff Configuration
SNIFF_ALLOWED_DOMAINS=staging.example.com,deriv.com
PLAYWRIGHT_HEADLESS=false
SNIFF_MAX_STEPS=50
EOF
chmod 600 .env
echo "✓ .env file created and secured (chmod 600)"

# Ensure .env is in .gitignore
if [ -f .gitignore ]; then
    if ! grep -q "^\.env$" .gitignore; then
        echo ".env" >> .gitignore
        echo "✓ Added .env to .gitignore"
    fi
else
    echo ".env" > .gitignore
    echo "✓ Created .gitignore with .env"
fi

echo ""
echo "╔════════════════════════════════════════╗"
echo "║  Configuration Complete                ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Verify provider setup
echo "🔍 Verifying Gemini/k2-horizon setup..."
if sniff preflight; then
    echo ""
    echo "✅ Setup complete! Providers verified."
else
    echo ""
    echo "⚠️  Verification failed. Please check your credentials."
    exit 1
fi

echo ""
echo "╔════════════════════════════════════════╗"
echo "║  Demo Ready!                          ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "Run your first test:"
echo "  sniff run \\"
echo "    --url https://deriv.com \\"
echo "    --goal \"Complete signup process\" \\"
echo "    --persona impatient_user \\"
echo "    --device \"iPhone 13\" \\"
echo "    --headed"
echo ""
echo "View results:"
echo "  sniff report"
echo ""
echo "For more examples, see DEMO_SETUP.md"
echo ""
