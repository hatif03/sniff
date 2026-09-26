"use client";

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  XAxis,
  YAxis,
} from 'recharts';
import {
  Activity,
  Gauge,
  GitBranch,
  LineChart as LineChartIcon,
  Users,
  type LucideIcon,
} from 'lucide-react';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  type ChartConfig,
} from '@/components/ui/chart';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  getRunTrendHistory,
  getAuditTrendHistory,
  getPersonaMetrics,
} from '@/lib/queries';

interface RunTrendRow {
  run_id: string;
  outcome: string;
  root_cause: string | null;
  persona_name: string;
  created_at: string;
}

interface AuditTrendRow {
  audit_id: string;
  url: string;
  overall_score: number | null;
  lcp: number | null;
  fcp: number | null;
  cls: number | null;
  created_at: string;
}

interface PersonaMetricRow {
  persona_name: string;
  total_runs: number;
  avg_rating: number | null;
  positive_runs: number;
  negative_runs: number;
  high_abandonment_runs: number;
  avg_duration: number | null;
  successful_runs: number;
  failed_runs: number;
}

// Same status-color convention as UserConfidenceViz.tsx / the audit detail
// page - the dataviz-skill good/warning/critical palette, scoped to charts.
const STATUS_COLOR = {
  good: 'var(--color-chart-good)',
  warning: 'var(--color-chart-warning)',
  critical: 'var(--color-chart-critical)',
} as const;

// Same 0-10 score bands as app/dashboard/audits/[auditId]/page.tsx's
// scoreBand() - duplicated rather than shared since that page is owned by a
// parallel task; the values must stay identical either way.
function scoreBand(score: number): { color: string } {
  if (score >= 7) return { color: STATUS_COLOR.good };
  if (score >= 4) return { color: STATUS_COLOR.warning };
  return { color: STATUS_COLOR.critical };
}

// Same published Core Web Vitals thresholds as that same audit detail page's
// VITAL_THRESHOLDS.lcp.
function lcpBand(lcp: number): 'good' | 'needsImprovement' | 'poor' {
  if (lcp < 2500) return 'good';
  if (lcp < 4000) return 'needsImprovement';
  return 'poor';
}

// ---------------------------------------------------------------------------
// Bucketing - ISO week (Monday-keyed) or day, whichever keeps the bucket
// count reasonable. Not a generic date-lib: two small pure functions cover
// every chart below.
// ---------------------------------------------------------------------------

type Granularity = 'day' | 'week';

function chooseGranularity(dates: Date[]): Granularity {
  if (dates.length < 2) return 'day';
  const times = dates.map((d) => d.getTime()).sort((a, b) => a - b);
  const spanDays = (times[times.length - 1] - times[0]) / 86_400_000;
  return spanDays > 21 ? 'week' : 'day';
}

/** Bucket key = the day, or the Monday of that ISO week, as YYYY-MM-DD (sorts for free). */
function bucketKeyFor(date: Date, granularity: Granularity): string {
  if (granularity === 'day') return date.toISOString().slice(0, 10);
  const dow = (date.getUTCDay() + 6) % 7; // Monday = 0
  const monday = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate() - dow));
  return monday.toISOString().slice(0, 10);
}

function formatBucketLabel(key: string, granularity: Granularity): string {
  const label = new Date(`${key}T00:00:00Z`).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  });
  return granularity === 'week' ? `Wk of ${label}` : label;
}

// ---------------------------------------------------------------------------
// Empty state - every section below renders one of these instead of a
// broken-looking chart whenever there's 0 or 1 usable data point.
// ---------------------------------------------------------------------------

function EmptyState({ icon: Icon, message }: { icon: LucideIcon; message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
      <Icon className="size-6 text-muted-foreground/40" />
      <p className="text-sm text-muted-foreground max-w-sm">{message}</p>
    </div>
  );
}

function LoadingCard() {
  return <div className="animate-pulse bg-card rounded-xl h-64 ring-1 ring-foreground/10" />;
}

// ---------------------------------------------------------------------------
// 1. Run outcome rate over time
// ---------------------------------------------------------------------------

