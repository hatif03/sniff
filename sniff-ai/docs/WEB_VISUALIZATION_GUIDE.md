# Sniff Web Visualization Guide

Beautiful graph-based visualization of Sniff test runs using Supabase + React/Next.js.

## Overview

Sniff uploads test run artifacts to Supabase, which can then be visualized on a web dashboard with:
- **Timeline graphs** showing step-by-step journey progression
- **Agent reasoning transparency** with confidence scores
- **Persona review insights** with sentiment analysis
- **Friction heatmaps** across different personas
- **Screenshot galleries** with action overlays
- **Video playback** of test sessions

## Architecture

```
┌─────────────────┐
│  Sniff CLI   │
│   (Local Run)   │
└────────┬────────┘
         │ Upload artifacts
         ▼
┌─────────────────────────────┐
│      Supabase Cloud         │
│                             │
│  ┌─────────────────────┐   │
│  │  PostgreSQL DB      │   │
│  │  - runs             │   │
│  │  - observations     │   │
│  │  - actions          │   │
│  │  - agent_reasoning  │   │
│  │  - persona_reviews  │   │
│  └─────────────────────┘   │
│                             │
│  ┌─────────────────────┐   │
│  │  Storage Buckets    │   │
│  │  - screenshots      │   │
│  │  - videos           │   │
│  │  - traces           │   │
│  └─────────────────────┘   │
└────────┬────────────────────┘
         │ Query/Fetch
         ▼
┌─────────────────────────────┐
│   Web Dashboard (React)     │
│   - Timeline graphs         │
│   - Agent reasoning viz     │
│   - Persona insights        │
│   - Screenshot gallery      │
└─────────────────────────────┘
```

## Supabase Setup

### 1. Create Supabase Project

1. Go to https://supabase.com and create a new project
2. Note your project URL and anon key
3. Add to `.env`:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

### 2. Run Database Schema

Execute `docs/supabase_schema.sql` in the Supabase SQL Editor:

```sql
-- Copy contents of docs/supabase_schema.sql
-- Paste into Supabase SQL Editor
-- Run to create tables, views, and functions
```

### 3. Create Storage Buckets

In Supabase Dashboard → Storage:

1. Create bucket: `Sniff-screenshots` (public)
2. Create bucket: `Sniff-videos` (public)
3. Create bucket: `Sniff-traces` (public)

### 4. Configure Sniff

```bash
# In your Sniff .env file
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

## Upload Runs to Supabase

```bash
# Upload latest run automatically (runs after each test)
Sniff run --goal "Complete signup" --persona confused_user

# Manually upload latest run
Sniff upload

# Upload specific run
Sniff upload run_20260207_123456_abc123

# Upload all past runs
Sniff upload --all
```

## Web Dashboard Implementation

### Recommended Tech Stack

- **Frontend**: Next.js 14+ (App Router)
- **UI Library**: shadcn/ui + Tailwind CSS
- **Charts**: Recharts or D3.js
- **Database Client**: Supabase JS Client
- **Deployment**: Vercel

### Project Structure

```
Sniff-web/
├── app/
│   ├── page.tsx                    # Dashboard home (run list)
│   ├── runs/[runId]/page.tsx       # Run details page
│   ├── personas/page.tsx           # Persona analytics
│   └── insights/page.tsx           # Global insights
├── components/
│   ├── RunTimeline.tsx             # Step-by-step timeline graph
│   ├── AgentReasoningViz.tsx       # Agent thinking transparency
│   ├── PersonaReviewCard.tsx       # Persona experience review
│   ├── ScreenshotGallery.tsx       # Screenshot carousel
│   ├── FrictionHeatmap.tsx         # Friction point heatmap
│   └── ConfidenceGraph.tsx         # Agent confidence over time
├── lib/
│   ├── supabase.ts                 # Supabase client
│   └── queries.ts                  # Database queries
└── types/
    └── Sniff.ts                 # TypeScript types
```

### Key Visualizations

#### 1. Run Timeline Graph

```tsx
// components/RunTimeline.tsx
import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts'
import { supabase } from '@/lib/supabase'

