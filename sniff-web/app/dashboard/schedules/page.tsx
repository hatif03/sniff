"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Loader2, CheckCircle2, Trash2 } from 'lucide-react';
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
import { Container } from '@/components/ui/container';
import { Display2, Heading3, Body } from '@/components/ui/typography';

// Same quick-fill goal templates and persona/device/network options as
// app/dashboard/new-run/page.tsx - a schedule is that form plus a name/interval.
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

const INTERVAL_PRESETS = [
  { value: 5, label: 'Every 5 minutes' },
  { value: 15, label: 'Every 15 minutes' },
  { value: 30, label: 'Every 30 minutes' },
  { value: 60, label: 'Every hour' },
  { value: 360, label: 'Every 6 hours' },
  { value: 1440, label: 'Every 24 hours' },
] as const;

type Mode = 'run' | 'audit';

interface Schedule {
  schedule_id: string;
  name: string;
  mode: Mode;
  url: string;
  goal?: string | null;
  persona?: string | null;
  device?: string | null;
  network?: string | null;
  interval_minutes: number;
  enabled: boolean;
  next_run_at?: string | null;
  last_run_id?: string | null;
  last_triggered_at?: string | null;
}

/** "30" -> "every 30 minutes", "60" -> "every hour", "1440" -> "every 24 hours". */
function formatInterval(minutes: number): string {
  const preset = INTERVAL_PRESETS.find((p) => p.value === minutes);
  if (preset) return preset.label.replace(/^Every/, 'every');
  if (minutes % 60 === 0) return `every ${minutes / 60} hours`;
  return `every ${minutes} minutes`;
}

function formatTimestamp(value?: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString();
}

function ScheduleForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState('');
  const [mode, setMode] = useState<Mode>('run');
  const [url, setUrl] = useState('');
  const [goal, setGoal] = useState('');
  const [persona, setPersona] = useState<string>(PERSONAS[0].value);
  const [device, setDevice] = useState<string>(DEVICES[0]);
  const [network, setNetwork] = useState<string>(NETWORKS[0]);
  const [intervalMinutes, setIntervalMinutes] = useState<number>(30);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    setSubmitted(false);
    setSubmitting(true);

    try {
      const res = await fetch('/api/backend/schedules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          mode,
          url,
          goal: mode === 'run' ? goal : undefined,
          persona,
          device,
          network,
          interval_minutes: intervalMinutes,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error ?? `Backend returned ${res.status}`);
      }

      setSubmitted(true);
      setName('');
      setUrl('');
      setGoal('');
      onCreated();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to create the schedule');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="schedule-name">Schedule name</Label>
            <Input
              id="schedule-name"
              required
              placeholder="Nightly checkout check"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <Tabs value={mode} onValueChange={(v) => setMode(v as Mode)}>
            <TabsList className="mb-2">
              <TabsTrigger value="run">Test a Goal</TabsTrigger>
              <TabsTrigger value="audit">Full Site Audit</TabsTrigger>
            </TabsList>
          </Tabs>

          <div className="space-y-2">
            <Label htmlFor="schedule-url">
              {mode === 'run' ? 'Starting URL' : 'Landing page URL'}
            </Label>
            <Input
              id="schedule-url"
              type="url"
              required
              placeholder="https://app.example.com/signup"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </div>

          {mode === 'run' && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="schedule-goal">Goal</Label>
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
                id="schedule-goal"
                required
                rows={3}
                placeholder="What should the agent try to accomplish?"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
              />
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
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

            <div className="space-y-2">
              <Label>Repeats</Label>
              <Select
                value={String(intervalMinutes)}
                onValueChange={(v) => setIntervalMinutes(Number(v))}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {INTERVAL_PRESETS.map((p) => (
                    <SelectItem key={p.value} value={String(p.value)}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button type="submit" size="lg" className="w-full" disabled={submitting}>
            {submitting ? (
              <>
                <Loader2 className="animate-spin" data-icon="inline-start" />
                Creating schedule…
              </>
            ) : (
              'Create Schedule'
            )}
          </Button>

          {submitted && (
            <div className="flex items-center gap-2 text-sm text-chart-good">
              <CheckCircle2 className="size-4" />
              Schedule created.
            </div>
          )}
          {submitError && <p className="text-sm text-critical">{submitError}</p>}
        </form>
      </CardContent>
    </Card>
  );
}

function ScheduleCard({
  schedule,
  onChanged,
}: {
  schedule: Schedule;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);

  async function toggleEnabled() {
    setBusy(true);
    try {
      await fetch(`/api/backend/schedules/${schedule.schedule_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !schedule.enabled }),
      });
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    // ponytail: window.confirm, not a custom AlertDialog primitive - no
    // confirm-dialog pattern exists yet in this codebase to reuse for this
    // one destructive action.
    if (!window.confirm(`Delete schedule "${schedule.name}"? This cannot be undone.`)) return;
    setBusy(true);
    try {
      await fetch(`/api/backend/schedules/${schedule.schedule_id}`, { method: 'DELETE' });
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  const nextRun = formatTimestamp(schedule.next_run_at);
  const lastTriggered = formatTimestamp(schedule.last_triggered_at);

  return (
    <Card>
      <CardContent>
        <div className="flex justify-between items-start mb-3 gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <Heading3 className="text-foreground">{schedule.name}</Heading3>
              <Badge variant="secondary" className="uppercase">{schedule.mode}</Badge>
              <Badge variant={schedule.enabled ? 'default' : 'outline'}>
                {schedule.enabled ? 'Enabled' : 'Disabled'}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground truncate">{schedule.url}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground mb-4">
          <span>{formatInterval(schedule.interval_minutes)}</span>
          {nextRun && (
            <>
              <span>•</span>
              <span>Next run: {nextRun}</span>
            </>
          )}
          {lastTriggered && (
            <>
              <span>•</span>
              <span>Last triggered: {lastTriggered}</span>
            </>
          )}
        </div>

        <div className="flex gap-2">
          <Button variant="secondary" size="sm" disabled={busy} onClick={toggleEnabled}>
            {schedule.enabled ? 'Disable' : 'Enable'}
          </Button>
          <Button variant="destructive" size="sm" disabled={busy} onClick={handleDelete}>
            <Trash2 data-icon="inline-start" />
            Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function ScheduleList({
  schedules,
  loading,
  onChanged,
}: {
  schedules: Schedule[];
  loading: boolean;
  onChanged: () => void;
}) {
  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2].map((i) => (
          <div
            key={`skeleton-${i}`}
            className="animate-pulse bg-card rounded-xl h-28 ring-1 ring-foreground/10"
          />
        ))}
      </div>
    );
  }

  if (schedules.length === 0) {
    return (
      <Card size="sm" className="[--card-spacing:--spacing(12)]">
        <CardContent className="text-center">
          <p className="text-muted-foreground">No schedules yet</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {schedules.map((s) => (
        <ScheduleCard key={s.schedule_id} schedule={s} onChanged={onChanged} />
      ))}
    </div>
  );
}

export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  // Bumped by child components after create/toggle/delete to trigger a refetch,
  // same inline-fetch-in-effect shape as app/dashboard/page.tsx.
  const [reloadKey, setReloadKey] = useState(0);
  const refresh = () => setReloadKey((k) => k + 1);

  useEffect(() => {
    async function fetchSchedules() {
      try {
        const res = await fetch('/api/backend/schedules');
        const data = await res.json();
        setSchedules(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error('Error fetching schedules:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchSchedules();
  }, [reloadKey]);

  return (
    <main className="min-h-screen py-32 bg-background">
      <Container>
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
          <Display2 as="h1" className="text-foreground mb-3">Schedules</Display2>
          <Body className="text-lg text-muted-foreground">
            Set up recurring runs or audits against a URL on a fixed interval.
          </Body>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1, ease: [0.33, 1, 0.68, 1] }}
          className="mb-12"
        >
          <ScheduleForm onCreated={refresh} />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2, ease: [0.33, 1, 0.68, 1] }}
        >
          <h2 className="text-2xl font-display font-bold text-foreground mb-4">Existing schedules</h2>
          <ScheduleList schedules={schedules} loading={loading} onChanged={refresh} />
        </motion.div>
      </Container>
    </main>
  );
}
