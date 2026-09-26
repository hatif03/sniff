"use client";

import { useEffect, useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AnimatedNumber } from '@/components/AnimatedNumber';
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

  const sentimentBg = {
    positive: 'from-primary/10 to-soft-accent/10',
    neutral: 'from-warning/10 to-warning/5',
    negative: 'from-critical/10 to-critical/5',
  }[review.overall_sentiment];

  const sentimentBadgeVariant = {
    positive: 'default',
    neutral: 'secondary',
    negative: 'destructive',
  }[review.overall_sentiment] as 'default' | 'secondary' | 'destructive';

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
      className={`bg-gradient-to-br ${sentimentBg} p-8 rounded-2xl border border-foreground/10 shadow-lg`}
    >
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-2xl font-display font-bold text-foreground">
          {review.persona_display_name}&apos;s Review
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-3xl font-display font-bold text-gold">
            <AnimatedNumber value={review.experience_rating} decimals={1} />/10
          </span>
          <Badge variant={sentimentBadgeVariant} className="uppercase tracking-wide">
            {review.overall_sentiment}
          </Badge>
        </div>
      </div>

      <p className="text-foreground italic mb-6 leading-relaxed text-lg">
        &quot;{review.narrative}&quot;
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.2, ease: [0.33, 1, 0.68, 1] }}
        >
          <Card>
            <CardContent>
              <h4 className="font-display font-semibold text-sm text-foreground mb-3">
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
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.3, ease: [0.33, 1, 0.68, 1] }}
        >
          <Card>
            <CardContent>
              <h4 className="font-display font-semibold text-sm text-foreground mb-3">
                What Worked
              </h4>
              <ul className="space-y-2">
                {review.positive_aspects.map((aspect, i) => (
                  <li key={i} className="text-sm text-primary flex items-start gap-2">
                    <span>•</span>
                    <span>{aspect}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4, ease: [0.33, 1, 0.68, 1] }}
        className="mb-4"
      >
        <Card>
          <CardContent>
            <h4 className="font-display font-semibold text-sm text-foreground mb-3">
              Recommendations
            </h4>
            <ul className="space-y-2">
              {review.recommendations.map((rec, i) => (
                <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                  <span className="text-primary">→</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.5 }}
      >
        <Badge
          variant={review.abandonment_likelihood === 'high' ? 'destructive' : review.abandonment_likelihood === 'medium' ? 'secondary' : 'default'}
          className="px-4 py-2 uppercase tracking-wide"
        >
          Abandonment Risk: {review.abandonment_likelihood}
        </Badge>
      </motion.div>
    </motion.div>
  );
}
