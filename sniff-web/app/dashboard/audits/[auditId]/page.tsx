"use client";

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  CheckCircle2,
  MinusCircle,
  XCircle,
  MousePointerClick,
  AlertTriangle,
} from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, XAxis, YAxis } from 'recharts';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from '@/components/ui/chart';
import { Container, ContainerNarrow } from '@/components/ui/container';
import { Display2, Heading3 } from '@/components/ui/typography';
import { AnimatedNumber } from '@/components/AnimatedNumber';
import { AuditScreenshot } from '@/components/AuditScreenshot';
import type { AuditReport, AuditStatus, AuditStatusResponse, Sentiment } from '@/lib/audits';

const POLL_INTERVAL_MS = 2500;

// Same status-color convention as UserConfidenceViz.tsx - the dataviz-skill
// good/warning/critical palette, scoped to charts/score accents only.
const STATUS_COLOR = {
  good: 'var(--color-chart-good)',
  warning: 'var(--color-chart-warning)',
  critical: 'var(--color-chart-critical)',
} as const;

function scoreBand(score: number): { key: 'good' | 'warning' | 'critical'; color: string; textClass: string } {
  if (score >= 7) return { key: 'good', color: STATUS_COLOR.good, textClass: 'text-chart-good' };
  if (score >= 4) return { key: 'warning', color: STATUS_COLOR.warning, textClass: 'text-chart-warning' };
  return { key: 'critical', color: STATUS_COLOR.critical, textClass: 'text-chart-critical' };
}

const SENTIMENT_META: Record<Sentiment, { icon: typeof CheckCircle2; color: string; textClass: string }> = {
  positive: { icon: CheckCircle2, color: STATUS_COLOR.good, textClass: 'text-chart-good' },
  neutral: { icon: MinusCircle, color: STATUS_COLOR.warning, textClass: 'text-chart-warning' },
  negative: { icon: XCircle, color: STATUS_COLOR.critical, textClass: 'text-chart-critical' },
};

/** Compact horizontal 0-10 score bar, colored by band. Used on every mini score card. */
function ScoreBar({ score }: { score: number }) {
  const band = scoreBand(score);
  return (
    <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
      <div
        className="h-full rounded-full transition-all"
        style={{ width: `${Math.max(0, Math.min(100, score * 10))}%`, backgroundColor: band.color }}
      />
    </div>
  );
}

function FixCard({
  issue,
  why,
  action,
  prominent = false,
}: {
  issue: string;
  why: string;
  action: string;
  prominent?: boolean;
}) {
  return (
    <Card className={prominent ? 'ring-2 ring-primary/40' : undefined}>
      <CardContent className="space-y-2">
        <div className="flex items-center gap-2">
          {prominent && <Badge>Primary Fix</Badge>}
          <p className="font-display font-semibold text-foreground">{issue}</p>
        </div>
        <p className="text-sm text-muted-foreground">{why}</p>
        <p className="text-sm text-foreground border-l-2 border-primary/50 pl-3">{action}</p>
      </CardContent>
    </Card>
  );
}

