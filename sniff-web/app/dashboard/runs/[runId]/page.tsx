"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
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
          <div className="animate-pulse bg-surface rounded-xl h-32 border border-primary/10" />
          <div className="animate-pulse bg-surface rounded-xl h-64 border border-primary/10" />
          <div className="animate-pulse bg-surface rounded-xl h-96 border border-primary/10" />
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
            className="bg-surface rounded-xl p-12 border border-primary/10 text-center"
          >
            <h2 className="text-2xl font-display font-bold text-primary mb-4">
              Run Not Found
            </h2>
            <p className="text-muted mb-6">
              The test run you&apos;re looking for doesn&apos;t exist or hasn&apos;t been uploaded yet.
            </p>
            <Link
              href="/dashboard"
              className="inline-block px-6 py-3 bg-accent text-white rounded-lg font-medium hover:bg-accent/90 transition-colors"
            >
              Back to Dashboard
            </Link>
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
            className="text-sm text-muted hover:text-accent transition-colors mb-4 inline-block"
          >
            ← Back to Dashboard
          </Link>
          <div className="flex justify-between items-start mb-6">
            <div>
              <h1 className="text-5xl font-display font-bold text-primary mb-4">
                {run.persona_name} Journey
              </h1>
              <p className="text-lg text-muted">{run.goal}</p>
            </div>
            <span
              className={`px-4 py-2 rounded-full text-sm font-bold ${
                run.outcome === 'success'
                  ? 'bg-accent/10 text-accent'
                  : run.outcome === 'failure'
                  ? 'bg-critical/10 text-critical'
                  : 'bg-warning/10 text-warning'
              }`}
            >
              {run.outcome}
            </span>
          </div>
          <p className="text-sm text-muted">
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
