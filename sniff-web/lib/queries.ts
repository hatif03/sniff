import type { SiteAuditManifestEntry, SiteAuditStatusResponse } from './site-audits';
import { supabase } from './supabase';

export async function getRunDetails(runId: string) {
  // Fetch from run_summaries instead of RPC function
  const { data, error } = await supabase
    .from('run_summaries')
    .select('*')
    .eq('run_id', runId)
    .single();

  if (error) throw error;
  return data;
}

export async function getRecentRuns(limit = 10) {
  const { data, error } = await supabase
    .from('run_summaries')
    .select('*')
    .neq('outcome', 'failure')
    .order('created_at', { ascending: false })
    .limit(limit);

  if (error) throw error;
  return data;
}

export async function getRecentAudits(limit = 10) {
  const { data, error } = await supabase
    .from('audits')
    .select('audit_id, url, persona, overall_score, label, verdict, created_at')
    .is('site_audit_id', null)
    .order('created_at', { ascending: false })
    .limit(limit);

  if (error) throw error;
  return data;
}

export async function getRecentSiteAudits(limit = 10) {
  const { data, error } = await supabase
    .from('site_audits')
    .select('site_audit_id, seed_url, status, max_pages, pages_discovered, pages_audited, created_at')
    .order('created_at', { ascending: false })
    .limit(limit);

  if (error) throw error;
  return data || [];
}

/** Standalone page audits + whole-site crawls for the dashboard feed (one row per job). */
export type DashboardAuditFeedItem =
  | {
      kind: 'page';
      audit_id: string;
      url: string;
      overall_score: number | null;
      label: string | null;
      created_at: string;
    }
  | {
      kind: 'site';
      site_audit_id: string;
      seed_url: string;
      status: string;
      pages_audited: number;
      created_at: string;
    };

export async function getDashboardAuditFeed(limit = 12): Promise<DashboardAuditFeedItem[]> {
  const [pages, sites] = await Promise.all([getRecentAudits(limit), getRecentSiteAudits(limit)]);
  const items: DashboardAuditFeedItem[] = [
    ...(pages ?? []).map((p) => ({
      kind: 'page' as const,
      audit_id: p.audit_id,
      url: p.url,
      overall_score: p.overall_score,
      label: p.label,
      created_at: p.created_at,
    })),
    ...(sites ?? []).map((s) => ({
      kind: 'site' as const,
      site_audit_id: s.site_audit_id,
      seed_url: s.seed_url,
      status: s.status,
      pages_audited: s.pages_audited,
      created_at: s.created_at,
    })),
  ];
  return items
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, limit);
}

export async function getPersonaMetrics() {
  const { data, error } = await supabase
    .from('persona_metrics')
    .select('*');

  if (error) throw error;
  return data;
}

export async function getObservations(runId: string) {
  const { data, error } = await supabase
    .from('observations')
    .select('step, url, screenshot_url, timestamp')
    .eq('run_id', runId)
    .order('step');

  if (error) throw error;
  return data || [];
}

export async function getActions(runId: string) {
  const { data, error } = await supabase
    .from('actions')
    .select('step, action, target, success, duration_ms')
    .eq('run_id', runId)
    .order('step');

  if (error) throw error;
  return data || [];
}

export async function getAgentReasoning(runId: string) {
  const { data, error } = await supabase
    .from('agent_reasoning')
    .select('*')
    .eq('run_id', runId)
    .order('step');

  if (error) throw error;
  return data || [];
}

export async function getPersonaReview(runId: string) {
  const { data, error } = await supabase
    .from('persona_reviews')
    .select('*')
    .eq('run_id', runId)
    .single();

  if (error) throw error;
  return data;
}

export async function getFrictionAnalytics() {
  const { data, error} = await supabase
    .from('friction_analytics')
    .select('*')
    .order('occurrence_count', { ascending: false })
    .limit(20);

  if (error) throw error;
  return data || [];
}

export async function getAgentConfidenceMetrics(runId: string) {
  const { data, error } = await supabase
    .from('agent_confidence_metrics')
    .select('*')
    .eq('run_id', runId)
    .single();

  // No matching row (e.g. a run with zero agent_reasoning entries) isn't an
  // error worth throwing on - the caller should just render nothing.
  if (error && error.code !== 'PGRST116') throw error;
  return data || null;
}

/**
 * Run outcome + root-cause history for the "Trends" tab. `run_summaries`
 * already joins runs+diagnoses+persona_reviews in one row (root_cause,
 * outcome, created_at together), so both the outcome-rate-over-time and
 * root-cause-distribution-over-time charts bucket this same result client
 * side - no bespoke SQL view needed at today's data volume.
 */
export async function getRunTrendHistory(limit = 500) {
  const { data, error } = await supabase
    .from('run_summaries')
    .select('run_id, outcome, root_cause, persona_name, created_at')
    .order('created_at', { ascending: true })
    .limit(limit);

  if (error) throw error;
  return data || [];
}

/**
 * Audit score + Core Web Vitals history for the "Trends" tab's per-URL
 * score chart. Returns every audit (not just the most recent), across all
 * URLs - the caller groups by `url` client side to build the URL picker.
 */
export async function getAuditTrendHistory(limit = 500) {
  const { data, error } = await supabase
    .from('audits')
    .select('audit_id, url, overall_score, lcp, fcp, cls, created_at')
    .order('created_at', { ascending: true })
    .limit(limit);

  if (error) throw error;
  return data || [];
}

/** Supabase fallback when the in-process API no longer has this site audit (post-redeploy). */
export async function getSiteAuditDetailFromSupabase(
  siteAuditId: string
): Promise<SiteAuditStatusResponse | null> {
  const { data: row, error } = await supabase
    .from('site_audits')
    .select('*')
    .eq('site_audit_id', siteAuditId)
    .maybeSingle();

  if (error) throw error;
  if (!row) return null;

  const { data: pageRows, error: pagesError } = await supabase
    .from('audits')
    .select('audit_id, url, overall_score, label')
    .eq('site_audit_id', siteAuditId)
    .order('created_at');

  if (pagesError) throw pagesError;

  const manifest = (row.manifest ?? {}) as Record<string, SiteAuditManifestEntry>;
  const pages = (pageRows ?? []).map((p) => ({
    audit_id: p.audit_id,
    url: p.url,
    overall_score: p.overall_score,
    label: p.label,
  }));

  return {
    site_audit_id: row.site_audit_id,
    status: row.status,
    seed_url: row.seed_url,
    max_pages: row.max_pages,
    pages_discovered: row.pages_discovered ?? Object.keys(manifest).length,
    pages_audited: row.pages_audited ?? pages.length,
    manifest,
    pages,
    error: row.error,
  };
}
