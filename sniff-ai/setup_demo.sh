#!/bin/bash
# Sherlock Demo Setup Script
# This script helps configure Sherlock for demos without storing credentials in the package

set -e

echo "╔════════════════════════════════════════╗"
echo "║  Sherlock Demo Environment Setup      ║"
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

# Check if sherlock is installed
echo "🔍 Checking Sherlock installation..."
if command -v sherlock &> /dev/null; then
    echo "✓ Sherlock is installed"
else
    echo "⚠️  Sherlock not found in PATH"
    echo "   Install with: pip install sherlock"
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

# AWS Configuration
echo "╔════════════════════════════════════════╗"
echo "║  AWS Credentials Configuration        ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "Choose AWS credentials method:"
echo "1. AWS Profile (Recommended - most secure)"
echo "2. Environment variables (Session-based)"
echo "3. .env file (Persistent, local only)"
echo ""
read -p "Select option (1-3): " aws_method

case $aws_method in
    1)
        echo ""
        echo "Setting up AWS Profile..."
        read -p "Profile name [sherlock]: " profile_name
        profile_name=${profile_name:-sherlock}

        echo ""
        echo "Configuring AWS CLI profile '$profile_name'..."
        aws configure --profile "$profile_name"

        echo ""
        echo "Creating .env file with AWS profile..."
        cat > .env << EOF
# AWS Configuration (using profile)
AWS_PROFILE=$profile_name
AWS_DEFAULT_REGION=us-west-2

# Bedrock Configuration
BEDROCK_MODEL_ID=nvidia.nemotron-nano-12b-v2
BEDROCK_REGION=us-west-2

# Sherlock Configuration
SHERLOCK_ALLOWED_DOMAINS=staging.example.com,deriv.com
PLAYWRIGHT_HEADLESS=false
SHERLOCK_MAX_STEPS=50
EOF
        echo "✓ .env file created with AWS profile"
        ;;

    2)
        echo ""
        echo "Setting environment variables for this session..."
        read -p "AWS Access Key ID: " aws_key
        read -sp "AWS Secret Access Key: " aws_secret
        echo ""
        read -p "AWS Region [us-west-2]: " aws_region
        aws_region=${aws_region:-us-west-2}

        export AWS_ACCESS_KEY_ID="$aws_key"
        export AWS_SECRET_ACCESS_KEY="$aws_secret"
        export AWS_DEFAULT_REGION="$aws_region"

        echo ""
        echo "✓ Environment variables set for this session"
        echo "⚠️  These will be lost when you close the terminal"
        echo "   To persist, add them to your .bashrc or .zshrc"
        ;;

    3)
        echo ""
        echo "Creating .env file with credentials..."
        echo "⚠️  WARNING: This stores credentials in plaintext"
        echo "   Never commit this file to version control!"
        echo ""
        read -p "AWS Access Key ID: " aws_key
        read -sp "AWS Secret Access Key: " aws_secret
        echo ""
        read -p "AWS Region [us-west-2]: " aws_region
        aws_region=${aws_region:-us-west-2}

        cat > .env << EOF
# AWS Credentials (NEVER COMMIT THIS FILE!)
AWS_ACCESS_KEY_ID=$aws_key
AWS_SECRET_ACCESS_KEY=$aws_secret
AWS_DEFAULT_REGION=$aws_region

# Bedrock Configuration
BEDROCK_MODEL_ID=nvidia.nemotron-nano-12b-v2
BEDROCK_REGION=$aws_region

# Sherlock Configuration
SHERLOCK_ALLOWED_DOMAINS=staging.example.com,deriv.com
PLAYWRIGHT_HEADLESS=false
SHERLOCK_MAX_STEPS=50
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
        ;;

    *)
        echo "Invalid option. Exiting."
        exit 1
        ;;
esac

echo ""
echo "╔════════════════════════════════════════╗"
echo "║  Configuration Complete                ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Verify AWS credentials
echo "🔍 Verifying AWS credentials..."
if sherlock preflight; then
    echo ""
    echo "✅ Setup complete! AWS credentials verified."
else
    echo ""
    echo "⚠️  AWS verification failed. Please check your credentials."
    exit 1
fi

echo ""
echo "╔════════════════════════════════════════╗"
echo "║  Demo Ready!                          ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "Run your first test:"
echo "  sherlock run \\"
echo "    --url https://deriv.com \\"
echo "    --goal \"Complete signup process\" \\"
echo "    --persona impatient_user \\"
echo "    --device \"iPhone 13\" \\"
echo "    --headed"
echo ""
echo "View results:"
echo "  sherlock report"
echo ""
echo "For more examples, see DEMO_SETUP.md"
echo ""