const outcomeChartConfig = {
  success: { label: 'Success', color: STATUS_COLOR.good },
  error: { label: 'Error', color: STATUS_COLOR.warning },
  failure: { label: 'Failure', color: STATUS_COLOR.critical },
  aborted: { label: 'Aborted', color: 'var(--muted-foreground)' },
} satisfies ChartConfig;

function buildOutcomeBuckets(rows: RunTrendRow[], granularity: Granularity) {
  const map = new Map<string, { bucket: string; success: number; failure: number; error: number; aborted: number }>();
  for (const r of rows) {
    const key = bucketKeyFor(new Date(r.created_at), granularity);
    if (!map.has(key)) map.set(key, { bucket: key, success: 0, failure: 0, error: 0, aborted: 0 });
    const entry = map.get(key)!;
    if (r.outcome in entry) (entry as unknown as Record<string, number>)[r.outcome] += 1;
  }
  return Array.from(map.values()).sort((a, b) => a.bucket.localeCompare(b.bucket));
}

function RunOutcomeTrend({ rows }: { rows: RunTrendRow[] }) {
  if (rows.length < 2) {
    return (
      <EmptyState
        icon={Activity}
        message="Not enough runs yet - outcome trends appear once you have a few runs."
      />
    );
  }

  const granularity = chooseGranularity(rows.map((r) => new Date(r.created_at)));
  const data = buildOutcomeBuckets(rows, granularity);

  return (
    <ChartContainer config={outcomeChartConfig} className="h-72 w-full aspect-auto">
      <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis
          dataKey="bucket"
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => formatBucketLabel(v, granularity)}
        />
        <YAxis tickLine={false} axisLine={false} allowDecimals={false} />
        <ChartTooltip
          cursor={{ fill: 'var(--muted)' }}
          content={<ChartTooltipContent labelFormatter={(v) => formatBucketLabel(String(v), granularity)} />}
        />
        <Bar dataKey="success" stackId="outcome" fill="var(--color-success)" stroke="var(--card)" strokeWidth={2} maxBarSize={40} />
        <Bar dataKey="error" stackId="outcome" fill="var(--color-error)" stroke="var(--card)" strokeWidth={2} maxBarSize={40} />
        <Bar dataKey="aborted" stackId="outcome" fill="var(--color-aborted)" stroke="var(--card)" strokeWidth={2} maxBarSize={40} />
        <Bar
          dataKey="failure"
          stackId="outcome"
          fill="var(--color-failure)"
          stroke="var(--card)"
          strokeWidth={2}
          radius={[4, 4, 0, 0]}
          maxBarSize={40}
        />
        <ChartLegend content={<ChartLegendContent />} />
      </BarChart>
    </ChartContainer>
  );
}

// ---------------------------------------------------------------------------
// 2. Root-cause distribution over time
// ---------------------------------------------------------------------------

const ROOT_CAUSES = ['Backend', 'UX/Content', 'Performance', 'Integration'] as const;

const rootCauseChartConfig = {
  Backend: { label: 'Backend', color: 'var(--chart-1)' },
  'UX/Content': { label: 'UX/Content', color: 'var(--chart-2)' },
  Performance: { label: 'Performance', color: 'var(--chart-3)' },
  Integration: { label: 'Integration', color: 'var(--chart-4)' },
} satisfies ChartConfig;

function buildRootCauseBuckets(rows: RunTrendRow[], granularity: Granularity) {
  const map = new Map<string, { bucket: string } & Record<(typeof ROOT_CAUSES)[number], number>>();
  for (const r of rows) {
    if (!r.root_cause) continue;
    const key = bucketKeyFor(new Date(r.created_at), granularity);
    if (!map.has(key)) {
      const base = { bucket: key } as { bucket: string } & Record<(typeof ROOT_CAUSES)[number], number>;
      for (const c of ROOT_CAUSES) base[c] = 0;
      map.set(key, base);
    }
    const entry = map.get(key)!;
    if ((ROOT_CAUSES as readonly string[]).includes(r.root_cause)) {
      entry[r.root_cause as (typeof ROOT_CAUSES)[number]] += 1;
    }
  }
  return Array.from(map.values()).sort((a, b) => a.bucket.localeCompare(b.bucket));
}

