"use client";

import { useEffect, useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { getFrictionAnalytics } from '@/lib/queries';

interface FrictionData {
  friction_point: string;
  persona_name: string;
  occurrence_count: number;
}

export default function FrictionHeatmap() {
  const [data, setData] = useState<FrictionData[]>([]);
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  useEffect(() => {
    async function fetchFriction() {
      const frictionData = await getFrictionAnalytics();
      setData(frictionData);
    }

    fetchFriction();
  }, []);

  if (data.length === 0) return null;

  const maxCount = Math.max(...data.map(d => d.occurrence_count), 1);

  return (
    <div ref={ref}>
      <motion.h3
        initial={{ opacity: 0, y: 20 }}
        animate={isInView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
        className="text-2xl font-display font-bold text-foreground mb-6"
      >
        Top Friction Points
      </motion.h3>
      <div className="space-y-3">
        {data.map((item, i) => {
          const percentage = (item.occurrence_count / maxCount) * 100;
          const intensity = percentage > 75 ? 'critical' : percentage > 50 ? 'warning' : 'soft-accent';

          return (
            <motion.div
              key={`${item.friction_point}-${i}`}
              initial={{ opacity: 0, x: -20 }}
              animate={isInView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.5, delay: i * 0.05, ease: [0.33, 1, 0.68, 1] }}
            >
              <Card className="hover:border-primary/30 transition-all shadow-sm hover:shadow-md">
                <CardContent className="flex items-center gap-4">
                  <div className="flex-1">
                    <p className="text-sm font-display font-semibold text-foreground mb-1">
                      {item.friction_point}
                    </p>
                    <p className="text-xs text-muted-foreground">{item.persona_name}</p>
                  </div>
                  <div className="flex-1 bg-background rounded-full h-3 overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={isInView ? { width: `${percentage}%` } : {}}
                      transition={{ duration: 0.8, delay: 0.3 + i * 0.05, ease: [0.33, 1, 0.68, 1] }}
                      className={`h-full rounded-full ${
                        intensity === 'critical'
                          ? 'bg-gradient-to-r from-critical to-critical/70'
                          : intensity === 'warning'
                          ? 'bg-gradient-to-r from-warning to-warning/70'
                          : 'bg-gradient-to-r from-soft-accent to-primary'
                      }`}
                    />
                  </div>
                  <span className="text-sm font-mono font-bold text-foreground w-8 text-right shrink-0">
                    {item.occurrence_count}
                  </span>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
