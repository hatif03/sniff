import { backendFetch } from "@/lib/backend";

// Proxies GET /site-audits/{site_audit_id} to the FastAPI backend
// server-side. The client polls this same-origin route while a site audit
// is queued/running.
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ siteAuditId: string }> }
) {
  const { siteAuditId } = await params;
  return backendFetch(`/site-audits/${encodeURIComponent(siteAuditId)}`, { method: "GET" });
}
