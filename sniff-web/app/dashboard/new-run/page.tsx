"use client";

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, CheckCircle2, XCircle, ArrowRight } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ContainerNarrow } from '@/components/ui/container';
import { Display2, Body, Caption } from '@/components/ui/typography';
import type { AuditStatusResponse } from '@/lib/audits';
import type { SiteAuditStatusResponse } from '@/lib/site-audits';
import { getRecentSiteAudits } from '@/lib/queries';

const QUICK_START_TEMPLATES = [
  {
    label: 'Signup',
    goal: 'Create a new account using the signup flow and confirm the account was created successfully.',
  },
  {
    label: 'Login',
    goal: 'Log in with valid credentials and confirm you land on the authenticated dashboard or home page.',
  },
  {
    label: 'Checkout',
    goal: 'Add an item to the cart and complete checkout through to order confirmation.',
  },
  {
    label: 'Password reset',
    goal: 'Request a password reset, follow the reset flow, and confirm the password was changed.',
  },
] as const;

const PERSONAS = [
  { value: 'confused_first_time_user', label: 'Confused First-Time User' },
  { value: 'impatient_user', label: 'Impatient User' },
  { value: 'careful_user', label: 'Careful User' },
] as const;

const DEVICES = ['iPhone 13', 'Pixel 5', 'Desktop Chrome'] as const;
const NETWORKS = ['4g', '3g', 'slow3g'] as const;
const MAX_PAGES_OPTIONS = [5, 10, 20, 30] as const;

const POLL_INTERVAL_MS = 2500;

type RunStatus = 'queued' | 'running' | 'completed' | 'failed';

interface RunStatusResponse {
  run_id: string;
  status: RunStatus;
  outcome?: string | null;
  diagnosis?: {
    rootCause?: string | null;
    severity?: string | null;
    likelyOwner?: string | null;
    suggestedFix?: string | null;
  } | null;
  supabase_url?: string | null;
  error?: string | null;
}

const STATUS_STEPS: { key: RunStatus; label: string }[] = [
  { key: 'queued', label: 'Queued' },
  { key: 'running', label: 'Running' },
  { key: 'completed', label: 'Done' },
];

/** Shared queued/running/completed/failed stepper, used by both modes below. */
function StatusStepper({ status }: { status: RunStatus }) {
  const currentStepIndex = STATUS_STEPS.findIndex((s) => s.key === status);
  return (
    <>
      <div className="flex items-center gap-2">
        {STATUS_STEPS.map((step, i) => {
          const reached = currentStepIndex >= i || status === 'failed';
          const isFailedHere = status === 'failed' && i === STATUS_STEPS.length - 1;
          return (
            <div key={step.key} className="flex items-center gap-2 flex-1">
              <motion.div
                initial={false}
                animate={{
                  backgroundColor: isFailedHere
                    ? 'var(--color-chart-critical)'
                    : reached
                    ? 'var(--primary)'
                    : 'var(--muted)',
                }}
                transition={{ duration: 0.4 }}
                className="h-1.5 flex-1 rounded-full"
              />
            </div>
          );
        })}
      </div>
      <div className="flex justify-between text-xs text-muted-foreground -mt-4">
        {STATUS_STEPS.map((step) => (
          <span key={step.key}>{step.label}</span>
        ))}
      </div>
    </>
  );
}

