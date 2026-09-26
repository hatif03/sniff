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

export interface CoreWebVitals {
  lcp: number | null;
  fcp: number | null;
  cls: number | null;
}

export interface SeoChecks {
  title: string | null;
  title_length: number | null;
  meta_description: string | null;
  meta_description_length: number | null;
  h1_count: number | null;
  img_alt_count: number | null;
  img_alt_pct: number | null;
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
  core_web_vitals: CoreWebVitals | null;
  seo_checks: SeoChecks | null;
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
