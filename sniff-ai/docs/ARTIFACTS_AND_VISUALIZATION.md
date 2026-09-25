# Sherlock Artifacts & Web Visualization

Complete guide to Sherlock's artifact system, Supabase upload, and beautiful web visualization.

## 📦 Artifacts Stored per Run

Each Sherlock test run (`artifacts/<run_id>/`) contains:

### 1. Visual Artifacts
- **Screenshots** (`step_*.png`) - Full-page screenshots at each step
- **Videos** (`videos/*.webm`) - Complete browser session recording
- **Playwright Trace** (`trace.zip`) - Interactive trace file for debugging

### 2. Structured Data (JSON)

#### `report.json` - Run Summary
```json
{
  "run_id": "run_20260207_123456_abc123",
  "outcome": "failure",
  "goal": "Complete signup with document upload",
  "persona": "confused_first_time_user",
  "start_time": "2026-02-07T12:34:56Z",
  "end_time": "2026-02-07T12:36:42Z",
  "duration_seconds": 106.3,
  "total_steps": 15,
  "successful_actions": 12,
  "failed_actions": 3,
  "starting_url": "https://staging.acme.com",
  "final_url": "https://staging.acme.com/signup/step-3"
}
```

#### `observations.json` - Browser State Timeline
```json
[
  {
    "runId": "run_20260207_123456_abc123",
    "step": 1,
    "timestamp": "2026-02-07T12:34:56.123Z",
    "url": "https://staging.acme.com/signup",
    "screenshotPath": "/path/to/step_1.png",
    "visibleText": ["Sign Up", "Create Account", "Already have an account?"],
    "timing": {"ttfb": 145, "domReady": 423},
    "consoleErrors": [],
    "networkEvents": []
  }
]
```

#### `actions.json` - Execution Results
```json
[
  {
    "action": "tap",
    "target": "Sign Up button",
    "success": true,
    "status": "success",
    "duration_ms": 234,
    "timestamp": "2026-02-07T12:34:57.345Z"
  }
]
```

#### `diagnosis.json` - Failure Analysis
```json
{
  "rootCause": "UX/Content",
  "severity": "P1",
  "likelyOwner": "Product/UX Team",
  "suggestedFix": "Add clear label to document upload button",
  "reproSteps": [
    "Navigate to signup page",
    "Fill in email and password",
    "Attempt to find document upload - unclear UI"
  ]
}
```

#### `agent_reasoning.json` ⭐ NEW - AI Decision Timeline
```json
[
  {
    "timestamp": "2026-02-07T12:34:58.123Z",
    "step": 2,
    "url": "https://staging.acme.com/signup",
    "action": "type",
    "target": "email input field",
    "reasoning": "I identified the email field by its label 'Email Address'. The persona (confused first-time user) would look for clear labels before acting.",
    "confidence": 0.87,
    "attempt": 1,
    "repaired": false,
    "is_fallback": false
  },
  {
    "timestamp": "2026-02-07T12:35:12.456Z",
    "step": 5,
    "url": "https://staging.acme.com/signup/step-2",
    "action": "scroll",
    "target": null,
    "reasoning": "The 'Continue' button is not visible in current viewport. As a confused user, I need to scroll down to find the next action.",
    "confidence": 0.65,
    "attempt": 1,
    "repaired": false,
    "is_fallback": false
  }
]
```

#### `persona_review.json` ⭐ NEW - User Experience Review
```json
{
  "persona_name": "confused_first_time_user",
  "persona_display_name": "Sarah (Confused First-Timer)",
  "overall_sentiment": "negative",
  "experience_rating": 4,
  "friction_points": [
    "Document upload button was not clearly labeled",
    "Had to scroll to find the Continue button on Step 2",
    "Password requirements were hidden until after submission"
  ],
  "positive_aspects": [
    "Email field was easy to find",
    "Error messages were clear when shown"
  ],
  "abandonment_likelihood": "high",
  "narrative": "As someone new to this platform, I found the signup process quite confusing. The document upload section wasn't clear - I saw a gray box with no label, and I hesitated for a while before clicking it. When I made a mistake with my password, the error message was helpful, but I wish those requirements were shown upfront. Overall, if this were a real signup, I probably would have given up at the document upload step.",
  "recommendations": [
    "Add a clear 'Upload Document' label to the upload button",
    "Show password requirements above the password field, not just in error messages",
    "Make Continue buttons more visible without requiring scrolling"
  ],
  "timestamp": "2026-02-07T12:36:42.789Z"
}
```

## 🚀 Uploading to Supabase

### Setup Supabase

1. **Create Supabase Project**
   ```bash
   # Go to https://supabase.com and create a new project
   ```

2. **Run Database Schema**
   ```sql
   -- Execute docs/supabase_schema.sql in Supabase SQL Editor
   -- This creates tables, views, and storage buckets
   ```

3. **Configure Sherlock**
   ```bash
   # Add to .env
   SUPABASE_ENABLED=true
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   SUPABASE_AUTO_UPLOAD=true
   ```