function RootCauseTrend({ rows }: { rows: RunTrendRow[] }) {
  const diagnosed = rows.filter((r) => r.root_cause);
  if (diagnosed.length < 2) {
    return (
      <EmptyState
        icon={GitBranch}
        message="Not enough diagnosed failures yet - root-cause trends need at least two diagnosed runs."
      />
    );
  }

  const granularity = chooseGranularity(diagnosed.map((r) => new Date(r.created_at)));
  const data = buildRootCauseBuckets(diagnosed, granularity);

  return (
    <ChartContainer config={rootCauseChartConfig} className="h-72 w-full aspect-auto">
      <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis
          dataKey="bucket"
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => formatBucketLabel(v, granularity)}
        />
        <YAxis tickLine={false} axisLine={false} allowDecimals={false} />
        <ChartTooltip
          cursor={{ fill: 'var(--muted)' }}
          content={<ChartTooltipContent labelFormatter={(v) => formatBucketLabel(String(v), granularity)} />}
        />
        {ROOT_CAUSES.map((cause, i) => (
          <Bar
            key={cause}
            dataKey={cause}
            stackId="rootcause"
            fill={`var(--color-${cause})`}
            stroke="var(--card)"
            strokeWidth={2}
            radius={i === ROOT_CAUSES.length - 1 ? [4, 4, 0, 0] : undefined}
            maxBarSize={40}
          />
        ))}
        <ChartLegend content={<ChartLegendContent />} />
      </BarChart>
    </ChartContainer>
  );
}

// ---------------------------------------------------------------------------
// 3. Persona comparison (snapshot, not a time series)
// ---------------------------------------------------------------------------

