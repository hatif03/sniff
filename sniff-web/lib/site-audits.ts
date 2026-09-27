// Shared types for the whole-site audit feature. Mirrors the snake_case
// shape returned by GET/POST /site-audits on the FastAPI backend (see
// sniff-ai/src/api/main.py + docs/supabase_schema.sql's site_audits table).
// Each per-page report is a normal audit, fetched via the existing
// AuditStatusResponse/GET /audits/{audit_id} - not duplicated here.

export type SiteAuditStatus = "queued" | "running" | "completed" | "failed";

export type SiteAuditManifestStatus = "audited" | "skipped" | "failed";

export interface SiteAuditManifestEntry {
  status: SiteAuditManifestStatus;
  audit_id?: string;
  reason?: string;
  error?: string;
}

export interface SiteAuditPage {
  audit_id: string;
  url: string;
  overall_score: number | null;
  label: string | null;
}

export interface SiteAuditStatusResponse {
  site_audit_id: string;
  status: SiteAuditStatus;
  seed_url: string;
  max_pages: number;
  pages_discovered: number;
  pages_audited: number;
  manifest: Record<string, SiteAuditManifestEntry>;
  pages: SiteAuditPage[];
  error?: string | null;
}
