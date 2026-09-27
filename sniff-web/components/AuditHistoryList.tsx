"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getDashboardAuditFeed, type DashboardAuditFeedItem } from '@/lib/queries';

const scoreVariant = (score: number | null): 'default' | 'destructive' | 'secondary' => {
  if (score === null) return 'secondary';
  if (score >= 7) return 'default';
  if (score >= 4) return 'secondary';
  return 'destructive';
};

/**
 * Shared "Audits" section for the dashboard — standalone page audits plus
 * whole-site crawls as a single row each (per-page rows are hidden; they
 * live under /dashboard/site-audits/{id}).
 */
export default function AuditHistoryList() {
  const [items, setItems] = useState<DashboardAuditFeedItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAudits() {
      try {
        const data = await getDashboardAuditFeed();
        setItems(data);
      } catch (err) {
        console.error('Failed to fetch audits:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchAudits();
  }, []);

  if (loading || items.length === 0) return null;

  return (
    <div className="mt-12">
      <div className="flex items-baseline justify-between mb-4">
        <h2 className="text-2xl font-display font-bold text-foreground">Audits</h2>
        <p className="text-xs text-muted-foreground">Every audit run on Sniff, shared with everyone</p>
      </div>
      <div className="space-y-3">
        {items.map((item, i) => {
          if (item.kind === 'page') {
            return (
              <motion.div
                key={item.audit_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: i * 0.05 }}
              >
                <Link href={`/dashboard/audits/${item.audit_id}`} className="block">
                  <Card className="transition-all hover:ring-primary/40 hover:shadow-lg">
                    <CardContent className="flex items-center justify-between gap-4">
                      <div className="min-w-0">
                        <p className="font-display font-semibold text-foreground truncate">{item.url}</p>
                        <p className="text-xs text-muted-foreground truncate">
                          {item.label ?? new Date(item.created_at).toLocaleString()}
                        </p>
                      </div>
                      <Badge variant={scoreVariant(item.overall_score)} className="shrink-0 text-xs font-bold">
                        {item.overall_score !== null ? `${Number(item.overall_score).toFixed(1)}/10` : '—'}
                      </Badge>
                    </CardContent>
                  </Card>
                </Link>
              </motion.div>
            );
          }

          return (
            <motion.div
              key={item.site_audit_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: i * 0.05 }}
            >
              <Link href={`/dashboard/site-audits/${item.site_audit_id}`} className="block">
                <Card className="transition-all hover:ring-primary/40 hover:shadow-lg">
                  <CardContent className="flex items-center justify-between gap-4">
                    <div className="min-w-0">
                      <p className="font-display font-semibold text-foreground truncate">{item.seed_url}</p>
                      <p className="text-xs text-muted-foreground truncate">
                        Site audit · {item.pages_audited} page{item.pages_audited === 1 ? '' : 's'} audited
                      </p>
                    </div>
                    <Badge variant={item.status === 'completed' ? 'default' : 'secondary'} className="shrink-0 text-xs font-bold">
                      Site
                    </Badge>
                  </CardContent>
                </Card>
              </Link>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