4. **Install Dependencies**
   ```bash
   pip install supabase Pillow
   ```

### Auto-Upload During Runs

When `SUPABASE_AUTO_UPLOAD=true`, artifacts are automatically uploaded after each test:

```bash
sherlock run --goal "Complete signup" --persona confused_user

# Output includes:
# ✓ Run completed
# ✓ Uploaded run to Supabase: https://your-project.supabase.co/runs/run_20260207_123456
```

### Manual Upload

```bash
# Upload latest run
sherlock upload

# Upload specific run
sherlock upload run_20260207_123456_abc123

# Upload all past runs
sherlock upload --all
```

## 📊 Web Dashboard Visualizations

### Architecture

```
┌─────────────────┐
│  Sherlock CLI   │ → Local test execution
│   (Python)      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│      Supabase Cloud         │
│                             │
│  PostgreSQL Database:       │
│  - runs                     │
│  - observations             │
│  - actions                  │
│  - agent_reasoning   ⭐      │
│  - persona_reviews   ⭐      │
│  - diagnoses                │
│                             │
│  Storage Buckets:           │
│  - Screenshots              │
│  - Videos                   │
│  - Traces                   │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Web Dashboard             │
│   (Next.js + React)         │
│                             │
│  Beautiful Visualizations:  │
│  - Journey Timeline Graph   │
│  - Agent Reasoning viz  ⭐   │
│  - Persona Review Cards ⭐   │
│  - Screenshot Gallery       │
│  - Friction Heatmap         │
│  - Confidence Trends        │
└─────────────────────────────┘
```

### Key Visualizations

#### 1. Journey Timeline Graph
Interactive step-by-step timeline showing:
- URL progression (graph nodes)
- Actions taken (edges with labels)
- Success/failure indicators (green/red nodes)
- Duration at each step (edge weights)
- Screenshot thumbnails on hover

**Tech**: D3.js force-directed graph or Recharts timeline

#### 2. Agent Reasoning Transparency ⭐ NEW
Shows the AI's decision-making process:
- Confidence score over time (line chart)
- Reasoning cards for each decision
- Attempt/repair indicators
- Fallback decision highlights

**Why it's powerful**:
- **Judge transparency** - Shows AI isn't a black box
- **Debug support** - Understand why agent made specific choices
- **Trust building** - See confidence scores and reasoning

#### 3. Persona Review Card ⭐ NEW
Beautiful card showing user experience from persona's perspective:
- Experience rating (1-10 with sentiment color)
- First-person narrative (italic quote)
- Friction points (red bullets)
- Positive aspects (green bullets)
- Recommendations (actionable list)
- Abandonment risk badge

**Why it's powerful**:
- **Empathy building** - Stakeholders see human impact, not just technical failures
- **Actionable insights** - Recommendations are user-centric
- **Demo value** - Makes presentations compelling

#### 4. Screenshot Gallery with Action Overlays
Carousel of screenshots with:
- Action annotations (what was clicked/typed)
- Highlighted elements
- URL and step information
- Zoom/pan controls

#### 5. Friction Heatmap Across Personas
Bar chart showing:
- Most common friction points
- Which personas encounter which issues
- Frequency counts
- Sortable/filterable

#### 6. Agent Confidence Trends
Area chart showing:
- Confidence scores over journey steps
- Low confidence moments highlighted
- Correlation with action success/failure

### Example Dashboard Pages

#### Home - Runs List
```
┌────────────────────────────────────────────────────┐
│ Recent Test Runs                                    │
├────────────────────────────────────────────────────┤
│                                                     │
│ ✗ run_20260207_123456  Failed   4/10  Sarah       │
│   Goal: Complete signup with document upload       │
│   Duration: 1m 46s  |  15 steps  |  12 successful │
│                                                     │
│ ✓ run_20260207_123400  Success  9/10  Mike        │
│   Goal: Login with existing account                │
│   Duration: 32s     |  5 steps   |  5 successful  │
│                                                     │
│ ✗ run_20260207_123300  Failed   3/10  Alex        │
│   Goal: Reset password flow                        │
│   Duration: 2m 12s  |  18 steps  |  14 successful │
└────────────────────────────────────────────────────┘
```

