"use client";

import { useEffect, useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { getObservations, getActions } from '@/lib/queries';

interface TimelineStep {
  step: number;
  url: string;
  action?: string;
  success?: boolean;
  duration?: number;
}

export default function RunTimeline({ runId }: { runId: string }) {
  const [data, setData] = useState<TimelineStep[]>([]);
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  useEffect(() => {
    async function fetchTimeline() {
      const observations = await getObservations(runId);
      const actions = await getActions(runId);

      // Merge observations and actions
      const timeline = observations.map((obs, i) => ({
        step: obs.step,
        url: obs.url,
        action: actions[i]?.action,
        success: actions[i]?.success,
        duration: actions[i]?.duration_ms,
      }));

      setData(timeline);
    }

    if (runId) {
      fetchTimeline();
    }
  }, [runId]);

  return (
    <div ref={ref} className="w-full">
      <motion.h3
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
        className="text-2xl font-display font-bold text-foreground mb-6"
      >
        Journey Timeline
      </motion.h3>
      <div className="space-y-4">
        {data.map((step, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: i * 0.08, ease: [0.33, 1, 0.68, 1] }}
          >
            <Card className="transition-all hover:ring-primary/30 hover:shadow-md">
              <CardContent className="flex items-center gap-4">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-mono text-sm font-bold shrink-0 ${
                    step.success
                      ? 'bg-primary/10 text-primary border-2 border-primary/20'
                      : 'bg-critical/10 text-critical border-2 border-critical/20'
                  }`}
                >
                  {step.step}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-display font-semibold text-foreground">{step.action || 'Navigated'}</p>
                  <p className="text-sm text-muted-foreground font-mono break-all">{step.url}</p>
                </div>
                {step.duration && (
                  <span className="text-sm text-muted-foreground font-mono">{step.duration}ms</span>
                )}
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
