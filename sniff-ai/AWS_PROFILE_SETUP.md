# AWS Profile Setup for Sniff

This guide explains how to configure AWS credentials using profiles for Sniff demos.

## Quick Setup (2 minutes)

### Prerequisites

You need:
1. AWS Access Key ID (starts with `AKIA...`)
2. AWS Secret Access Key (long string)
3. AWS region where Bedrock is enabled (usually `us-west-2`)

**Don't have these?** Contact your AWS administrator or create them in AWS IAM Console.

---

## Step-by-Step Profile Configuration

### Step 1: Install AWS CLI

**macOS:**
```bash
brew install awscli
```

**Linux:**
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

**Windows:**
Download from: https://awscli.amazonaws.com/AWSCLIV2.msi

**Verify installation:**
```bash
aws --version
# Should show: aws-cli/2.x.x ...
```

### Step 2: Run AWS Configure

```bash
aws configure --profile Sniff
```

**You'll be prompted for 4 values:**

```
AWS Access Key ID [None]:
```
Enter your access key (e.g., `AKIAIOSFODNN7EXAMPLE`)

```
AWS Secret Access Key [None]:
```
Enter your secret key (e.g., `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`)

```
Default region name [None]:
```
Enter `us-west-2` (or your Bedrock-enabled region)

```
Default output format [None]:
```
Enter `json` (or press Enter for default)

### Step 3: Verify Configuration

**Test the profile:**
```bash
aws sts get-caller-identity --profile Sniff
```

**Expected output:**
```json
{
    "UserId": "AIDAI23SAMPLEUSERID",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-username"
}
```

If you see this, your profile is configured correctly! ✅

**Test Bedrock access:**
```bash
aws bedrock list-foundation-models --region us-west-2 --profile Sniff --query 'modelSummaries[0:3].[modelId,modelName]'
```

### Step 4: Configure Sniff

Create a `.env` file in your Sniff working directory:

```bash
cat > .env << EOF
# AWS Configuration
AWS_PROFILE=Sniff
AWS_DEFAULT_REGION=us-west-2

# Bedrock Configuration
BEDROCK_MODEL_ID=nvidia.nemotron-nano-12b-v2
BEDROCK_REGION=us-west-2

# Sniff Configuration
SHERLOCK_ALLOWED_DOMAINS=staging.example.com,deriv.com
PLAYWRIGHT_HEADLESS=false
SHERLOCK_MAX_STEPS=50
EOF
```

### Step 5: Test with Sniff

```bash
# Verify Sniff can access AWS
Sniff preflight

# Expected output:
# ✓ AWS credentials configured
# ✓ Bedrock access verified
# ✓ Model nvidia.nemotron-nano-12b-v2 available
```

---

## Where Are Credentials Stored?

When you run `aws configure --profile Sniff`, two files are created:

### 1. `~/.aws/credentials`
Contains your access keys (secured with 600 permissions):
```ini
[Sniff]
aws_access_key_id = AKIA...
aws_secret_access_key = wJalrXUtnFEMI/...
```

### 2. `~/.aws/config`
Contains regional settings:
```ini
[profile Sniff]
region = us-west-2
output = json
```

**Security:** These files are stored in your home directory with restricted permissions. They're NOT in your project directory and NOT in the Sniff package.

---

## Getting AWS Credentials

### If You Have AWS Console Access

1. Go to AWS Console: https://console.aws.amazon.com/
2. Navigate to **IAM** (Identity and Access Management)
3. Click **Users** → Select your user
4. Click **Security credentials** tab
5. Under **Access keys**, click **Create access key**
6. Choose **CLI** as use case
7. Copy the Access Key ID and Secret Access Key
8. **Important:** Save the secret key now - you can't view it again!

### If You're a Demo User

Ask the Sniff administrator/organizer for:
- AWS Access Key ID
- AWS Secret Access Key
- AWS Region (usually `us-west-2`)

They should provide these securely (not via email or chat).

---

## Multiple Profiles

You can have multiple AWS profiles for different projects:

```bash
# Default profile
aws configure

# Sniff profile
aws configure --profile Sniff

# Work profile
aws configure --profile work

# Personal profile
aws configure --profile personal
```

List all profiles:
```bash
cat ~/.aws/credentials
```

Switch profiles by changing `AWS_PROFILE` in `.env`:
```bash
# Use Sniff profile
AWS_PROFILE=Sniff

# Use work profile
AWS_PROFILE=work
```

---

## Troubleshooting

### "aws: command not found"

AWS CLI is not installed. Follow Step 1 above.

### "The security token included in the request is invalid"

Your access key or secret key is incorrect. Run `aws configure --profile Sniff` again.

### "Could not connect to the endpoint URL"

Check your region. Bedrock might not be available in your region. Use `us-west-2` or `us-east-1`.

### "Access Denied" when testing Bedrock

Your IAM user doesn't have Bedrock permissions. Ask your AWS administrator to add this policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:ListFoundationModels"
            ],
            "Resource": "*"
        }
    ]
}
```

### Profile exists but Sniff can't find it

Ensure your `.env` file has:
```bash
AWS_PROFILE=Sniff
```

And verify the profile name matches:
```bash
aws configure list-profiles
# Should show "Sniff"
```

---

## Security Best Practices

✅ **DO:**
- Use profiles for different projects
- Rotate access keys regularly (every 90 days)
- Use MFA (multi-factor authentication) on your AWS account
- Delete unused access keys
- Use least-privilege IAM permissions

❌ **DON'T:**
- Share access keys via email or chat
- Commit `~/.aws/credentials` to git
- Use root account credentials
- Share the same credentials across multiple users
- Store credentials in plaintext files in your project

---

## Quick Reference Commands

```bash
# Configure new profile
aws configure --profile Sniff

# List all profiles
aws configure list-profiles

# Test profile
aws sts get-caller-identity --profile Sniff

# View profile config
aws configure list --profile Sniff

# Set default profile for current session
export AWS_PROFILE=Sniff

# Use specific profile for one command
aws s3 ls --profile Sniff
```

---

## For Sniff Demo

Once your AWS profile is configured:

1. ✅ AWS CLI installed
2. ✅ Profile configured: `aws configure --profile Sniff`
3. ✅ Profile tested: `aws sts get-caller-identity --profile Sniff`
4. ✅ `.env` file created with `AWS_PROFILE=Sniff`
5. ✅ Sniff verified: `Sniff preflight`

Now you're ready to run demos:
```bash
Sniff run \
  --url https://deriv.com \
  --goal "Complete signup process" \
  --persona impatient_user \
  --device "iPhone 13" \
  --headed
```

---

## Need Help?

- AWS CLI docs: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html
- AWS profiles: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html
- Bedrock setup: See `DEMO_SETUP.md`