#### Run Details Page
```
┌────────────────────────────────────────────────────┐
│ Run: run_20260207_123456                           │
│ Status: Failed  |  Duration: 1m 46s  |  P1 Severity│
├────────────────────────────────────────────────────┤
│                                                     │
│ [Journey Timeline Graph]                           │
│  ○────>○────>○────>●────>○                         │
│  Step1  Step2 Step3 STUCK Step5                   │
│                                                     │
├────────────────────────────────────────────────────┤
│                                                     │
│ [Sarah's Review]           Experience: 4/10 😞      │
│ "As someone new to this platform, I found the     │
│  signup process quite confusing..."                │
│                                                     │
│  Friction Points:          What Worked:           │
│  • Upload button unclear   • Email field clear    │
│  • Hidden password rules   • Error messages good  │
│                                                     │
│  Abandonment Risk: HIGH                            │
│                                                     │
├────────────────────────────────────────────────────┤
│                                                     │
│ [Agent Reasoning Timeline]                         │
│  Confidence Over Time: [Line Chart 0-100%]        │
│                                                     │
│  Step 2: Type email (87% confident)               │
│  "I identified the email field by its label..."   │
│                                                     │
│  Step 5: Scroll down (65% confident)              │
│  "Continue button not visible, scrolling..."      │
│                                                     │
├────────────────────────────────────────────────────┤
│                                                     │
│ [Screenshot Gallery]                               │
│  [Screenshot 1] [Screenshot 2] [Screenshot 3]     │
│                                                     │
├────────────────────────────────────────────────────┤
│                                                     │
│ [Diagnosis]                                        │
│  Root Cause: UX/Content                           │
│  Severity: P1 (Major friction)                    │
│  Owner: Product/UX Team                           │
│  Fix: Add clear label to document upload button   │
│                                                     │
└────────────────────────────────────────────────────┘
```

#### Persona Analytics Page
```
┌────────────────────────────────────────────────────┐
│ Persona Performance Metrics                        │
├────────────────────────────────────────────────────┤
│                                                     │
│ Sarah (Confused First-Timer)                       │
│  Avg Rating: 5.2/10  |  High Abandonment: 67%     │
│  Total Runs: 12      |  Success Rate: 25%         │
│                                                     │
│ Mike (Tech-Savvy User)                             │
│  Avg Rating: 8.1/10  |  High Abandonment: 8%      │
│  Total Runs: 15      |  Success Rate: 87%         │
│                                                     │
├────────────────────────────────────────────────────┤
│                                                     │
│ [Top Friction Points Across All Personas]         │
│  Document upload unclear     ████████████ 12      │
│  Password requirements hidden ████████ 8          │
│  Continue button buried      ██████ 6             │
│                                                     │
└────────────────────────────────────────────────────┘
```

## 🎨 Implementation Guide

### Tech Stack
- **Frontend**: Next.js 14+ (App Router)
- **UI Library**: shadcn/ui + Tailwind CSS
- **Charts**: Recharts or D3.js
- **Database**: Supabase (PostgreSQL)
- **Storage**: Supabase Storage
- **Deployment**: Vercel

### Quick Start

1. **Clone Web Template** (create Next.js app)
   ```bash
   npx create-next-app@latest sherlock-web
   cd sherlock-web
   npm install @supabase/supabase-js recharts
   ```

2. **Configure Supabase Client**
   ```typescript
   // lib/supabase.ts
   import { createClient } from '@supabase/supabase-js'

   export const supabase = createClient(
     process.env.NEXT_PUBLIC_SUPABASE_URL!,
     process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
   )
   ```

3. **Fetch Run Data**
   ```typescript
   // Get run details with all related data
   const { data } = await supabase
     .rpc('get_run_details', { p_run_id: runId })
   ```

4. **Build Visualizations** (see WEB_VISUALIZATION_GUIDE.md)

## 🔥 Demo Power Features

### For Judge Presentations

1. **Live Run Streaming** - Show test executing in real-time
2. **Side-by-Side Comparison** - Compare different personas on same flow
3. **Friction Replay** - Replay exact friction point with screenshot + reasoning
4. **Shareable Links** - Generate public links to share specific run results
5. **PDF Export** - Download beautiful PDF reports

### Wow Factors

- **Agent Transparency**: Show AI isn't a black box - full reasoning visible
- **User Empathy**: Persona reviews make technical issues human
- **Beautiful Design**: Graph-based timelines, not boring tables
- **Real Value**: Actionable recommendations, not just data dumps

## 📈 Value Proposition

### For Product Teams
- See failures through user's eyes (persona reviews)
- Get actionable UX recommendations
- Track friction trends across personas

### For Engineering Teams
- Root cause diagnosis with evidence
- Screenshot galleries for debugging
- Playwright traces for deep investigation

### For Leadership
- Success/failure metrics dashboard
- Severity-based prioritization (P0-P3)
- ROI tracking (issues prevented)

## 🔐 Security & Privacy

- Row Level Security (RLS) for multi-tenant dashboards
- Signed URLs for private screenshots
- PII redaction in logs
- Domain allowlisting prevents production accidents

## 📚 Additional Resources

- Full implementation guide: `docs/WEB_VISUALIZATION_GUIDE.md`
- Database schema: `docs/supabase_schema.sql`
- Supabase setup: https://supabase.com/docs
- Next.js docs: https://nextjs.org
- shadcn/ui: https://ui.shadcn.com

## 🎯 Next Steps

1. Set up Supabase project and run schema
2. Configure `.env` with Supabase credentials
3. Run test and verify upload: `sherlock upload`
4. Build web dashboard following guide
5. Deploy to Vercel and share with team!
