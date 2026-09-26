"use client";

import { useEffect, useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { Bar, BarChart, CartesianGrid, Cell, XAxis, YAxis } from 'recharts';
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from '@/components/ui/chart';
import { AnimatedNumber } from '@/components/AnimatedNumber';
import { getAgentReasoning } from '@/lib/queries';

interface Reasoning {
  id: string;
  step: number;
  action: string;
  target: string;
  reasoning: string;
  confidence: number;
}

function statusFor(confidence: number) {
  if (confidence > 0.7) return { fill: 'var(--color-chart-good)', textClass: 'text-chart-good' };
  if (confidence > 0.4) return { fill: 'var(--color-chart-warning)', textClass: 'text-chart-warning' };
  return { fill: 'var(--color-chart-critical)', textClass: 'text-chart-critical' };
}

const chartConfig = {
  confidencePct: { label: 'Confidence' },
} satisfies ChartConfig;

export default function AgentReasoningViz({ runId }: { runId: string }) {
  const [reasoning, setReasoning] = useState<Reasoning[]>([]);
  const ref = useRef(null);
  useInView(ref, { once: true, margin: "-100px" });

  useEffect(() => {
    async function fetchReasoning() {
      const data = await getAgentReasoning(runId);
      setReasoning(data);
    }

    if (runId) {
      fetchReasoning();
    }
  }, [runId]);

  if (reasoning.length === 0) return null;

  const chartData = reasoning.map((r) => ({
    ...r,
    confidencePct: Math.round(r.confidence * 100),
    fill: statusFor(r.confidence).fill,
  }));

  const avgConfidence = reasoning.reduce((sum, r) => sum + r.confidence, 0) / reasoning.length;
  const avgStatus = statusFor(avgConfidence);

  return (
    <div ref={ref}>
      <motion.h3
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
        className="text-2xl font-display font-bold text-foreground mb-2"
      >
        Agent Decision Confidence
      </motion.h3>
      <p className="text-sm text-muted-foreground mb-4">
        How confident the AI agent was in identifying the correct UI elements and actions
      </p>
      <div className="mb-6">
        <div className="inline-flex items-center gap-3 bg-card rounded-xl px-4 py-3 border border-foreground/10">
          <span className="text-sm text-muted-foreground">Average Decision Confidence:</span>
          <span className={`text-lg font-bold ${avgStatus.textClass}`}>
            <AnimatedNumber value={avgConfidence * 100} decimals={0} suffix="%" />
          </span>
        </div>
      </div>

      {/* Real chart: per-step agent confidence, colored by status */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="bg-card rounded-xl p-6 border border-foreground/10 mb-6"
      >
        <ChartContainer config={chartConfig} className="h-64 w-full aspect-auto">
          <BarChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid vertical={false} strokeDasharray="3 3" />
            <XAxis dataKey="step" tickLine={false} axisLine={false} tickFormatter={(v) => `Step ${v}`} />
            <YAxis domain={[0, 100]} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}%`} />
            <ChartTooltip
              cursor={{ fill: 'var(--muted)' }}
              content={
                <ChartTooltipContent
                  labelFormatter={(_, payload) => `Step ${payload?.[0]?.payload?.step}`}
                  formatter={(value, _name, item) => (
                    <div className="flex w-full items-center justify-between gap-3">
                      <span className="text-muted-foreground">
                        {item.payload.action} → {item.payload.target}
                      </span>
                      <span className="font-mono font-medium tabular-nums">{String(value)}%</span>
                    </div>
                  )}
                />
              }
            />
            <Bar dataKey="confidencePct" radius={[4, 4, 0, 0]} maxBarSize={48}>
              {chartData.map((d) => (
                <Cell key={d.id} fill={d.fill} />
              ))}
            </Bar>
          </BarChart>
        </ChartContainer>
      </motion.div>

      {/* Reasoning cards */}
      <div className="space-y-4">
        {chartData.map((r, i) => (
          <motion.div
            key={r.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 + i * 0.08, ease: [0.33, 1, 0.68, 1] }}
            className="bg-card rounded-xl p-6 border border-foreground/10 hover:border-primary/30 transition-all shadow-sm hover:shadow-md"
          >
            <div className="flex justify-between items-start gap-4">
              <div className="flex-1">
                <p className="font-display font-semibold text-foreground mb-2">
                  {r.action} → <span className="text-primary">{r.target}</span>
                </p>
                <p className="text-sm text-muted-foreground leading-relaxed">{r.reasoning}</p>
              </div>
              <div className="flex-shrink-0">
                <span
                  className="px-3 py-1 rounded-full text-xs font-bold"
                  style={{ backgroundColor: `color-mix(in srgb, ${r.fill} 15%, transparent)`, color: r.fill }}
                >
                  {r.confidencePct}%
                </span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