function PersonaComparison({ personas }: { personas: PersonaMetricRow[] }) {
  if (personas.length === 0) {
    return (
      <EmptyState
        icon={Users}
        message="No persona activity yet - run a few tests to compare personas."
      />
    );
  }

  // A comparison table rather than a chart: avg_rating and run counts sit on
  // different scales, and mixing them in one chart would mean a second axis
  // (never do that - see dataviz skill). A table handles heterogeneous
  // columns for free and stays legible at any persona count.
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs text-muted-foreground uppercase tracking-wide">
          <th className="pb-2 font-medium">Persona</th>
          <th className="pb-2 font-medium text-right">Avg rating</th>
          <th className="pb-2 font-medium text-right">Successful</th>
          <th className="pb-2 font-medium text-right">Failed</th>
          <th className="pb-2 font-medium text-right">Total runs</th>
        </tr>
      </thead>
      <tbody>
        {personas.map((p) => (
          <tr key={p.persona_name} className="border-t border-border/50">
            <td className="py-2.5 font-medium text-foreground">{p.persona_name}</td>
            <td className="py-2.5 text-right tabular-nums">{p.avg_rating != null ? p.avg_rating.toFixed(1) : '—'}</td>
            <td className="py-2.5 text-right tabular-nums text-chart-good">{p.successful_runs}</td>
            <td className="py-2.5 text-right tabular-nums text-chart-critical">{p.failed_runs}</td>
            <td className="py-2.5 text-right tabular-nums text-muted-foreground">{p.total_runs}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ---------------------------------------------------------------------------
// 4 & 5. Audit score history + Core Web Vitals trend, per URL. Share the
// selected-URL state since #5 depends on #4's pick - kept as one component
// so the two Cards never disagree about which URL is showing.
// ---------------------------------------------------------------------------

const cwvChartConfig = {
  good: { label: 'Good (<2.5s)', color: STATUS_COLOR.good },
  needsImprovement: { label: 'Needs improvement (<4s)', color: STATUS_COLOR.warning },
  poor: { label: 'Poor (>=4s)', color: STATUS_COLOR.critical },
} satisfies ChartConfig;

function buildCwvBuckets(points: AuditTrendRow[], granularity: Granularity) {
  const map = new Map<string, { bucket: string; good: number; needsImprovement: number; poor: number }>();
  for (const p of points) {
    if (p.lcp == null) continue;
    const key = bucketKeyFor(new Date(p.created_at), granularity);
    if (!map.has(key)) map.set(key, { bucket: key, good: 0, needsImprovement: 0, poor: 0 });
    map.get(key)![lcpBand(p.lcp)] += 1;
  }
  return Array.from(map.values()).sort((a, b) => a.bucket.localeCompare(b.bucket));
}

function AuditTrendSections({ audits }: { audits: AuditTrendRow[] }) {
  const router = useRouter();
  const [manualUrl, setManualUrl] = useState<string | null>(null);

  const grouped = useMemo(() => {
    const map = new Map<string, AuditTrendRow[]>();
    for (const a of audits) {
      if (!a.url) continue;
      if (!map.has(a.url)) map.set(a.url, []);
      map.get(a.url)!.push(a);
    }
    return map;
  }, [audits]);

  const qualifyingUrls = useMemo(
    () => Array.from(grouped.entries()).filter(([, list]) => list.length >= 2).map(([url]) => url),
    [grouped]
  );

  const selectedUrl = manualUrl && qualifyingUrls.includes(manualUrl) ? manualUrl : (qualifyingUrls[0] ?? null);

  const scoreEmpty = (
    <EmptyState
      icon={LineChartIcon}
      message={
        audits.length === 0
          ? 'No audits yet - run your first audit to start tracking score history.'
          : 'No URL has been audited more than once yet - audit the same URL again to see its score trend.'
      }
    />
  );

  const scorePoints = useMemo(() => {
    if (!selectedUrl) return [];
    return (grouped.get(selectedUrl) ?? [])
      .slice()
      .sort((a, b) => a.created_at.localeCompare(b.created_at));
  }, [grouped, selectedUrl]);

  const cwvPoints = useMemo(() => scorePoints.filter((p) => p.lcp != null), [scorePoints]);

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Audit score history</CardTitle>
          <CardDescription>Overall score over time, per URL - click a point to open that audit.</CardDescription>
        </CardHeader>
        <CardContent>
          {qualifyingUrls.length === 0 ? (
            scoreEmpty
          ) : (
            <>
              {qualifyingUrls.length > 1 && (
                <Select value={selectedUrl ?? undefined} onValueChange={setManualUrl}>
                  <SelectTrigger className="w-full sm:w-96 mb-4">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {qualifyingUrls.map((u) => (
                      <SelectItem key={u} value={u}>
                        {u}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <ChartContainer config={{ overall_score: { label: 'Score' } }} className="h-72 w-full aspect-auto">
                <LineChart data={scorePoints} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                  <CartesianGrid vertical={false} strokeDasharray="3 3" />
                  <XAxis
                    dataKey="created_at"
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => new Date(v).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                  />
                  <YAxis domain={[0, 10]} tickLine={false} axisLine={false} allowDecimals={false} />
                  <ChartTooltip
                    cursor={{ stroke: 'var(--border)' }}
                    content={
                      <ChartTooltipContent
                        labelFormatter={(v) => new Date(v as string).toLocaleString()}
                        formatter={(value) => (
                          <span className="font-mono font-medium tabular-nums">{String(value)}/10</span>
                        )}
                      />
                    }
                  />
                  <Line
                    type="monotone"
                    dataKey="overall_score"
                    stroke="var(--chart-1)"
                    strokeWidth={2}
                    dot={(props: { cx?: number; cy?: number; payload?: AuditTrendRow; index?: number }) => {
                      const { cx, cy, payload, index } = props;
                      const score = payload?.overall_score ?? 0;
                      const band = scoreBand(score);
                      return (
                        <circle
                          key={`dot-${index}`}
                          cx={cx}
                          cy={cy}
                          r={5}
                          fill={band.color}
                          stroke="var(--card)"
                          strokeWidth={2}
                          style={{ cursor: 'pointer' }}
                          onClick={() => payload && router.push(`/dashboard/audits/${payload.audit_id}`)}
                        />
                      );
                    }}
                  />
                </LineChart>
              </ChartContainer>
              <p className="text-xs text-muted-foreground mt-2">Click a point to open its audit report.</p>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Core Web Vitals trend</CardTitle>
          <CardDescription>
            {selectedUrl ? `LCP distribution for ${selectedUrl}` : 'Largest Contentful Paint distribution, per URL'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {qualifyingUrls.length === 0 ? (
            scoreEmpty
          ) : cwvPoints.length < 2 ? (
            <EmptyState
              icon={Gauge}
              message="Not enough Core Web Vitals data for this URL yet - LCP wasn't captured on early audits, or only one audit has it so far."
            />
          ) : (
            (() => {
              const granularity = chooseGranularity(cwvPoints.map((p) => new Date(p.created_at)));
              const data = buildCwvBuckets(cwvPoints, granularity);
              return (
                <ChartContainer config={cwvChartConfig} className="h-72 w-full aspect-auto">
                  <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                    <CartesianGrid vertical={false} strokeDasharray="3 3" />
                    <XAxis
                      dataKey="bucket"
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) => formatBucketLabel(v, granularity)}
                    />
                    <YAxis tickLine={false} axisLine={false} allowDecimals={false} />
                    <ChartTooltip
                      cursor={{ fill: 'var(--muted)' }}
                      content={<ChartTooltipContent labelFormatter={(v) => formatBucketLabel(String(v), granularity)} />}
                    />
                    <Bar dataKey="good" stackId="cwv" fill="var(--color-good)" stroke="var(--card)" strokeWidth={2} maxBarSize={40} />
                    <Bar
                      dataKey="needsImprovement"
                      stackId="cwv"
                      fill="var(--color-needsImprovement)"
                      stroke="var(--card)"
                      strokeWidth={2}
                      maxBarSize={40}
                    />
                    <Bar
                      dataKey="poor"
                      stackId="cwv"
                      fill="var(--color-poor)"
                      stroke="var(--card)"
                      strokeWidth={2}
                      radius={[4, 4, 0, 0]}
                      maxBarSize={40}
                    />
                    <ChartLegend content={<ChartLegendContent />} />
                  </BarChart>
                </ChartContainer>
              );
            })()
          )}
        </CardContent>
      </Card>
    </>
  );
}

// ---------------------------------------------------------------------------
// Panel
// ---------------------------------------------------------------------------

export default function TrendsPanel() {
  const [runs, setRuns] = useState<RunTrendRow[]>([]);
  const [audits, setAudits] = useState<AuditTrendRow[]>([]);
  const [personas, setPersonas] = useState<PersonaMetricRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [runRows, auditRows, personaRows] = await Promise.all([
          getRunTrendHistory(),
          getAuditTrendHistory(),
          getPersonaMetrics(),
        ]);
        setRuns((runRows ?? []) as RunTrendRow[]);
        setAudits((auditRows ?? []) as AuditTrendRow[]);
        setPersonas((personaRows ?? []) as PersonaMetricRow[]);
      } catch (err) {
        console.error('Error fetching trend data:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[1, 2, 3, 4].map((i) => (
          <LoadingCard key={i} />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Run outcome rate over time</CardTitle>
          <CardDescription>Success, failure, error, and abort counts per {runs.length >= 2 ? 'period' : 'run'}.</CardDescription>
        </CardHeader>
        <CardContent>
          <RunOutcomeTrend rows={runs} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Root-cause distribution over time</CardTitle>
          <CardDescription>What&apos;s behind failed runs, bucketed the same way as outcomes.</CardDescription>
        </CardHeader>
        <CardContent>
          <RootCauseTrend rows={runs} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Persona comparison</CardTitle>
          <CardDescription>A snapshot, not a trend - current totals per persona.</CardDescription>
        </CardHeader>
        <CardContent>
          <PersonaComparison personas={personas} />
        </CardContent>
      </Card>

      <AuditTrendSections audits={audits} />
    </div>
  );
}
