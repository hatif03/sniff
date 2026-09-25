"use client";

import { useEffect, useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
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
  action: string;
  target: string;
  emoji: string;
  label: string;
}

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

function getConfidenceLabel(confidence: number): { emoji: string; label: string } {
  if (confidence >= 0.7) {
    return { emoji: '😊', label: 'Confident' };
  } else if (confidence >= 0.5) {
    return { emoji: '😐', label: 'Uncertain' };
  } else if (confidence >= 0.3) {
    return { emoji: '😕', label: 'Confused' };
  } else {
    return { emoji: '😣', label: 'Frustrated' };
  }
}

export default function UserConfidenceViz({ runId }: { runId: string }) {
  const [confidenceData, setConfidenceData] = useState<UserConfidenceData[]>([]);
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  useEffect(() => {
    async function fetchAndCalculate() {
      const actions = await getActions(runId);

      const data: UserConfidenceData[] = actions.map((action) => {
        const confidence = calculateUserConfidence(action);
        const { emoji, label } = getConfidenceLabel(confidence);

        return {
          step: action.step,
          confidence,
          action: action.action,
          target: action.target,
          emoji,
          label,
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

  return (
    <div ref={ref}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
      >
        <h3 className="text-2xl font-display font-bold text-primary mb-2">
          User Confidence Over Time
        </h3>
        <p className="text-sm text-muted mb-6">
          How confident the user felt at each step, based on success rate and hesitation patterns
        </p>

        {/* Overall confidence badge */}
        <div className="mb-6">
          <div className="inline-flex items-center gap-3 bg-surface rounded-xl px-4 py-3 border border-primary/10">
            <span className="text-sm text-muted">Average User Confidence:</span>
            <span
              className={`text-lg font-bold ${
                avgConfidence >= 0.7
                  ? 'text-accent'
                  : avgConfidence >= 0.5
                  ? 'text-warning'
                  : 'text-critical'
              }`}
            >
              {(avgConfidence * 100).toFixed(0)}%
            </span>
            <span className="text-xl">
              {getConfidenceLabel(avgConfidence).emoji}
            </span>
          </div>
        </div>
      </motion.div>

      {/* Confidence bars */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="bg-surface rounded-xl p-6 border border-primary/10 mb-6"
      >
        <div className="space-y-3">
          {confidenceData.map((d, i) => (
            <div key={d.step} className="space-y-2">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-mono text-muted">Step {d.step}</span>
                  <span className="text-lg">{d.emoji}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted">{d.label}</span>
                  <span
                    className={`text-sm font-bold ${
                      d.confidence >= 0.7
                        ? 'text-accent'
                        : d.confidence >= 0.5
                        ? 'text-warning'
                        : 'text-critical'
                    }`}
                  >
                    {(d.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
              <div className="relative h-2 bg-background rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${d.confidence * 100}%` }}
                  transition={{ duration: 0.8, delay: 0.3 + i * 0.1, ease: [0.33, 1, 0.68, 1] }}
                  className={`absolute inset-y-0 left-0 rounded-full ${
                    d.confidence >= 0.7
                      ? 'bg-gradient-to-r from-accent to-soft-accent'
                      : d.confidence >= 0.5
                      ? 'bg-gradient-to-r from-warning to-warning/70'
                      : 'bg-gradient-to-r from-critical to-critical/70'
                  }`}
                />
              </div>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Emotional journey cards */}
      <div className="space-y-4">
        {confidenceData.map((d, i) => (
          <motion.div
            key={d.step}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 + i * 0.1, ease: [0.33, 1, 0.68, 1] }}
            className="bg-surface rounded-xl p-6 border border-primary/10 hover:border-accent/30 transition-all shadow-sm hover:shadow-md"
          >
            <div className="flex justify-between items-start gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-2xl">{d.emoji}</span>
                  <p className="font-display font-semibold text-primary">
                    {d.action} → <span className="text-accent">{d.target}</span>
                  </p>
                </div>
                <p className="text-sm text-muted">
                  User felt <span className="font-semibold">{d.label.toLowerCase()}</span> during this step
                </p>
              </div>
              <div className="flex-shrink-0">
                <span
                  className={`px-3 py-1 rounded-full text-xs font-bold ${
                    d.confidence >= 0.7
                      ? 'bg-accent/10 text-accent'
                      : d.confidence >= 0.5
                      ? 'bg-warning/10 text-warning'
                      : 'bg-critical/10 text-critical'
                  }`}
                >
                  {(d.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
