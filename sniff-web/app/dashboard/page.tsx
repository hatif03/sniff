"use client";

import { useEffect, useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import Link from 'next/link';
import { getRecentRuns } from '@/lib/queries';

interface Run {
  run_id: string;
  persona_name: string;
  goal: string;
  outcome: string;
  total_steps: number;
  created_at: string;
}

export default function DashboardPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true });

  useEffect(() => {
    async function fetchRuns() {
      try {
        const data = await getRecentRuns();
        setRuns(data);
      } catch (error) {
        console.error('Error fetching runs:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchRuns();
  }, []);

  return (
    <main className="min-h-screen py-32 px-6 bg-background">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
          className="mb-12"
        >
          <Link
            href="/"
            className="text-sm text-muted hover:text-accent transition-colors mb-4 inline-block"
          >
            ← Back to Home
          </Link>
          <h1 className="text-5xl font-display font-bold text-primary mb-4">
            Test Runs Dashboard
          </h1>
          <p className="text-lg text-muted">
            View and analyze your Sherlock test runs
          </p>
        </motion.div>

        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div
                key={`skeleton-${i}`}
                className="animate-pulse bg-surface rounded-xl h-32 border border-primary/10"
              />
            ))}
          </div>
        ) : runs.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="bg-surface rounded-xl p-12 border border-primary/10 text-center"
          >
            <p className="text-muted mb-4">No test runs found</p>
            <p className="text-sm text-muted">
              Configure your Supabase credentials in .env.local to start viewing runs
            </p>
          </motion.div>
        ) : (
          <div ref={ref} className="space-y-4">
            {runs.map((run, i) => (
              <motion.div
                key={run.run_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: i * 0.1, ease: [0.33, 1, 0.68, 1] }}
              >
                <Link
                  href={`/dashboard/runs/${run.run_id}`}
                  className="block bg-surface rounded-xl p-6 border border-primary/10 hover:border-accent/30 transition-all shadow-sm hover:shadow-lg"
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="font-display font-bold text-primary text-xl mb-2">
                        {run.persona_name}
                      </h3>
                      <p className="text-sm text-muted">{run.goal}</p>
                    </div>
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-bold ${
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
                  <div className="flex gap-4 text-sm text-muted">
                    <span>{run.total_steps} steps</span>
                    <span>•</span>
                    <span>{new Date(run.created_at).toLocaleDateString()}</span>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