function GoalRunForm() {
  const [url, setUrl] = useState('');
  const [goal, setGoal] = useState('');
  const [persona, setPersona] = useState<string>(PERSONAS[0].value);
  const [device, setDevice] = useState<string>(DEVICES[0]);
  const [network, setNetwork] = useState<string>(NETWORKS[0]);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [run, setRun] = useState<RunStatusResponse | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const elapsedTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearTimers = () => {
    if (pollTimer.current) clearInterval(pollTimer.current);
    if (elapsedTimer.current) clearInterval(elapsedTimer.current);
    pollTimer.current = null;
    elapsedTimer.current = null;
  };

  useEffect(() => clearTimers, []);

  async function pollRun(runId: string) {
    try {
      const res = await fetch(`/api/backend/runs/${runId}`);
      const data: RunStatusResponse = await res.json();
      if (!res.ok) {
        setSubmitError(
          (data as unknown as { error?: string })?.error ?? `Backend returned ${res.status}`
        );
        clearTimers();
        return;
      }
      setRun(data);
      if (data.status === 'completed' || data.status === 'failed') {
        clearTimers();
      }
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Could not reach the backend');
      clearTimers();
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    setRun(null);
    setSubmitting(true);
    setElapsedSeconds(0);

    try {
      const res = await fetch('/api/backend/runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal, url, persona, device, network }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error ?? `Backend returned ${res.status}`);
      }

      const initial: RunStatusResponse = { run_id: data.run_id, status: data.status ?? 'queued' };
      setRun(initial);

      elapsedTimer.current = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
      pollTimer.current = setInterval(() => pollRun(initial.run_id), POLL_INTERVAL_MS);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to start the run');
    } finally {
      setSubmitting(false);
    }
  }

  const isInFlight = run && (run.status === 'queued' || run.status === 'running');

  return (
    <>
      <Card>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="url">Starting URL</Label>
              <Input
                id="url"
                type="url"
                required
                placeholder="https://app.example.com/signup"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="goal">Goal</Label>
                <div className="flex flex-wrap gap-1.5 justify-end">
                  {QUICK_START_TEMPLATES.map((t) => (
                    <button
                      key={t.label}
                      type="button"
                      onClick={() => setGoal(t.goal)}
                      className="text-xs font-medium px-2.5 py-1 rounded-full border border-gold/30 text-gold hover:bg-gold/10 transition-colors"
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>
              <Textarea
                id="goal"
                required
                rows={3}
                placeholder="What should the agent try to accomplish?"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Persona</Label>
                <Select value={persona} onValueChange={setPersona}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PERSONAS.map((p) => (
                      <SelectItem key={p.value} value={p.value}>
                        {p.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Device</Label>
                <Select value={device} onValueChange={setDevice}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DEVICES.map((d) => (
                      <SelectItem key={d} value={d}>
                        {d}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Network</Label>
                <Select value={network} onValueChange={setNetwork}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {NETWORKS.map((n) => (
                      <SelectItem key={n} value={n}>
                        {n}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Button
              type="submit"
              size="lg"
              className="w-full"
              disabled={submitting || Boolean(isInFlight)}
            >
              {submitting ? (
                <>
                  <Loader2 className="animate-spin" data-icon="inline-start" />
                  Starting run…
                </>
              ) : (
                'Run'
              )}
            </Button>

            {submitError && (
              <p className="text-sm text-critical">{submitError}</p>
            )}
          </form>
        </CardContent>
      </Card>

      <AnimatePresence>
        {run && (
          <motion.div
            key="progress"
            initial={{ opacity: 0, y: 20, height: 0 }}
            animate={{ opacity: 1, y: 0, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.4, ease: [0.33, 1, 0.68, 1] }}
            className="mt-8"
          >
            <Card>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {run.status === 'completed' ? (
                      <CheckCircle2 className="text-chart-good size-5" />
                    ) : run.status === 'failed' ? (
                      <XCircle className="text-chart-critical size-5" />
                    ) : (
                      <motion.span
                        animate={{ scale: [1, 1.25, 1], opacity: [1, 0.6, 1] }}
                        transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
                        className="size-2.5 rounded-full bg-primary inline-block"
                      />
                    )}
                    <span className="font-display font-semibold text-foreground">
                      Run {run.run_id}
                    </span>
                  </div>
                  <span className="text-sm text-muted-foreground font-mono">{elapsedSeconds}s</span>
                </div>

                <StatusStepper status={run.status} />

                {run.status === 'completed' && (
                  <div className="flex items-center justify-between rounded-lg bg-muted/50 px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">Outcome:</span>
                      <Badge variant={run.outcome === 'success' ? 'default' : 'destructive'}>
                        {run.outcome ?? 'unknown'}
                      </Badge>
                    </div>
                    <Button asChild variant="secondary" size="sm">
                      <Link href={`/dashboard/runs/${run.run_id}`}>
                        View details
                        <ArrowRight data-icon="inline-end" />
                      </Link>
                    </Button>
                  </div>
                )}

                {run.status === 'failed' && (
                  <div className="rounded-lg bg-critical/10 px-4 py-3 text-sm text-critical">
                    {run.error ?? 'The run failed.'}
                  </div>
                )}

                {run.diagnosis?.rootCause && (
                  <div className="rounded-lg border border-foreground/10 px-4 py-3 text-sm">
                    <p className="font-semibold text-foreground mb-1">
                      Diagnosis {run.diagnosis.severity ? `(${run.diagnosis.severity})` : ''}
                    </p>
                    <p className="text-muted-foreground">{run.diagnosis.rootCause}</p>
                    {run.diagnosis.suggestedFix && (
                      <p className="text-muted-foreground mt-1">Suggested fix: {run.diagnosis.suggestedFix}</p>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

function AuditForm() {
  const router = useRouter();
  const [url, setUrl] = useState('');
  const [persona, setPersona] = useState<string>('');

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [audit, setAudit] = useState<AuditStatusResponse | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const elapsedTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearTimers = () => {
    if (pollTimer.current) clearInterval(pollTimer.current);
    if (elapsedTimer.current) clearInterval(elapsedTimer.current);
    pollTimer.current = null;
    elapsedTimer.current = null;
  };

  useEffect(() => clearTimers, []);

  async function pollAudit(auditId: string) {
    try {
      const res = await fetch(`/api/backend/audits/${auditId}`);
      const data: AuditStatusResponse = await res.json();
      if (!res.ok) {
        setSubmitError(
          (data as unknown as { error?: string })?.error ?? `Backend returned ${res.status}`
        );
        clearTimers();
        return;
      }
      setAudit(data);
      if (data.status === 'completed') {
        clearTimers();
        router.push(`/dashboard/audits/${auditId}`);
        return;
      }
      if (data.status === 'failed') {
        clearTimers();
      }
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Could not reach the backend');
      clearTimers();
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    setAudit(null);
    setSubmitting(true);
    setElapsedSeconds(0);

    try {
      const res = await fetch('/api/backend/audits', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, persona: persona || undefined }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error ?? `Backend returned ${res.status}`);
      }

      const initial: AuditStatusResponse = { audit_id: data.audit_id, status: data.status ?? 'queued' };
      setAudit(initial);

      elapsedTimer.current = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
      pollTimer.current = setInterval(() => pollAudit(initial.audit_id), POLL_INTERVAL_MS);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to start the audit');
    } finally {
      setSubmitting(false);
    }
  }

  const isInFlight = audit && (audit.status === 'queued' || audit.status === 'running');

  return (
    <>
      <Card>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="audit-url">Landing page URL</Label>
              <Input
                id="audit-url"
                type="url"
                required
                placeholder="https://example.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
              <p className="text-sm text-muted-foreground">
                Sniff will browse the page as a first-time visitor and score it across
                message clarity, audience fit, action path, trust, and content depth.
              </p>
            </div>

            <div className="space-y-2 sm:w-1/3">
              <Label>Persona (optional)</Label>
              <Select value={persona} onValueChange={setPersona}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Confused First-Time User (default)" />
                </SelectTrigger>
                <SelectContent>
                  {PERSONAS.map((p) => (
                    <SelectItem key={p.value} value={p.value}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Button
              type="submit"
              size="lg"
              className="w-full"
              disabled={submitting || Boolean(isInFlight)}
            >
              {submitting ? (
                <>
                  <Loader2 className="animate-spin" data-icon="inline-start" />
                  Starting audit…
                </>
              ) : (
                'Run Audit'
              )}
            </Button>

            {submitError && (
              <p className="text-sm text-critical">{submitError}</p>
            )}
          </form>
        </CardContent>
      </Card>

      <AnimatePresence>
        {audit && (
          <motion.div
            key="audit-progress"
            initial={{ opacity: 0, y: 20, height: 0 }}
            animate={{ opacity: 1, y: 0, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.4, ease: [0.33, 1, 0.68, 1] }}
            className="mt-8"
          >
            <Card>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {audit.status === 'completed' ? (
                      <CheckCircle2 className="text-chart-good size-5" />
                    ) : audit.status === 'failed' ? (
                      <XCircle className="text-chart-critical size-5" />
                    ) : (
                      <motion.span
                        animate={{ scale: [1, 1.25, 1], opacity: [1, 0.6, 1] }}
                        transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
                        className="size-2.5 rounded-full bg-primary inline-block"
                      />
                    )}
                    <span className="font-display font-semibold text-foreground">
                      Audit {audit.audit_id}
                    </span>
                  </div>
                  <span className="text-sm text-muted-foreground font-mono">{elapsedSeconds}s</span>
                </div>

                <StatusStepper status={audit.status} />

                {audit.status === 'completed' && (
                  <div className="flex items-center justify-between rounded-lg bg-muted/50 px-4 py-3">
                    <span className="text-sm text-muted-foreground">Report ready - redirecting…</span>
                    <Button asChild variant="secondary" size="sm">
                      <Link href={`/dashboard/audits/${audit.audit_id}`}>
                        View report
                        <ArrowRight data-icon="inline-end" />
                      </Link>
                    </Button>
                  </div>
                )}

                {audit.status === 'failed' && (
                  <div className="rounded-lg bg-critical/10 px-4 py-3 text-sm text-critical">
                    {audit.error ?? 'The audit failed.'}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

type LoginMode = 'credentials' | 'session';

/** Compact "last few site audits" list - lives here rather than on the main
 * dashboard so that page's diff stays limited to its one new nav button. */
function RecentSiteAudits() {
  const [audits, setAudits] = useState<Awaited<ReturnType<typeof getRecentSiteAudits>>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRecentSiteAudits(5)
      .then(setAudits)
      .catch((err) => console.error('Error fetching recent site audits:', err))
      .finally(() => setLoading(false));
  }, []);

  if (loading || audits.length === 0) return null;

  return (
    <div className="mt-8">
      <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground mb-3">Recent site audits</p>
      <div className="space-y-2">
        {audits.map((a) => (
          <Link key={a.site_audit_id} href={`/dashboard/site-audits/${a.site_audit_id}`} className="block">
            <Card className="transition-colors hover:ring-primary/40">
              <CardContent className="flex items-center justify-between gap-4 py-3">
                <span className="text-sm font-mono text-foreground truncate">{a.seed_url}</span>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-xs text-muted-foreground">
                    {a.pages_audited}/{a.max_pages} pages
                  </span>
                  <Badge variant={a.status === 'completed' ? 'default' : a.status === 'failed' ? 'destructive' : 'secondary'}>
                    {a.status}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}

function SiteAuditForm() {
  const router = useRouter();
  const [seedUrl, setSeedUrl] = useState('');
  const [persona, setPersona] = useState<string>('');
  const [maxPages, setMaxPages] = useState<string>('10');

  const [showLogin, setShowLogin] = useState(false);
  const [loginMode, setLoginMode] = useState<LoginMode>('credentials');
  const [loginUrl, setLoginUrl] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [sessionJson, setSessionJson] = useState('');
  const [sessionJsonError, setSessionJsonError] = useState<string | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [siteAudit, setSiteAudit] = useState<SiteAuditStatusResponse | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const elapsedTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearTimers = () => {
    if (pollTimer.current) clearInterval(pollTimer.current);
    if (elapsedTimer.current) clearInterval(elapsedTimer.current);
    pollTimer.current = null;
    elapsedTimer.current = null;
  };

  useEffect(() => clearTimers, []);

  async function pollSiteAudit(siteAuditId: string) {
    try {
      const res = await fetch(`/api/backend/site-audits/${siteAuditId}`);
      const data: SiteAuditStatusResponse = await res.json();
      if (!res.ok) {
        setSubmitError(
          (data as unknown as { error?: string })?.error ?? `Backend returned ${res.status}`
        );
        clearTimers();
        return;
      }
      setSiteAudit(data);
      if (data.status === 'completed') {
        clearTimers();
        router.push(`/dashboard/site-audits/${siteAuditId}`);
        return;
      }
      if (data.status === 'failed') {
        clearTimers();
      }
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Could not reach the backend');
      clearTimers();
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    setSessionJsonError(null);
    setSiteAudit(null);

    let storageState: object | undefined;
    if (showLogin && loginMode === 'session' && sessionJson.trim()) {
      try {
        storageState = JSON.parse(sessionJson);
      } catch {
        setSessionJsonError("That doesn't look like valid JSON.");
        return;
      }
    }

    setSubmitting(true);
    setElapsedSeconds(0);

    try {
      const body: Record<string, unknown> = {
        seed_url: seedUrl,
        persona: persona || undefined,
        max_pages: Number(maxPages),
      };
      if (showLogin && loginMode === 'credentials' && loginUrl && username && password) {
        body.login = { url: loginUrl, username, password };
      }
      if (storageState) {
        body.storage_state = storageState;
      }

      const res = await fetch('/api/backend/site-audits', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error ?? `Backend returned ${res.status}`);
      }

      const initial: SiteAuditStatusResponse = {
        site_audit_id: data.site_audit_id,
        status: data.status ?? 'queued',
        seed_url: seedUrl,
        max_pages: Number(maxPages),
        pages_discovered: 0,
        pages_audited: 0,
        manifest: {},
        pages: [],
        error: null,
      };
      setSiteAudit(initial);

      elapsedTimer.current = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
      pollTimer.current = setInterval(() => pollSiteAudit(initial.site_audit_id), POLL_INTERVAL_MS);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to start the site audit');
    } finally {
      setSubmitting(false);
    }
  }

  const isInFlight = siteAudit && (siteAudit.status === 'queued' || siteAudit.status === 'running');

  return (
    <>
      <Card>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="site-audit-url">Seed URL</Label>
              <Input
                id="site-audit-url"
                type="url"
                required
                placeholder="https://example.com"
                value={seedUrl}
                onChange={(e) => setSeedUrl(e.target.value)}
              />
              <p className="text-sm text-muted-foreground">
                Sniff will crawl same-origin links and sitemap.xml from here, then run the same
                per-page audit used above on each page it finds.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Persona (optional)</Label>
                <Select value={persona} onValueChange={setPersona}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Confused First-Time User (default)" />
                  </SelectTrigger>
                  <SelectContent>
                    {PERSONAS.map((p) => (
                      <SelectItem key={p.value} value={p.value}>
                        {p.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Max pages</Label>
                <Select value={maxPages} onValueChange={setMaxPages}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MAX_PAGES_OPTIONS.map((n) => (
                      <SelectItem key={n} value={String(n)}>
                        {n} pages
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="rounded-lg border border-foreground/10">
              <button
                type="button"
                onClick={() => setShowLogin((v) => !v)}
                className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-foreground"
              >
                Login (optional)
                <span className="text-muted-foreground">{showLogin ? '−' : '+'}</span>
              </button>

              {showLogin && (
                <div className="px-4 pb-4 space-y-4 border-t border-foreground/10 pt-4">
                  <Caption>
                    Use a dedicated test/staging account, not your real login. Your password is
                    used once to sign in and is never stored.
                  </Caption>

                  <div className="flex gap-1.5">
                    <button
                      type="button"
                      onClick={() => setLoginMode('credentials')}
                      className={`text-xs font-medium px-2.5 py-1 rounded-full border transition-colors ${
                        loginMode === 'credentials'
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-foreground/15 text-muted-foreground hover:bg-muted'
                      }`}
                    >
                      Username & password
                    </button>
                    <button
                      type="button"
                      onClick={() => setLoginMode('session')}
                      className={`text-xs font-medium px-2.5 py-1 rounded-full border transition-colors ${
                        loginMode === 'session'
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-foreground/15 text-muted-foreground hover:bg-muted'
                      }`}
                    >
                      Paste an existing session
                    </button>
                  </div>

                  {loginMode === 'credentials' ? (
                    <div className="space-y-3">
                      <div className="space-y-2">
                        <Label htmlFor="login-url">Login page URL</Label>
                        <Input
                          id="login-url"
                          type="url"
                          placeholder="https://example.com/login"
                          value={loginUrl}
                          onChange={(e) => setLoginUrl(e.target.value)}
                        />
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div className="space-y-2">
                          <Label htmlFor="login-username">Username</Label>
                          <Input
                            id="login-username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="login-password">Password</Label>
                          <Input
                            id="login-password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                          />
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <Label htmlFor="login-session">Session (storage_state JSON)</Label>
                      <Textarea
                        id="login-session"
                        rows={5}
                        placeholder='{"cookies": [...], "origins": [...]}'
                        value={sessionJson}
                        onChange={(e) => {
                          setSessionJson(e.target.value);
                          setSessionJsonError(null);
                        }}
                        className="font-mono text-xs"
                      />
                      {sessionJsonError && <p className="text-sm text-critical">{sessionJsonError}</p>}
                    </div>
                  )}
                </div>
              )}
            </div>

            <Button
              type="submit"
              size="lg"
              className="w-full"
              disabled={submitting || Boolean(isInFlight)}
            >
              {submitting ? (
                <>
                  <Loader2 className="animate-spin" data-icon="inline-start" />
                  Starting site audit…
                </>
              ) : (
                'Start Site Audit'
              )}
            </Button>

            {submitError && (
              <p className="text-sm text-critical">{submitError}</p>
            )}
          </form>
        </CardContent>
      </Card>

      <AnimatePresence>
        {siteAudit && (
          <motion.div
            key="site-audit-progress"
            initial={{ opacity: 0, y: 20, height: 0 }}
            animate={{ opacity: 1, y: 0, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.4, ease: [0.33, 1, 0.68, 1] }}
            className="mt-8"
          >
            <Card>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {siteAudit.status === 'completed' ? (
                      <CheckCircle2 className="text-chart-good size-5" />
                    ) : siteAudit.status === 'failed' ? (
                      <XCircle className="text-chart-critical size-5" />
                    ) : (
                      <motion.span
                        animate={{ scale: [1, 1.25, 1], opacity: [1, 0.6, 1] }}
                        transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
                        className="size-2.5 rounded-full bg-primary inline-block"
                      />
                    )}
                    <span className="font-display font-semibold text-foreground">
                      Site Audit {siteAudit.site_audit_id}
                    </span>
                  </div>
                  <span className="text-sm text-muted-foreground font-mono">{elapsedSeconds}s</span>
                </div>

                <StatusStepper status={siteAudit.status} />

                {isInFlight && (
                  <p className="text-sm text-muted-foreground">
                    Auditing page {siteAudit.pages_audited} of up to {siteAudit.max_pages}…
                  </p>
                )}

                {siteAudit.status === 'completed' && (
                  <div className="flex items-center justify-between rounded-lg bg-muted/50 px-4 py-3">
                    <span className="text-sm text-muted-foreground">Report ready - redirecting…</span>
                    <Button asChild variant="secondary" size="sm">
                      <Link href={`/dashboard/site-audits/${siteAudit.site_audit_id}`}>
                        View report
                        <ArrowRight data-icon="inline-end" />
                      </Link>
                    </Button>
                  </div>
                )}

                {siteAudit.status === 'failed' && (
                  <div className="rounded-lg bg-critical/10 px-4 py-3 text-sm text-critical">
                    {siteAudit.error ?? 'The site audit failed.'}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      <RecentSiteAudits />
    </>
  );
}

export default function NewRunPage() {
  // Plain window.location read on mount rather than useSearchParams(), which
  // would force this page into a Suspense boundary just to support the
  // `?mode=audit`/`?mode=site-audit` deep links from the dashboard's nav buttons.
  const [defaultTab, setDefaultTab] = useState<'goal' | 'audit' | 'site-audit'>('goal');
  // One-time read of a browser API (the URL) unavailable during SSR/first
  // render, not state derived from props/state that could be computed inline.
  useEffect(() => {
    const mode = new URLSearchParams(window.location.search).get('mode');
    if (mode === 'audit' || mode === 'site-audit') {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDefaultTab(mode);
    }
  }, []);

  return (
    <main className="min-h-screen py-32 bg-background">
      <ContainerNarrow>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
          className="mb-10"
        >
          <Link
            href="/dashboard"
            className="text-sm text-muted-foreground hover:text-primary transition-colors mb-4 inline-block"
          >
            ← Back to Dashboard
          </Link>
          <Display2 as="h1" className="text-foreground mb-3">New Test Run</Display2>
          <Body className="text-lg text-muted-foreground">
            Trigger a persona-driven test run against a live URL and watch it work.
          </Body>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1, ease: [0.33, 1, 0.68, 1] }}
        >
          <Tabs key={defaultTab} defaultValue={defaultTab}>
            <TabsList className="mb-6">
              <TabsTrigger value="goal">Test a Goal</TabsTrigger>
              <TabsTrigger value="audit">Single Page Audit</TabsTrigger>
              <TabsTrigger value="site-audit">Full Site Audit</TabsTrigger>
            </TabsList>
            <TabsContent value="goal">
              <GoalRunForm />
            </TabsContent>
            <TabsContent value="audit">
              <AuditForm />
            </TabsContent>
            <TabsContent value="site-audit">
              <SiteAuditForm />
            </TabsContent>
          </Tabs>
        </motion.div>
      </ContainerNarrow>
    </main>
  );
}