export function RunTimeline({ runId }: { runId: string }) {
  const [data, setData] = useState([])

  useEffect(() => {
    async function fetchTimeline() {
      const { data: observations } = await supabase
        .from('observations')
        .select('step, url, timestamp')
        .eq('run_id', runId)
        .order('step')

      const { data: actions } = await supabase
        .from('actions')
        .select('step, action, success, duration_ms')
        .eq('run_id', runId)
        .order('step')

      // Merge observations and actions
      const timeline = observations.map((obs, i) => ({
        step: obs.step,
        url: obs.url,
        action: actions[i]?.action,
        success: actions[i]?.success,
        duration: actions[i]?.duration_ms,
      }))

      setData(timeline)
    }

    fetchTimeline()
  }, [runId])

  return (
    <div className="w-full">
      <h3 className="text-lg font-semibold mb-4">Journey Timeline</h3>
      <div className="space-y-4">
        {data.map((step, i) => (
          <div key={i} className="flex items-center gap-4">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
              step.success ? 'bg-green-500' : 'bg-red-500'
            }`}>
              {step.step}
            </div>
            <div className="flex-1">
              <p className="font-medium">{step.action}</p>
              <p className="text-sm text-gray-500">{step.url}</p>
            </div>
            <span className="text-sm text-gray-400">{step.duration}ms</span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

#### 2. Agent Reasoning Visualization

```tsx
// components/AgentReasoningViz.tsx
import { AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts'

export function AgentReasoningViz({ runId }: { runId: string }) {
  const [reasoning, setReasoning] = useState([])

  useEffect(() => {
    async function fetchReasoning() {
      const { data } = await supabase
        .from('agent_reasoning')
        .select('*')
        .eq('run_id', runId)
        .order('step')

      setReasoning(data)
    }

    fetchReasoning()
  }, [runId])

  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">Agent Confidence Over Time</h3>
      <AreaChart width={800} height={300} data={reasoning}>
        <XAxis dataKey="step" />
        <YAxis domain={[0, 1]} />
        <Tooltip
          content={({ active, payload }) => {
            if (active && payload?.[0]) {
              const data = payload[0].payload
              return (
                <div className="bg-white p-4 shadow-lg rounded">
                  <p className="font-semibold">Step {data.step}</p>
                  <p className="text-sm">Action: {data.action}</p>
                  <p className="text-sm">Confidence: {(data.confidence * 100).toFixed(0)}%</p>
                  <p className="text-sm italic mt-2">{data.reasoning}</p>
                </div>
              )
            }
            return null
          }}
        />
        <Area
          type="monotone"
          dataKey="confidence"
          stroke="#8884d8"
          fill="#8884d8"
          fillOpacity={0.3}
        />
      </AreaChart>

      {/* Reasoning cards */}
      <div className="mt-6 space-y-4">
        {reasoning.map((r) => (
          <div key={r.id} className="border p-4 rounded">
            <div className="flex justify-between items-start">
              <div>
                <p className="font-semibold">{r.action} → {r.target}</p>
                <p className="text-sm text-gray-600 mt-2">{r.reasoning}</p>
              </div>
              <div className="text-right">
                <span className={`px-2 py-1 rounded text-xs ${
                  r.confidence > 0.7 ? 'bg-green-100' :
                  r.confidence > 0.4 ? 'bg-yellow-100' :
                  'bg-red-100'
                }`}>
                  {(r.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

#### 3. Persona Review Card

```tsx
// components/PersonaReviewCard.tsx
export function PersonaReviewCard({ runId }: { runId: string }) {
  const [review, setReview] = useState(null)

  useEffect(() => {
    async function fetchReview() {
      const { data } = await supabase
        .from('persona_reviews')
        .select('*')
        .eq('run_id', runId)
        .single()

      setReview(data)
    }

    fetchReview()
  }, [runId])

  if (!review) return null

  const sentimentColor = {
    positive: 'text-green-600',
    neutral: 'text-yellow-600',
    negative: 'text-red-600',
  }[review.overall_sentiment]

  return (
    <div className="bg-gradient-to-br from-purple-50 to-blue-50 p-6 rounded-lg">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-bold">{review.persona_display_name}'s Review</h3>
        <div className="flex items-center gap-2">
          <span className={`text-2xl font-bold ${sentimentColor}`}>
            {review.experience_rating}/10
          </span>
          <span className={`text-sm ${sentimentColor}`}>
            {review.overall_sentiment}
          </span>
        </div>
      </div>

      <p className="text-gray-700 italic mb-4">"{review.narrative}"</p>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className="font-semibold text-sm mb-2">Friction Points</h4>
          <ul className="space-y-1">
            {review.friction_points.map((point, i) => (
              <li key={i} className="text-sm text-red-600">• {point}</li>
            ))}
          </ul>
        </div>

        <div>
          <h4 className="font-semibold text-sm mb-2">What Worked</h4>
          <ul className="space-y-1">
            {review.positive_aspects.map((aspect, i) => (
              <li key={i} className="text-sm text-green-600">• {aspect}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t">
        <h4 className="font-semibold text-sm mb-2">Recommendations</h4>
        <ul className="space-y-2">
          {review.recommendations.map((rec, i) => (
            <li key={i} className="text-sm">→ {rec}</li>
          ))}
        </ul>
      </div>

      <div className="mt-4">
        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
          review.abandonment_likelihood === 'high' ? 'bg-red-100 text-red-700' :
          review.abandonment_likelihood === 'medium' ? 'bg-yellow-100 text-yellow-700' :
          'bg-green-100 text-green-700'
        }`}>
          Abandonment Risk: {review.abandonment_likelihood}
        </span>
      </div>
    </div>
  )
}
```

#### 4. Screenshot Gallery with Timeline

```tsx
// components/ScreenshotGallery.tsx
import Image from 'next/image'
import { Carousel } from '@/components/ui/carousel'

export function ScreenshotGallery({ runId }: { runId: string }) {
  const [observations, setObservations] = useState([])

  useEffect(() => {
    async function fetchScreenshots() {
      const { data } = await supabase
        .from('observations')
        .select('step, screenshot_url, url')
        .eq('run_id', runId)
        .order('step')

      setObservations(data)
    }

    fetchScreenshots()
  }, [runId])

  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">Journey Screenshots</h3>
      <Carousel>
        {observations.map((obs) => (
          <div key={obs.step} className="relative">
            <Image
              src={obs.screenshot_url}
              alt={`Step ${obs.step}`}
              width={800}
              height={600}
              className="rounded-lg"
            />
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
              <p className="text-white font-semibold">Step {obs.step}</p>
              <p className="text-white/80 text-sm">{obs.url}</p>
            </div>
          </div>
        ))}
      </Carousel>
    </div>
  )
}
```

#### 5. Friction Heatmap Across Personas

```tsx
// components/FrictionHeatmap.tsx
export function FrictionHeatmap() {
  const [data, setData] = useState([])

  useEffect(() => {
    async function fetchFriction() {
      const { data } = await supabase
        .from('friction_analytics')
        .select('*')
        .order('occurrence_count', { ascending: false })
        .limit(20)

      setData(data)
    }

    fetchFriction()
  }, [])

  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">Top Friction Points</h3>
      <div className="space-y-2">
        {data.map((item) => (
          <div key={item.friction_point} className="flex items-center gap-4">
            <div className="flex-1">
              <p className="text-sm font-medium">{item.friction_point}</p>
              <p className="text-xs text-gray-500">{item.persona_name}</p>
            </div>
            <div className="w-32 bg-gray-200 rounded-full h-6">
              <div
                className="bg-red-500 h-6 rounded-full"
                style={{ width: `${(item.occurrence_count / Math.max(...data.map(d => d.occurrence_count))) * 100}%` }}
              />
            </div>
            <span className="text-sm font-semibold w-8">{item.occurrence_count}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

### Database Queries

```typescript
// lib/queries.ts
import { supabase } from './supabase'

export async function getRunDetails(runId: string) {
  const { data, error } = await supabase
    .rpc('get_run_details', { p_run_id: runId })

  return data
}

export async function getRecentRuns(limit = 10) {
  const { data, error } = await supabase
    .from('run_summaries')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(limit)

  return data
}

export async function getPersonaMetrics() {
  const { data, error } = await supabase
    .from('persona_metrics')
    .select('*')

  return data
}
```

## Deployment

### Deploy to Vercel

```bash
# In your Next.js project
vercel deploy

# Set environment variables in Vercel Dashboard
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### Custom Domain

Point your domain to the Vercel deployment for a branded experience:
- `insights.yourcompany.com`
- `Sniff.yourcompany.com`

## Advanced Features

### Real-time Updates

Use Supabase Realtime to show live test execution:

```typescript
useEffect(() => {
  const subscription = supabase
    .channel('run-updates')
    .on('postgres_changes', {
      event: 'INSERT',
      schema: 'public',
      table: 'observations',
    }, (payload) => {
      // Update UI with new observation
      console.log('New observation:', payload.new)
    })
    .subscribe()

  return () => subscription.unsubscribe()
}, [])
```

### Shared Run Links

Generate public shareable links for specific runs:

```
https://insights.yourcompany.com/share/run_20260207_123456_abc123
```

### Export Reports

Generate PDF reports from run data using react-pdf or similar.

## Example Dashboard Pages

1. **Home** - List of recent runs with status indicators
2. **Run Details** - Timeline, screenshots, reasoning, review
3. **Persona Analytics** - Metrics across all personas
4. **Friction Insights** - Heatmap and trend analysis
5. **Agent Performance** - Confidence metrics and decision quality

## Security Notes

- Use Row Level Security (RLS) if sharing dashboard publicly
- Rotate Supabase keys regularly
- Consider auth for sensitive internal dashboards
- Use signed URLs for private screenshots if needed

## Resources

- Supabase Docs: https://supabase.com/docs
- shadcn/ui: https://ui.shadcn.com
- Recharts: https://recharts.org
- Next.js: https://nextjs.org
