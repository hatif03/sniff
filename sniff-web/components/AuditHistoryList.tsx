"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getAuditHistory, type AuditHistoryEntry, type AuditStatus } from '@/lib/audits';

const POLL_INTERVAL_MS = 5000;

const badgeVariant = (status: AuditStatus): 'default' | 'destructive' | 'secondary' => {
  if (status === 'completed') return 'default';
  if (status === 'failed') return 'destructive';
  return 'secondary';
};

/**
 * "Audits" section for the dashboard.
 *
 * ponytail: the backend has no GET /audits list-all endpoint (src/api/main.py
 * only defines POST /audits and GET /audits/{audit_id}), so unlike the runs
 * list above (backed by Supabase), there is no real persisted audit history
 * to query. This instead replays the audit_ids this browser has triggered
 * (lib/audits.ts localStorage helpers) and polls each one's live status.
 * It only ever shows audits started from this browser - not a real list.
 * Replace with a real query once/if the backend gains a list endpoint.
 */
export default function AuditHistoryList() {
  const [entries, setEntries] = useState<AuditHistoryEntry[]>([]);
  const [statuses, setStatuses] = useState<Record<string, AuditStatus>>({});

  // One-time read of localStorage, unavailable during SSR/first render, not
  // state derivable from props/state.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setEntries(getAuditHistory());
  }, []);

  // `statuses` is read below but intentionally left out of the deps: this
  // effect should only restart its poll timer when the set of tracked audit
  // ids changes, not on every status update it produces.
  useEffect(() => {
    if (entries.length === 0) return;

    let cancelled = false;

    async function refresh() {
      const pending = entries.filter((e) => {
        const s = statuses[e.audit_id];
        return !s || s === 'queued' || s === 'running';
      });
      if (pending.length === 0) return;

      const results = await Promise.all(
        pending.map(async (e) => {
          try {
            const res = await fetch(`/api/backend/audits/${e.audit_id}`);
            const data = await res.json();
            return [e.audit_id, res.ok ? (data.status as AuditStatus) : 'failed'] as const;
          } catch {
            return [e.audit_id, 'failed'] as const;
          }
        })
      );
      if (cancelled) return;
      setStatuses((prev) => ({ ...prev, ...Object.fromEntries(results) }));
    }

    refresh();
    const timer = setInterval(refresh, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entries]);

  if (entries.length === 0) return null;

  return (
    <div className="mt-12">
      <div className="flex items-baseline justify-between mb-4">
        <h2 className="text-2xl font-display font-bold text-foreground">Audits</h2>
        <p className="text-xs text-muted-foreground">Only audits triggered from this browser are shown</p>
      </div>
      <div className="space-y-3">
        {entries.map((e, i) => {
          const status = statuses[e.audit_id] ?? 'queued';
          return (
            <motion.div
              key={e.audit_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: i * 0.05 }}
            >
              <Link href={`/dashboard/audits/${e.audit_id}`} className="block">
                <Card className="transition-all hover:ring-primary/40 hover:shadow-lg">
                  <CardContent className="flex items-center justify-between gap-4">
                    <div className="min-w-0">
                      <p className="font-display font-semibold text-foreground truncate">{e.url}</p>
                      <p className="text-xs text-muted-foreground">{new Date(e.created_at).toLocaleString()}</p>
                    </div>
                    <Badge variant={badgeVariant(status)} className="shrink-0 text-xs font-bold">
                      {status}
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
