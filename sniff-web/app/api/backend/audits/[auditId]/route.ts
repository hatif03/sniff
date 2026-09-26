import { backendFetch } from "@/lib/backend";

// Proxies GET /audits/{audit_id} to the FastAPI backend server-side. The
// client polls this same-origin route while an audit is queued/running.
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ auditId: string }> }
) {
  const { auditId } = await params;
  return backendFetch(`/audits/${encodeURIComponent(auditId)}`, { method: "GET" });
}
