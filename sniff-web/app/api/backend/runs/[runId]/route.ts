import { backendFetch } from "@/lib/backend";

// Proxies GET /runs/{run_id} to the FastAPI backend server-side. The client
// polls this same-origin route while a run is queued/running.
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ runId: string }> }
) {
  const { runId } = await params;
  return backendFetch(`/runs/${encodeURIComponent(runId)}`, { method: "GET" });
}
