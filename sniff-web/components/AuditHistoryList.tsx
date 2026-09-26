"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getRecentAudits } from '@/lib/queries';

interface AuditSummary {
  audit_id: string;
  url: string;
  persona: string | null;
  overall_score: number | null;
  label: string | null;
  verdict: string | null;
  created_at: string;
}

const scoreVariant = (score: number | null): 'default' | 'destructive' | 'secondary' => {
  if (score === null) return 'secondary';
  if (score >= 7) return 'default';
  if (score >= 4) return 'secondary';
  return 'destructive';
};

/**
 * Shared "Audits" section for the dashboard - every completed audit from
 * every visitor, persisted in Supabase (public-read, no auth), same pattern
 * as the runs list above.
 */
export default function AuditHistoryList() {
  const [audits, setAudits] = useState<AuditSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAudits() {
      try {
        const data = await getRecentAudits();
        setAudits((data ?? []) as AuditSummary[]);
      } catch (err) {
        console.error('Failed to fetch audits:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchAudits();
  }, []);

  if (loading || audits.length === 0) return null;

  return (
    <div className="mt-12">
      <div className="flex items-baseline justify-between mb-4">
        <h2 className="text-2xl font-display font-bold text-foreground">Audits</h2>
        <p className="text-xs text-muted-foreground">Every audit run on Sniff, shared with everyone</p>
      </div>
      <div className="space-y-3">
        {audits.map((a, i) => (
          <motion.div
            key={a.audit_id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: i * 0.05 }}
          >
            <Link href={`/dashboard/audits/${a.audit_id}`} className="block">
              <Card className="transition-all hover:ring-primary/40 hover:shadow-lg">
                <CardContent className="flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <p className="font-display font-semibold text-foreground truncate">{a.url}</p>
                    <p className="text-xs text-muted-foreground truncate">{a.label ?? new Date(a.created_at).toLocaleString()}</p>
                  </div>
                  <Badge variant={scoreVariant(a.overall_score)} className="shrink-0 text-xs font-bold">
                    {a.overall_score !== null ? `${a.overall_score.toFixed(1)}/10` : '—'}
                  </Badge>
                </CardContent>
              </Card>
            </Link>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
