"use client";

import { useEffect, useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { getAgentReasoning } from '@/lib/queries';

interface Reasoning {
  id: string;
  step: number;
  action: string;
  target: string;
  reasoning: string;
  confidence: number;
}

export default function AgentReasoningViz({ runId }: { runId: string }) {
  const [reasoning, setReasoning] = useState<Reasoning[]>([]);
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

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

  return (
    <div ref={ref}>
      <motion.h3
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
        className="text-2xl font-display font-bold text-primary mb-6"
      >
        Agent Decision Confidence
      </motion.h3>
      <p className="text-sm text-muted mb-6">
        How confident the AI agent was in identifying the correct UI elements and actions
      </p>

      {/* Custom bar chart visualization */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="bg-surface rounded-xl p-6 border border-primary/10 mb-6"
      >
        <div className="space-y-3">
          {reasoning.map((r, i) => (
            <div key={r.id} className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm font-mono text-muted">Step {r.step}</span>
                <span
                  className={`text-sm font-bold ${
                    r.confidence > 0.7
                      ? 'text-accent'
                      : r.confidence > 0.4
                      ? 'text-warning'
                      : 'text-critical'
                  }`}
                >
                  {(r.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div className="relative h-2 bg-background rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${r.confidence * 100}%` }}
                  transition={{ duration: 0.8, delay: 0.3 + i * 0.1, ease: [0.33, 1, 0.68, 1] }}
                  className={`absolute inset-y-0 left-0 rounded-full ${
                    r.confidence > 0.7
                      ? 'bg-gradient-to-r from-accent to-soft-accent'
                      : r.confidence > 0.4
                      ? 'bg-gradient-to-r from-warning to-warning/70'
                      : 'bg-gradient-to-r from-critical to-critical/70'
                  }`}
                />
              </div>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Reasoning cards */}
      <div className="space-y-4">
        {reasoning.map((r, i) => (
          <motion.div
            key={r.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 + i * 0.1, ease: [0.33, 1, 0.68, 1] }}
            className="bg-surface rounded-xl p-6 border border-primary/10 hover:border-accent/30 transition-all shadow-sm hover:shadow-md"
          >
            <div className="flex justify-between items-start gap-4">
              <div className="flex-1">
                <p className="font-display font-semibold text-primary mb-2">
                  {r.action} → <span className="text-accent">{r.target}</span>
                </p>
                <p className="text-sm text-muted leading-relaxed">{r.reasoning}</p>
              </div>
              <div className="flex-shrink-0">
                <span
                  className={`px-3 py-1 rounded-full text-xs font-bold ${
                    r.confidence > 0.7
                      ? 'bg-accent/10 text-accent'
                      : r.confidence > 0.4
                      ? 'bg-warning/10 text-warning'
                      : 'bg-critical/10 text-critical'
                  }`}
                >
                  {(r.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
