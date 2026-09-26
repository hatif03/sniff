// Shared types + helpers for the landing-page audit feature. Mirrors the
// exact snake_case shape of AuditReport from sniff-ai/src/core/audit_models.py
// (pydantic -> JSON), not camelCase.

export type Sentiment = "positive" | "neutral" | "negative";

export interface AuditContext {
  page_type: string;
  primary_goal: string;
  likely_audience: string;
  audience_awareness: string;
  visitor_motivation: string;
  assumptions_to_respect: string[];
}

export interface StoryStep {
  step: string;
  title: string;
  text: string;
  sentiment: Sentiment;
}

export interface DimensionScore {
  dimension: string;
  score: number;
  rationale: string;
}

export interface FindingsBlock {
  score: number;
  findings: string[];
}

export interface StrategicOption {
  path: string;
  risk: string;
  experiment: string;
}

export interface GrowthSection {
  seo: FindingsBlock;
  visual_design: FindingsBlock;
  navigation: FindingsBlock;
  strategic_options: StrategicOption[];
}

export interface ColorUse {
  color: string;
  uses: number;
}

export interface FontUse {
  family: string;
  uses: number;
}

export interface VisualTeaser {
  dominant_colors: ColorUse[];
  font_families: FontUse[];
}

export interface Annotation {
  role: "headline" | "support" | "primary-cta" | "cta";
  text: string;
  color: string;
  label: string;
}

export interface CTATest {
  label: string;
  target_text: string;
  result: string;
}

export interface BrowsingEvidence {
  total_interactive_elements: number;
  safe_cta_candidates: number;
  tested_count: number;
  primary_label: string;
  annotations: Annotation[];
  tests: CTATest[];
}

export interface FixItem {
  issue: string;
  why: string;
  action: string;
}

export interface RewriteItem {
  original: string;
  replacement: string;
}

export interface ImagePaths {
  above_fold: string;
  full_page: string;
  annotated: string;
}

export interface AuditReport {
  overall_score: number;
  label: string;
  verdict: string;
  verdict_summary: string;
  honest_verdict: string;
  context: AuditContext;
  story: StoryStep[];
  scores: DimensionScore[];
  growth: GrowthSection;
  visual_teaser: VisualTeaser;
  strengths: string[];
  decision_gaps: string[];
  jargon_terms: string[];
  browsing_evidence: BrowsingEvidence;
  primary_fix: FixItem;
  next_fixes: FixItem[];
  rewrites: RewriteItem[];
  images: ImagePaths;
  visitor_persona: string;
}

export type AuditStatus = "queued" | "running" | "completed" | "failed";

export interface AuditStatusResponse {
  audit_id: string;
  status: AuditStatus;
  report?: AuditReport | null;
  error?: string | null;
}

/**
 * images.above_fold/full_page/annotated are local filesystem paths on the
 * backend host (e.g. "/tmp/sniff_audits/audit_xxx/annotated.png"). The route
 * handler at app/api/backend/audits/[auditId]/images/[filename]/route.ts only
 * needs the basename - it re-resolves the full path against the backend's
 * own artifacts dir (see that file's GAP comment: the backend doesn't
 * actually expose this yet, so this always 404s upstream today).
 */
export function auditImageSrc(auditId: string, localPath: string): string {
  const filename = localPath.split(/[/\\]/).pop() || localPath;
  return `/api/backend/audits/${encodeURIComponent(auditId)}/images/${encodeURIComponent(filename)}`;
}

// ---- Client-side audit history (localStorage) ----
//
// ponytail: the backend has no GET /audits list-all endpoint (confirmed by
// reading src/api/main.py - only POST /audits and GET /audits/{id} exist),
// so there is no real persisted "all audits" list to page through. This is a
// deliberate workaround, not a real list: it only remembers audit_ids this
// browser has triggered, in localStorage. Replace with a real backend list
// endpoint + query if/when one exists.

const HISTORY_KEY = "sniff_audit_history";
const HISTORY_LIMIT = 20;

export interface AuditHistoryEntry {
  audit_id: string;
  url: string;
  created_at: string;
}

export function getAuditHistory(): AuditHistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function addAuditToHistory(entry: AuditHistoryEntry): void {
  if (typeof window === "undefined") return;
  try {
    const existing = getAuditHistory().filter((e) => e.audit_id !== entry.audit_id);
    const next = [entry, ...existing].slice(0, HISTORY_LIMIT);
    window.localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
  } catch {
    // localStorage unavailable (private mode, quota, etc) - history is
    // best-effort only, never block the audit itself on it.
  }
}
