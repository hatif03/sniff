"use client";

import { useEffect, useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { Bar, BarChart, CartesianGrid, Cell, XAxis, YAxis } from 'recharts';
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from '@/components/ui/chart';
import { AnimatedNumber } from '@/components/AnimatedNumber';
import { getActions } from '@/lib/queries';

interface Action {
  step: number;
  action: string;
  target: string;
  success: boolean;
  duration_ms: number;
}

interface UserConfidenceData {
  step: number;
  confidence: number;
  confidencePct: number;
  action: string;
  target: string;
  emoji: string;
  label: string;
  fill: string;
}

// Confidence-status colors are the dataviz-skill status palette
// (good/warning/critical), scoped to charts only - never reused as a
// generic brand accent elsewhere in the UI.
const STATUS_COLOR = {
  good: 'var(--color-chart-good)',
  warning: 'var(--color-chart-warning)',
  critical: 'var(--color-chart-critical)',
} as const;

// Calculate user confidence based on action success and duration
function calculateUserConfidence(action: Action): number {
  // Base confidence starts at 0.8 for successful actions, 0.2 for failures
  let confidence = action.success ? 0.8 : 0.2;

  // Penalize for long durations (user hesitation/confusion)
  // Typical action: 3-8 seconds
  // Hesitation: 10-20 seconds
  // Very confused: 20+ seconds
  if (action.duration_ms > 20000) {
    confidence -= 0.3; // Very slow = very confused
  } else if (action.duration_ms > 12000) {
    confidence -= 0.2; // Slow = somewhat confused
  } else if (action.duration_ms > 8000) {
    confidence -= 0.1; // Slightly slow = slight hesitation
  }

  // Ensure confidence stays between 0.1 and 1.0
  return Math.max(0.1, Math.min(1.0, confidence));
}

function getConfidenceStatus(confidence: number): {
  emoji: string;
  label: string;
  fill: string;
  textClass: string;
} {
  if (confidence >= 0.7) {
    return { emoji: '😊', label: 'Confident', fill: STATUS_COLOR.good, textClass: 'text-chart-good' };
  } else if (confidence >= 0.5) {
    return { emoji: '😐', label: 'Uncertain', fill: STATUS_COLOR.warning, textClass: 'text-chart-warning' };
  } else if (confidence >= 0.3) {
    return { emoji: '😕', label: 'Confused', fill: STATUS_COLOR.warning, textClass: 'text-chart-warning' };
  } else {
    return { emoji: '😣', label: 'Frustrated', fill: STATUS_COLOR.critical, textClass: 'text-chart-critical' };
  }
}

const chartConfig = {
  confidencePct: { label: 'Confidence' },
} satisfies ChartConfig;

export default function UserConfidenceViz({ runId }: { runId: string }) {
  const [confidenceData, setConfidenceData] = useState<UserConfidenceData[]>([]);
  const ref = useRef(null);
  useInView(ref, { once: true, margin: "-100px" });

  useEffect(() => {
    async function fetchAndCalculate() {
      const actions = await getActions(runId);

      const data: UserConfidenceData[] = actions.map((action) => {
        const confidence = calculateUserConfidence(action);
        const status = getConfidenceStatus(confidence);

        return {
          step: action.step,
          confidence,
          confidencePct: Math.round(confidence * 100),
          action: action.action,
          target: action.target,
          emoji: status.emoji,
          label: status.label,
          fill: status.fill,
        };
      });

      setConfidenceData(data);
    }

    if (runId) {
      fetchAndCalculate();
    }
  }, [runId]);

  if (confidenceData.length === 0) return null;

  // Calculate average user confidence
  const avgConfidence = confidenceData.reduce((sum, d) => sum + d.confidence, 0) / confidenceData.length;
  const avgStatus = getConfidenceStatus(avgConfidence);

  return (
    <div ref={ref}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
      >
        <h3 className="text-2xl font-display font-bold text-foreground mb-2">
          User Confidence Over Time
        </h3>
        <p className="text-sm text-muted-foreground mb-6">
          How confident the user felt at each step, based on success rate and hesitation patterns
        </p>

        {/* Overall confidence badge */}
        <div className="mb-6">
          <div className="inline-flex items-center gap-3 bg-card rounded-xl px-4 py-3 border border-foreground/10">
            <span className="text-sm text-muted-foreground">Average User Confidence:</span>
            <span className={`text-lg font-bold ${avgStatus.textClass}`}>
              <AnimatedNumber value={avgConfidence * 100} decimals={0} suffix="%" />
            </span>
            <span className="text-xl">{avgStatus.emoji}</span>
          </div>
        </div>
      </motion.div>

      {/* Real chart: per-step confidence, colored by status */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="bg-card rounded-xl p-6 border border-foreground/10 mb-6"
      >
        <ChartContainer config={chartConfig} className="h-64 w-full aspect-auto">
          <BarChart data={confidenceData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid vertical={false} strokeDasharray="3 3" />
            <XAxis
              dataKey="step"
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `Step ${v}`}
            />
            <YAxis domain={[0, 100]} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}%`} />
            <ChartTooltip
              cursor={{ fill: 'var(--muted)' }}
              content={
                <ChartTooltipContent
                  labelFormatter={(_, payload) => `Step ${payload?.[0]?.payload?.step}`}
                  formatter={(value, _name, item) => (
                    <div className="flex w-full items-center justify-between gap-3">
                      <span className="text-muted-foreground">
                        {item.payload.emoji} {item.payload.label}
                      </span>
                      <span className="font-mono font-medium tabular-nums">{String(value)}%</span>
                    </div>
                  )}
                />
              }
            />
            <Bar dataKey="confidencePct" radius={[4, 4, 0, 0]} maxBarSize={48}>
              {confidenceData.map((d) => (
                <Cell key={d.step} fill={d.fill} />
              ))}
            </Bar>
          </BarChart>
        </ChartContainer>
      </motion.div>

      {/* Emotional journey cards */}
      <div className="space-y-4">
        {confidenceData.map((d, i) => (
          <motion.div
            key={d.step}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 + i * 0.08, ease: [0.33, 1, 0.68, 1] }}
            className="bg-card rounded-xl p-6 border border-foreground/10 hover:border-primary/30 transition-all shadow-sm hover:shadow-md"
          >
            <div className="flex justify-between items-start gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-2xl">{d.emoji}</span>
                  <p className="font-display font-semibold text-foreground">
                    {d.action} → <span className="text-primary">{d.target}</span>
                  </p>
                </div>
                <p className="text-sm text-muted-foreground">
                  User felt <span className="font-semibold">{d.label.toLowerCase()}</span> during this step
                </p>
              </div>
              <div className="flex-shrink-0">
                <span
                  className="px-3 py-1 rounded-full text-xs font-bold"
                  style={{ backgroundColor: `color-mix(in srgb, ${d.fill} 15%, transparent)`, color: d.fill }}
                >
                  {d.confidencePct}%
                </span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