function GrowthMiniCard({ title, score, findings }: { title: string; score: number; findings: string[] }) {
  const band = scoreBand(score);
  return (
    <Card>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="font-display font-semibold text-foreground">{title}</p>
          <span className={`text-sm font-bold font-mono ${band.textClass}`}>
            <AnimatedNumber value={score} decimals={1} suffix="/10" />
          </span>
        </div>
        <ScoreBar score={score} />
        <ul className="space-y-1.5 text-sm text-muted-foreground list-disc pl-4">
          {findings.map((f, i) => (
            <li key={i}>{f}</li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function StatTile({ label, value }: { label: string; value: number }) {
  return (
    <Card className="text-center">
      <CardContent>
        <p className="text-2xl font-display font-bold text-foreground">
          <AnimatedNumber value={value} />
        </p>
        <p className="text-xs text-muted-foreground mt-1">{label}</p>
      </CardContent>
    </Card>
  );
}

const dimensionChartConfig = { score: { label: 'Score' } } satisfies ChartConfig;

// Real published Core Web Vitals thresholds (ms for lcp/fcp, unitless for cls).
const VITAL_THRESHOLDS = {
  lcp: [2500, 4000],
  fcp: [1800, 3000],
  cls: [0.1, 0.25],
} as const;

type VitalBand = 'good' | 'warning' | 'critical';

function vitalBand(metric: keyof typeof VITAL_THRESHOLDS, value: number): VitalBand {
  const [goodMax, niMax] = VITAL_THRESHOLDS[metric];
  if (value < goodMax) return 'good';
  if (value < niMax) return 'warning';
  return 'critical';
}

const VITAL_BAND_LABEL: Record<VitalBand, string> = {
  good: 'Good',
  warning: 'Needs improvement',
  critical: 'Poor',
};

const VITAL_BAND_TEXT_CLASS: Record<VitalBand, string> = {
  good: 'text-chart-good',
  warning: 'text-chart-warning',
  critical: 'text-chart-critical',
};

function VitalBadge({ band }: { band: VitalBand }) {
  return (
    <Badge variant="outline" className={`${VITAL_BAND_TEXT_CLASS[band]} border-current`}>
      {VITAL_BAND_LABEL[band]}
    </Badge>
  );
}

function ReportView({ auditId, report }: { auditId: string; report: AuditReport }) {
  const overallBand = scoreBand(report.overall_score);

  const dimensionData = report.scores.map((s) => ({
    dimension: s.dimension,
    shortLabel: s.dimension.split(' ')[0],
    score: s.score,
    rationale: s.rationale,
    fill: scoreBand(s.score).color,
  }));

  return (
    <Container className="space-y-14">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
      >
        <Link
          href="/dashboard"
          className="text-sm text-muted-foreground hover:text-primary transition-colors mb-4 inline-block"
        >
          ← Back to Dashboard
        </Link>
        <Display2 as="h1" className="mb-2">Landing Page Audit</Display2>
        <p className="text-sm text-muted-foreground font-mono">
          Audited from the perspective of: <span className="text-foreground">{report.visitor_persona}</span>
        </p>
      </motion.div>

      {/* Score hero */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.05 }}>
        <Card>
          <CardContent className="grid grid-cols-1 md:grid-cols-[auto_1fr] gap-8 items-center">
            <div className="flex flex-col items-center gap-2">
              <div
                className="relative size-32 rounded-full flex items-center justify-center"
                style={{
                  background: `conic-gradient(${overallBand.color} ${report.overall_score * 36}deg, var(--muted) 0deg)`,
                }}
              >
                <div className="absolute inset-2 rounded-full bg-card flex items-center justify-center">
                  <span className={`text-3xl font-display font-bold ${overallBand.textClass}`}>
                    <AnimatedNumber value={report.overall_score} decimals={1} />
                  </span>
                </div>
              </div>
              <span className="text-xs text-muted-foreground">out of 10</span>
            </div>
            <div className="space-y-3">
              <Badge className="text-xs font-bold">{report.label}</Badge>
              <p className="text-xl font-display font-semibold text-foreground">{report.verdict}</p>
              <p className="text-sm text-muted-foreground">{report.verdict_summary}</p>
              <div className="rounded-lg bg-foreground/5 border border-foreground/10 px-4 py-3">
                <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground mb-1">
                  The blunt version
                </p>
                <p className="text-sm text-foreground">{report.honest_verdict}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Context */}
      <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: '-80px' }}>
        <Card>
          <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3 text-sm">
            <div><span className="text-muted-foreground">Page type: </span><span className="text-foreground">{report.context.page_type}</span></div>
            <div><span className="text-muted-foreground">Primary goal: </span><span className="text-foreground">{report.context.primary_goal}</span></div>
            <div><span className="text-muted-foreground">Likely audience: </span><span className="text-foreground">{report.context.likely_audience}</span></div>
            <div><span className="text-muted-foreground">Audience awareness: </span><span className="text-foreground">{report.context.audience_awareness}</span></div>
            <div className="sm:col-span-2"><span className="text-muted-foreground">Visitor motivation: </span><span className="text-foreground">{report.context.visitor_motivation}</span></div>
            {report.context.assumptions_to_respect.length > 0 && (
              <div className="sm:col-span-2 flex flex-wrap gap-1.5 pt-1">
                {report.context.assumptions_to_respect.map((a, i) => (
                  <Badge key={i} variant="outline">{a}</Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* 5-dimension scores */}
      <section>
        <Heading3 as="h2" className="mb-6">Scorecard</Heading3>
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true, margin: '-80px' }}
          className="bg-card rounded-xl p-6 border border-foreground/10 mb-6"
        >
          <ChartContainer config={dimensionChartConfig} className="h-64 w-full aspect-auto">
            <BarChart data={dimensionData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis dataKey="shortLabel" tickLine={false} axisLine={false} />
              <YAxis domain={[0, 10]} tickLine={false} axisLine={false} />
              <ChartTooltip
                cursor={{ fill: 'var(--muted)' }}
                content={
                  <ChartTooltipContent
                    labelFormatter={(_, payload) => payload?.[0]?.payload?.dimension}
                    formatter={(value) => (
                      <span className="font-mono font-medium tabular-nums">{String(value)}/10</span>
                    )}
                  />
                }
              />
              <Bar dataKey="score" radius={[4, 4, 0, 0]} maxBarSize={64}>
                {dimensionData.map((d) => (
                  <Cell key={d.dimension} fill={d.fill} />
                ))}
              </Bar>
            </BarChart>
          </ChartContainer>
        </motion.div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {report.scores.map((s, i) => {
            const band = scoreBand(s.score);
            return (
              <motion.div
                key={s.dimension}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-80px' }}
                transition={{ delay: i * 0.05 }}
              >
                <Card className="h-full">
                  <CardContent className="space-y-2">
                    <p className="text-sm font-display font-semibold text-foreground">{s.dimension}</p>
                    <span className={`text-lg font-bold font-mono ${band.textClass}`}>
                      <AnimatedNumber value={s.score} decimals={1} suffix="/10" />
                    </span>
                    <ScoreBar score={s.score} />
                    <p className="text-xs text-muted-foreground">{s.rationale}</p>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* Screenshots */}
      <section>
        <Heading3 as="h2" className="mb-6">Screenshots</Heading3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2 bg-surface rounded-2xl overflow-hidden border border-foreground/10 shadow-lg">
            <AuditScreenshot
              auditId={auditId}
              path={report.images.annotated}
              alt="Annotated screenshot with detected CTAs"
              className="w-full h-auto min-h-64 object-contain bg-background"
            />
            <p className="px-4 py-2 text-xs text-muted-foreground">Annotated - detected elements overlaid</p>
          </div>
          <div className="space-y-4">
            {([
              ['above_fold', 'Above the fold'],
              ['full_page', 'Full page'],
            ] as const).map(([key, label]) => (
              <Dialog key={key}>
                <DialogTrigger asChild>
                  <button className="w-full text-left bg-surface rounded-xl overflow-hidden border border-foreground/10 hover:border-primary/40 transition-colors">
                    <AuditScreenshot
                      auditId={auditId}
                      path={report.images[key]}
                      alt={label}
                      className="w-full h-32 object-cover bg-background"
                    />
                    <p className="px-3 py-2 text-xs text-muted-foreground">{label}</p>
                  </button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-3xl">
                  <DialogHeader>
                    <DialogTitle>{label}</DialogTitle>
                  </DialogHeader>
                  <AuditScreenshot
                    auditId={auditId}
                    path={report.images[key]}
                    alt={label}
                    className="w-full h-auto max-h-[75vh] object-contain bg-background rounded-lg"
                  />
                </DialogContent>
              </Dialog>
            ))}
          </div>
        </div>
      </section>

      {/* Story timeline */}
      <section>
        <Heading3 as="h2" className="mb-2">First-Time Visitor Walkthrough</Heading3>
        <p className="text-sm text-muted-foreground mb-6">Step by step, what a first-time visitor actually experienced.</p>
        <div className="space-y-4">
          {report.story.map((step, i) => {
            const meta = SENTIMENT_META[step.sentiment];
            const Icon = meta.icon;
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: '-80px' }}
                transition={{ delay: i * 0.06 }}
              >
                <Card>
                  <CardContent className="flex gap-4">
                    <div
                      className="size-9 rounded-full flex items-center justify-center shrink-0 border-2"
                      style={{ borderColor: `color-mix(in srgb, ${meta.color} 40%, transparent)`, color: meta.color }}
                    >
                      <Icon className="size-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs text-muted-foreground mb-1">{step.step}</p>
                      <p className="font-display font-semibold text-foreground">{step.title}</p>
                      <p className="text-sm text-muted-foreground mt-1">{step.text}</p>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* Browsing evidence */}
      <section>
        <Heading3 as="h2" className="mb-6">Browsing Evidence</Heading3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-6">
          <StatTile label="Interactive elements" value={report.browsing_evidence.total_interactive_elements} />
          <StatTile label="Safe CTA candidates" value={report.browsing_evidence.safe_cta_candidates} />
          <StatTile label="Actually tested" value={report.browsing_evidence.tested_count} />
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Detected primary CTA: <span className="text-foreground font-medium">&ldquo;{report.browsing_evidence.primary_label}&rdquo;</span>
        </p>
        <div className="space-y-3">
          {report.browsing_evidence.tests.map((t, i) => (
            <div key={i} className="flex items-start gap-3 bg-card rounded-lg p-4 border border-foreground/10">
              <MousePointerClick className="size-4 text-primary shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="text-foreground font-medium">{t.label} - &ldquo;{t.target_text}&rdquo;</p>
                <p className="text-muted-foreground">{t.result}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Strengths / gaps / jargon */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent>
            <p className="font-display font-semibold text-chart-good mb-3">Strengths</p>
            <ul className="space-y-2">
              {report.strengths.map((s, i) => (
                <li key={i} className="flex gap-2 text-sm text-foreground">
                  <CheckCircle2 className="size-4 text-chart-good shrink-0 mt-0.5" />
                  {s}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <p className="font-display font-semibold text-chart-critical mb-3">Decision Gaps</p>
            <ul className="space-y-2">
              {report.decision_gaps.map((s, i) => (
                <li key={i} className="flex gap-2 text-sm text-foreground">
                  <AlertTriangle className="size-4 text-chart-critical shrink-0 mt-0.5" />
                  {s}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <p className="font-display font-semibold text-chart-warning mb-3">Jargon Terms</p>
            <div className="flex flex-wrap gap-1.5">
              {report.jargon_terms.map((j, i) => (
                <Badge key={i} variant="outline">{j}</Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Fixes */}
      <section>
        <Heading3 as="h2" className="mb-6">Fixes</Heading3>
        <div className="space-y-4">
          <FixCard {...report.primary_fix} prominent />
          {report.next_fixes.map((f, i) => (
            <FixCard key={i} {...f} />
          ))}
        </div>
      </section>

      {/* Rewrites */}
      {report.rewrites.length > 0 && (
        <section>
          <Heading3 as="h2" className="mb-6">Rewrites</Heading3>
          <div className="space-y-4">
            {report.rewrites.map((r, i) => (
              <Card key={i}>
                <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Original</p>
                    <p className="text-sm text-muted-foreground line-through decoration-critical/50">{r.original}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-primary mb-1">Replacement</p>
                    <p className="text-sm font-medium text-foreground bg-primary/10 rounded-md px-3 py-2">{r.replacement}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* Growth sub-report */}
      <section>
        <Heading3 as="h2" className="mb-6">Growth Report</Heading3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <GrowthMiniCard title="SEO" score={report.growth.seo.score} findings={report.growth.seo.findings} />
          <GrowthMiniCard title="Visual Design" score={report.growth.visual_design.score} findings={report.growth.visual_design.findings} />
          <GrowthMiniCard title="Navigation" score={report.growth.navigation.score} findings={report.growth.navigation.findings} />
        </div>
        {report.growth.strategic_options.length > 0 && (
          <>
            <Heading3 className="mb-4">Where to go from here</Heading3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {report.growth.strategic_options.map((o, i) => (
                <Card key={i}>
                  <CardContent className="space-y-2">
                    <p className="font-display font-semibold text-foreground">{o.path}</p>
                    <p className="text-sm text-muted-foreground"><span className="text-chart-warning font-medium">Risk: </span>{o.risk}</p>
                    <p className="text-sm text-foreground border-l-2 border-primary/50 pl-3">{o.experiment}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </>
        )}
      </section>

      {/* Performance & SEO - both nullable on audits from before this data was captured */}
      {(report.core_web_vitals || report.seo_checks) && (
        <section>
          <Heading3 as="h2" className="mb-6">Performance & SEO</Heading3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {report.core_web_vitals && (
              <Card>
                <CardContent className="space-y-3">
                  <p className="font-display font-semibold text-foreground">Core Web Vitals</p>
                  <div className="space-y-2">
                    {([
                      ['lcp', 'LCP', report.core_web_vitals.lcp, (v: number) => `${(v / 1000).toFixed(1)}s`],
                      ['fcp', 'FCP', report.core_web_vitals.fcp, (v: number) => `${(v / 1000).toFixed(1)}s`],
                      ['cls', 'CLS', report.core_web_vitals.cls, (v: number) => v.toFixed(2)],
                    ] as const).map(([metric, label, value, format]) =>
                      value === null ? null : (
                        <div key={metric} className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">{label}</span>
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-foreground">{format(value)}</span>
                            <VitalBadge band={vitalBand(metric, value)} />
                          </div>
                        </div>
                      )
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
            {report.seo_checks && (
              <Card>
                <CardContent className="space-y-3">
                  <p className="font-display font-semibold text-foreground">SEO Checks</p>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="text-muted-foreground">Title: </span>
                      <span className="text-foreground">{report.seo_checks.title ?? '—'}</span>
                      {report.seo_checks.title_length !== null && (
                        <span className="text-xs text-muted-foreground"> ({report.seo_checks.title_length} chars)</span>
                      )}
                    </div>
                    <div>
                      <span className="text-muted-foreground">Meta description: </span>
                      {report.seo_checks.meta_description ? (
                        <>
                          <span className="text-foreground">{report.seo_checks.meta_description}</span>
                          {report.seo_checks.meta_description_length !== null && (
                            <span className="text-xs text-muted-foreground"> ({report.seo_checks.meta_description_length} chars)</span>
                          )}
                        </>
                      ) : (
                        <Badge variant="destructive">Missing</Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">H1 tags: </span>
                      <span className="text-foreground font-mono">{report.seo_checks.h1_count ?? '—'}</span>
                      {report.seo_checks.h1_count !== null && report.seo_checks.h1_count !== 1 && (
                        <Badge variant="destructive">
                          {report.seo_checks.h1_count === 0 ? 'Missing H1' : 'Multiple H1s'}
                        </Badge>
                      )}
                    </div>
                    {report.seo_checks.img_alt_pct !== null && (
                      <div>
                        <span className="text-muted-foreground">Image alt-text coverage: </span>
                        <span className="text-foreground font-mono">{report.seo_checks.img_alt_pct}%</span>
                        {report.seo_checks.img_alt_count !== null && (
                          <span className="text-xs text-muted-foreground"> ({report.seo_checks.img_alt_count} images)</span>
                        )}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </section>
      )}

      {/* Visual teaser - compact footer aside */}
      <section className="border-t border-foreground/10 pt-8 pb-4">
        <p className="text-xs uppercase tracking-wide text-muted-foreground mb-3">Page DNA</p>
        <div className="flex flex-wrap items-center gap-6">
          <div className="flex items-center gap-2">
            {report.visual_teaser.dominant_colors.map((c, i) => (
              <div key={i} className="flex items-center gap-1.5" title={`${c.color} - ${c.uses} uses`}>
                <span className="size-5 rounded-full border border-foreground/10" style={{ backgroundColor: c.color }} />
                <span className="text-xs text-muted-foreground font-mono">{c.uses}</span>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            {report.visual_teaser.font_families.map((f, i) => (
              <span key={i}>{f.family} <span className="font-mono">×{f.uses}</span></span>
            ))}
          </div>
        </div>
      </section>
    </Container>
  );
}

function ProgressCard({ status, error }: { status: AuditStatus; error?: string | null }) {
  return (
    <Card>
      <CardContent className="space-y-4 text-center py-8">
        <p className="font-display font-semibold text-foreground">
          {status === 'failed' ? 'Audit failed' : 'Audit in progress…'}
        </p>
        <Badge variant={status === 'failed' ? 'destructive' : 'secondary'}>{status}</Badge>
        {error && <p className="text-sm text-critical">{error}</p>}
        {status !== 'failed' && (
          <p className="text-sm text-muted-foreground">This page will update automatically once the audit completes.</p>
        )}
      </CardContent>
    </Card>
  );
}

export default function AuditReportPage({ params }: { params: Promise<{ auditId: string }> }) {
  const [auditId, setAuditId] = useState<string>('');
  const [data, setData] = useState<AuditStatusResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function poll(id: string) {
      try {
        const res = await fetch(`/api/backend/audits/${id}`);
        const json: AuditStatusResponse = await res.json();
        if (cancelled) return;
        if (!res.ok) {
          setLoadError((json as unknown as { error?: string })?.error ?? `Backend returned ${res.status}`);
          if (pollTimer.current) clearInterval(pollTimer.current);
          return;
        }
        setData(json);
        if (json.status === 'completed' || json.status === 'failed') {
          if (pollTimer.current) clearInterval(pollTimer.current);
        }
      } catch (err) {
        if (cancelled) return;
        setLoadError(err instanceof Error ? err.message : 'Could not reach the backend');
        if (pollTimer.current) clearInterval(pollTimer.current);
      }
    }

    async function init() {
      const { auditId: id } = await params;
      if (cancelled) return;
      setAuditId(id);
      await poll(id);
      pollTimer.current = setInterval(() => poll(id), POLL_INTERVAL_MS);
    }

    init();
    return () => {
      cancelled = true;
      if (pollTimer.current) clearInterval(pollTimer.current);
    };
  }, [params]);

  const showReport = data?.status === 'completed' && data.report;

  return (
    <main className="min-h-screen py-32 px-6 bg-background">
      {showReport ? (
        <ReportView auditId={auditId} report={data.report as AuditReport} />
      ) : (
        <ContainerNarrow className="space-y-6">
          <Link
            href="/dashboard"
            className="text-sm text-muted-foreground hover:text-primary transition-colors inline-block"
          >
            ← Back to Dashboard
          </Link>
          {!data && !loadError ? (
            <div className="animate-pulse bg-card rounded-xl h-40 ring-1 ring-foreground/10" />
          ) : (
            <ProgressCard status={data?.status ?? 'failed'} error={loadError ?? data?.error} />
          )}
          {data?.status === 'failed' && (
            <Button asChild>
              <Link href="/dashboard/new-run">Try another audit</Link>
            </Button>
          )}
        </ContainerNarrow>
      )}
    </main>
  );
}
