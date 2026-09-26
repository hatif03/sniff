"use client";

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { PlusIcon } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getRecentRuns } from '@/lib/queries';
import AuditHistoryList from '@/components/AuditHistoryList';

interface Run {
  run_id: string;
  persona_name: string;
  goal: string;
  outcome: string;
  total_steps: number;
  created_at: string;
}

const outcomeBadgeVariant = (outcome: string): 'default' | 'destructive' | 'secondary' => {
  if (outcome === 'success') return 'default';
  if (outcome === 'failure') return 'destructive';
  return 'secondary';
};

const listVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.33, 1, 0.68, 1] as const } },
};

export default function DashboardPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);

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
          className="mb-12 flex items-start justify-between gap-6 flex-wrap"
        >
          <div>
            <Link
              href="/"
              className="text-sm text-muted-foreground hover:text-primary transition-colors mb-4 inline-block"
            >
              ← Back to Home
            </Link>
            <h1 className="text-5xl font-display font-bold text-foreground mb-4">
              Test Runs Dashboard
            </h1>
            <p className="text-lg text-muted-foreground">
              View and analyze your Sniff test runs
            </p>
          </div>
          <div className="flex gap-3 mt-1">
            <Button asChild size="lg" variant="secondary">
              <Link href="/dashboard/new-run?mode=audit">
                <PlusIcon data-icon="inline-start" />
                New Audit
              </Link>
            </Button>
            <Button asChild size="lg">
              <Link href="/dashboard/new-run">
                <PlusIcon data-icon="inline-start" />
                New Run
              </Link>
            </Button>
          </div>
        </motion.div>

        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div
                key={`skeleton-${i}`}
                className="animate-pulse bg-card rounded-xl h-32 ring-1 ring-foreground/10"
              />
            ))}
          </div>
        ) : runs.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Card size="sm" className="[--card-spacing:--spacing(12)]">
              <CardContent className="text-center">
                <p className="text-muted-foreground mb-4">No test runs found</p>
                <p className="text-sm text-muted-foreground mb-6">
                  Configure your Supabase credentials in .env.local to start viewing runs,
                  or trigger your first run right from here.
                </p>
                <Button asChild>
                  <Link href="/dashboard/new-run">
                    <PlusIcon data-icon="inline-start" />
                    Start a run
                  </Link>
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        ) : (
          <motion.div variants={listVariants} initial="hidden" animate="show" className="space-y-4">
            {runs.map((run) => (
              <motion.div key={run.run_id} variants={itemVariants}>
                <Link href={`/dashboard/runs/${run.run_id}`} className="block">
                  <Card className="transition-all hover:ring-primary/40 hover:shadow-lg">
                    <CardContent>
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="font-display font-bold text-foreground text-xl mb-2">
                            {run.persona_name}
                          </h3>
                          <p className="text-sm text-muted-foreground">{run.goal}</p>
                        </div>
                        <Badge variant={outcomeBadgeVariant(run.outcome)} className="text-xs font-bold">
                          {run.outcome}
                        </Badge>
                      </div>
                      <div className="flex gap-4 text-sm text-muted-foreground">
                        <span>{run.total_steps} steps</span>
                        <span>•</span>
                        <span>{new Date(run.created_at).toLocaleDateString()}</span>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              </motion.div>
            ))}
          </motion.div>
        )}

        <AuditHistoryList />
      </div>
    </main>
  );
}
