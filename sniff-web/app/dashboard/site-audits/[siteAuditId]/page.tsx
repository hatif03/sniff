"use client";

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Container } from '@/components/ui/container';
import { Display2, Heading3 } from '@/components/ui/typography';
import type { SiteAuditStatusResponse } from '@/lib/site-audits';

const POLL_INTERVAL_MS = 2500;

// Mirrors scoreBand() in app/dashboard/audits/[auditId]/page.tsx (same 7/4
// thresholds) - duplicated rather than imported since that page is a
// reused-unchanged reference, not a shared module.
function scoreBand(score: number): { textClass: string; badgeVariant: 'default' | 'secondary' | 'destructive' } {
  if (score >= 7) return { textClass: 'text-chart-good', badgeVariant: 'default' };
  if (score >= 4) return { textClass: 'text-chart-warning', badgeVariant: 'secondary' };
  return { textClass: 'text-chart-critical', badgeVariant: 'destructive' };
}

const MANIFEST_STATUS_BADGE: Record<string, 'default' | 'secondary' | 'destructive'> = {
  audited: 'default',
  skipped: 'secondary',
  failed: 'destructive',
};

type StatusFilter = 'all' | 'audited' | 'skipped' | 'failed';

export default function SiteAuditReportPage({ params }: { params: Promise<{ siteAuditId: string }> }) {
  const [data, setData] = useState<SiteAuditStatusResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filterText, setFilterText] = useState('');
  const [filterStatus, setFilterStatus] = useState<StatusFilter>('all');
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function poll(id: string) {
      try {
        const res = await fetch(`/api/backend/site-audits/${id}`);
        const json: SiteAuditStatusResponse = await res.json();
        if (cancelled) return;
        if (!res.ok) {
          setLoadError((json as unknown as { error?: string })?.error ?? `Backend returned ${res.status}`);
          if (pollTimer.current) clearInterval(pollTimer.current);
          return;
        }
        setData(json);
        if (json.status === 'completed' || json.status === 'failed') {
          if (pollTimer.current) clearInterval(pollTimer.current);
        }
      } catch (err) {
        if (cancelled) return;
        setLoadError(err instanceof Error ? err.message : 'Could not reach the backend');
        if (pollTimer.current) clearInterval(pollTimer.current);
      }
    }

    async function init() {
      const { siteAuditId: id } = await params;
      if (cancelled) return;
      await poll(id);
      pollTimer.current = setInterval(() => poll(id), POLL_INTERVAL_MS);
    }

    init();
    return () => {
      cancelled = true;
      if (pollTimer.current) clearInterval(pollTimer.current);
    };
  }, [params]);

  const isInProgress = data ? data.status === 'queued' || data.status === 'running' : false;

  const scoredPages = data ? data.pages.filter((p) => p.overall_score !== null) : [];
  const averageScore =
    scoredPages.length > 0
      ? scoredPages.reduce((sum, p) => sum + (p.overall_score as number), 0) / scoredPages.length
      : null;

  const manifestEntries = data
    ? Object.entries(data.manifest).filter(([url, entry]) => {
        if (filterStatus !== 'all' && entry.status !== filterStatus) return false;
        if (filterText && !url.toLowerCase().includes(filterText.toLowerCase())) return false;
        return true;
      })
    : [];

  return (
    <main className="min-h-screen py-32 px-6 bg-background">
      <Container className="space-y-8">
        <div>
          <Link
            href="/dashboard"
            className="text-sm text-muted-foreground hover:text-primary transition-colors mb-4 inline-block"
          >
            ← Back to Dashboard
          </Link>
          <Display2 as="h1" className="mb-2">Site Audit</Display2>
          {data && <p className="text-sm text-muted-foreground font-mono break-all">{data.seed_url}</p>}
        </div>

        {!data && !loadError && (
          <div className="animate-pulse bg-card rounded-xl h-40 ring-1 ring-foreground/10" />
        )}

        {loadError && (
          <Card>
            <CardContent className="text-sm text-critical">{loadError}</CardContent>
          </Card>
        )}

        {data && (
          <>
            <Card>
              <CardContent className="grid grid-cols-2 sm:grid-cols-4 gap-6">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Status</p>
                  <Badge
                    variant={
                      data.status === 'completed' ? 'default' : data.status === 'failed' ? 'destructive' : 'secondary'
                    }
                  >
                    {data.status}
                  </Badge>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Average score</p>
                  <p
                    className={`text-lg font-display font-bold ${
                      averageScore !== null ? scoreBand(averageScore).textClass : 'text-muted-foreground'
                    }`}
                  >
                    {averageScore !== null ? `${averageScore.toFixed(1)}/10` : '—'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Pages discovered</p>
                  <p className="text-lg font-display font-bold text-foreground">{data.pages_discovered}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Pages audited</p>
                  <p className="text-lg font-display font-bold text-foreground">
                    {data.pages_audited} / {data.max_pages}
                  </p>
                </div>
              </CardContent>
            </Card>

            {isInProgress && (
              <Card>
                <CardContent className="text-center py-8 space-y-2">
                  <p className="font-display font-semibold text-foreground">
                    Auditing page {data.pages_audited} of up to {data.max_pages}…
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {data.pages_discovered} page{data.pages_discovered === 1 ? '' : 's'} discovered so far - this page
                    updates automatically.
                  </p>
                </CardContent>
              </Card>
            )}

            {data.status === 'failed' && data.error && (
              <Card>
                <CardContent className="text-sm text-critical">{data.error}</CardContent>
              </Card>
            )}

            <section className="space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <Heading3 as="h2">Pages</Heading3>
                <div className="flex gap-3">
                  <Input
                    placeholder="Filter by URL…"
                    value={filterText}
                    onChange={(e) => setFilterText(e.target.value)}
                    className="w-56"
                  />
                  <Select value={filterStatus} onValueChange={(v) => setFilterStatus(v as StatusFilter)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="audited">Audited</SelectItem>
                      <SelectItem value="skipped">Skipped</SelectItem>
                      <SelectItem value="failed">Failed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                {manifestEntries.map(([url, entry]) => {
                  const page = entry.audit_id ? data.pages.find((p) => p.audit_id === entry.audit_id) : undefined;
                  return (
                    <Card key={url}>
                      <CardContent className="flex items-center justify-between gap-4 flex-wrap">
                        <div className="min-w-0">
                          <p className="text-sm text-foreground font-mono truncate">{url}</p>
                          {(entry.reason || entry.error) && (
                            <p className="text-xs text-muted-foreground mt-1">{entry.reason ?? entry.error}</p>
                          )}
                        </div>
                        <div className="flex items-center gap-3 shrink-0">
                          <Badge variant={MANIFEST_STATUS_BADGE[entry.status] ?? 'secondary'}>{entry.status}</Badge>
                          {page && page.overall_score !== null && (
                            <Badge variant={scoreBand(page.overall_score).badgeVariant}>
                              {page.overall_score.toFixed(1)}/10
                            </Badge>
                          )}
                          {entry.audit_id && (
                            <Button asChild size="sm" variant="secondary">
                              <Link href={`/dashboard/audits/${entry.audit_id}`}>View report</Link>
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
                {manifestEntries.length === 0 && (
                  <p className="text-sm text-muted-foreground">No pages match this filter.</p>
                )}
              </div>
            </section>
          </>
        )}
      </Container>
    </main>
  );
}
