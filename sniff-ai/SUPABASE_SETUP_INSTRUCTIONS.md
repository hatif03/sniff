# Supabase Project Setup for Sniff

## Quick Setup (2 minutes)

### Step 1: Create New Project (30 seconds)

1. Go to https://supabase.com/dashboard
2. Click **"New Project"**
3. Fill in the details:
   - **Name**: `Sniff-mystery-shopper`
   - **Database Password**: Generate a strong password (save it!)
   - **Region**: Choose closest to you (e.g., `us-west-1` or `ap-south-1`)
   - **Pricing Plan**: Free tier is fine
4. Click **"Create new project"**
5. Wait ~2 minutes for provisioning

### Step 2: Get Your Credentials

Once the project is created:

1. Go to **Project Settings** (⚙️ icon in sidebar)
2. Click **API** in the settings menu
3. Copy these two values:
   - **Project URL** (e.g., `https://xxxxx.supabase.co`)
   - **anon/public key** (the long JWT token)

### Step 3: Link Project to CLI

Run this command and paste your project reference ID when prompted:

```bash
cd /Users/abbasalisariya/code/hackathon/Sniff
supabase link --project-ref YOUR_PROJECT_REF
```

**Where to find Project Reference ID:**
- In your dashboard URL: `https://supabase.com/dashboard/project/{PROJECT_REF}`
- Or in Project Settings → General → Reference ID

---

## Alternative: Automated Setup with Access Token

If you prefer full automation, create a Personal Access Token:

1. Go to https://supabase.com/dashboard/account/tokens
2. Click **"Generate new token"**
3. Give it a name: "Sniff Setup"
4. Save the token securely
5. Run: `export SUPABASE_ACCESS_TOKEN=your_token_here`

Then I can create everything via the Management API.

---

## What Happens Next

Once you complete Step 1-3 above, I'll automatically:
- ✅ Execute database schema (all tables, views, functions)
- ✅ Create storage buckets (screenshots, videos, traces)
- ✅ Configure bucket policies
- ✅ Update your .env file
- ✅ Test the connection

**Ready? Complete Steps 1-3 above, then let me know!**
