"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import RunTimeline from '@/components/RunTimeline';
import AgentReasoningViz from '@/components/AgentReasoningViz';
import PersonaReviewCard from '@/components/PersonaReviewCard';
import UserConfidenceViz from '@/components/UserConfidenceViz';
import ScreenshotGallery from '@/components/ScreenshotGallery';
import { getRunDetails } from '@/lib/queries';

interface Run {
  run_id: string;
  persona_name: string;
  goal: string;
  outcome: string;
  created_at: string;
}

export default function RunDetailsPage({ params }: { params: Promise<{ runId: string }> }) {
  const [run, setRun] = useState<Run | null>(null);
  const [loading, setLoading] = useState(true);
  const [runId, setRunId] = useState<string>('');

  useEffect(() => {
    async function initAndFetch() {
      const resolvedParams = await params;
      setRunId(resolvedParams.runId);

      try {
        const data = await getRunDetails(resolvedParams.runId);
        setRun(data);
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
      <main className="min-h-screen py-32 px-6 bg-background">
        <div className="max-w-6xl mx-auto space-y-8">
          <div className="animate-pulse bg-card rounded-xl h-32 ring-1 ring-foreground/10" />
          <div className="animate-pulse bg-card rounded-xl h-64 ring-1 ring-foreground/10" />
          <div className="animate-pulse bg-card rounded-xl h-96 ring-1 ring-foreground/10" />
        </div>
      </main>
    );
  }

  if (!run) {
    return (
      <main className="min-h-screen py-32 px-6 bg-background">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <Card size="sm" className="[--card-spacing:--spacing(12)]">
              <CardContent className="text-center">
                <h2 className="text-2xl font-display font-bold text-foreground mb-4">
                  Run Not Found
                </h2>
                <p className="text-muted-foreground mb-6">
                  The test run you&apos;re looking for doesn&apos;t exist or hasn&apos;t been uploaded yet.
                </p>
                <Button asChild>
                  <Link href="/dashboard">Back to Dashboard</Link>
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen py-32 px-6 bg-background">
      <div className="max-w-6xl mx-auto space-y-12">
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
              <h1 className="text-5xl font-display font-bold text-foreground mb-4">
                {run.persona_name} Journey
              </h1>
              <p className="text-lg text-muted-foreground">{run.goal}</p>
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
        <AgentReasoningViz runId={runId} />
        <ScreenshotGallery runId={runId} />
      </div>
    </main>
  );
}
