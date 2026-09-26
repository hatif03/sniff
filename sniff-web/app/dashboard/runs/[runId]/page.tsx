"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Container } from '@/components/ui/container';
import { Display2, Heading3, Body } from '@/components/ui/typography';
import RunTimeline from '@/components/RunTimeline';
import AgentReasoningViz from '@/components/AgentReasoningViz';
import PersonaReviewCard from '@/components/PersonaReviewCard';
import UserConfidenceViz from '@/components/UserConfidenceViz';
import ScreenshotGallery from '@/components/ScreenshotGallery';
import { getRunDetails, getAgentConfidenceMetrics } from '@/lib/queries';

interface Run {
  run_id: string;
  persona_name: string;
  goal: string;
  outcome: string;
  created_at: string;
}

interface ConfidenceMetrics {
  run_id: string;
  total_decisions: number;
  avg_confidence: number;
  min_confidence: number;
  max_confidence: number;
  repaired_decisions: number;
  fallback_decisions: number;
}

export default function RunDetailsPage({ params }: { params: Promise<{ runId: string }> }) {
  const [run, setRun] = useState<Run | null>(null);
  const [confidence, setConfidence] = useState<ConfidenceMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [runId, setRunId] = useState<string>('');

  useEffect(() => {
    async function initAndFetch() {
      const resolvedParams = await params;
      setRunId(resolvedParams.runId);

      try {
        const [data, confidenceData] = await Promise.all([
          getRunDetails(resolvedParams.runId),
          getAgentConfidenceMetrics(resolvedParams.runId),
        ]);
        setRun(data);
        setConfidence(confidenceData);
      } catch (error) {
        console.error('Error fetching run details:', error);
      } finally {
        setLoading(false);
      }
    }

    initAndFetch();
  }, [params]);

  if (loading) {
    return (
      <main className="min-h-screen py-32 bg-background">
        <Container className="space-y-8">
          <div className="animate-pulse bg-card rounded-xl h-32 ring-1 ring-foreground/10" />
          <div className="animate-pulse bg-card rounded-xl h-64 ring-1 ring-foreground/10" />
          <div className="animate-pulse bg-card rounded-xl h-96 ring-1 ring-foreground/10" />
        </Container>
      </main>
    );
  }

  if (!run) {
    return (
      <main className="min-h-screen py-32 bg-background">
        <Container>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <Card size="sm" className="[--card-spacing:--spacing(12)]">
              <CardContent className="text-center">
                <Heading3 as="h2" className="text-foreground mb-4">
                  Run Not Found
                </Heading3>
                <Body className="text-muted-foreground mb-6">
                  The test run you&apos;re looking for doesn&apos;t exist or hasn&apos;t been uploaded yet.
                </Body>
                <Button asChild>
                  <Link href="/dashboard">Back to Dashboard</Link>
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        </Container>
      </main>
    );
  }

  return (
    <main className="min-h-screen py-32 bg-background">
      <Container className="space-y-12">
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
          <div className="flex justify-between items-start mb-6">
            <div>
              <Display2 as="h1" className="text-foreground mb-4">
                {run.persona_name} Journey
              </Display2>
              <Body className="text-lg text-muted-foreground">{run.goal}</Body>
            </div>
            <Badge
              variant={run.outcome === 'success' ? 'default' : run.outcome === 'failure' ? 'destructive' : 'secondary'}
              className="px-4 py-2 text-sm font-bold"
            >
              {run.outcome}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            {new Date(run.created_at).toLocaleString()}
          </p>
        </motion.div>

        <PersonaReviewCard runId={runId} />
        <UserConfidenceViz runId={runId} />
        <RunTimeline runId={runId} />
        {confidence && (
          <Card>
            <CardContent className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
              <div>
                <p className="text-2xl font-display font-bold text-foreground">
                  {Math.round(confidence.avg_confidence * 100)}%
                </p>
                <p className="text-xs text-muted-foreground mt-1">Avg. agent confidence</p>
              </div>
              <div>
                <p className="text-2xl font-display font-bold text-foreground">{confidence.total_decisions}</p>
                <p className="text-xs text-muted-foreground mt-1">Total decisions</p>
              </div>
              <div>
                <p className="text-2xl font-display font-bold text-foreground">{confidence.repaired_decisions}</p>
                <p className="text-xs text-muted-foreground mt-1">Repaired decisions</p>
              </div>
              <div>
                <p className="text-2xl font-display font-bold text-foreground">{confidence.fallback_decisions}</p>
                <p className="text-xs text-muted-foreground mt-1">Fallback decisions</p>
              </div>
            </CardContent>
          </Card>
        )}
        <AgentReasoningViz runId={runId} />
        <ScreenshotGallery runId={runId} />
      </Container>
    </main>
  );
}
