"use client";

import { useEffect, useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { getPersonaReview } from '@/lib/queries';

interface PersonaReview {
  persona_display_name: string;
  overall_sentiment: 'positive' | 'neutral' | 'negative';
  experience_rating: number;
  narrative: string;
  friction_points: string[];
  positive_aspects: string[];
  recommendations: string[];
  abandonment_likelihood: 'low' | 'medium' | 'high';
}

export default function PersonaReviewCard({ runId }: { runId: string }) {
  const [review, setReview] = useState<PersonaReview | null>(null);
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  useEffect(() => {
    async function fetchReview() {
      const data = await getPersonaReview(runId);
      setReview(data);
    }

    if (runId) {
      fetchReview();
    }
  }, [runId]);

  if (!review) return null;

  const sentimentColor = {
    positive: 'text-accent',
    neutral: 'text-warning',
    negative: 'text-critical',
  }[review.overall_sentiment];

  const sentimentBg = {
    positive: 'from-accent/10 to-soft-accent/10',
    neutral: 'from-warning/10 to-warning/5',
    negative: 'from-critical/10 to-critical/5',
  }[review.overall_sentiment];

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
      className={`bg-gradient-to-br ${sentimentBg} p-8 rounded-2xl border border-primary/10 shadow-lg`}
    >
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-2xl font-display font-bold text-primary">
          {review.persona_display_name}&apos;s Review
        </h3>
        <div className="flex items-center gap-3">
          <span className={`text-3xl font-display font-bold ${sentimentColor}`}>
            {review.experience_rating}/10
          </span>
          <span className={`text-sm font-medium uppercase tracking-wide ${sentimentColor}`}>
            {review.overall_sentiment}
          </span>
        </div>
      </div>

      <p className="text-primary italic mb-6 leading-relaxed text-lg">
        &quot;{review.narrative}&quot;
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.2, ease: [0.33, 1, 0.68, 1] }}
          className="bg-surface rounded-xl p-4 border border-primary/10"
        >
          <h4 className="font-display font-semibold text-sm text-primary mb-3">
            Friction Points
          </h4>
          <ul className="space-y-2">
            {review.friction_points.map((point, i) => (
              <li key={i} className="text-sm text-critical flex items-start gap-2">
                <span>•</span>
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.3, ease: [0.33, 1, 0.68, 1] }}
          className="bg-surface rounded-xl p-4 border border-primary/10"
        >
          <h4 className="font-display font-semibold text-sm text-primary mb-3">
            What Worked
          </h4>
          <ul className="space-y-2">
            {review.positive_aspects.map((aspect, i) => (
              <li key={i} className="text-sm text-accent flex items-start gap-2">
                <span>•</span>
                <span>{aspect}</span>
              </li>
            ))}
          </ul>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4, ease: [0.33, 1, 0.68, 1] }}
        className="bg-surface rounded-xl p-4 border border-primary/10 mb-4"
      >
        <h4 className="font-display font-semibold text-sm text-primary mb-3">
          Recommendations
        </h4>
        <ul className="space-y-2">
          {review.recommendations.map((rec, i) => (
            <li key={i} className="text-sm text-muted flex items-start gap-2">
              <span className="text-accent">→</span>
              <span>{rec}</span>
            </li>
          ))}
        </ul>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.5 }}
      >
        <span
          className={`px-4 py-2 rounded-full text-xs font-bold uppercase tracking-wide inline-block ${
            review.abandonment_likelihood === 'high'
              ? 'bg-critical/10 text-critical'
              : review.abandonment_likelihood === 'medium'
              ? 'bg-warning/10 text-warning'
              : 'bg-accent/10 text-accent'
          }`}
        >
          Abandonment Risk: {review.abandonment_likelihood}
        </span>
      </motion.div>
    </motion.div>
  );
}
