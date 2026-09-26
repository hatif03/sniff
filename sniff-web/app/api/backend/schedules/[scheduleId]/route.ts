import { backendFetch } from "@/lib/backend";

// Proxies PATCH/DELETE /schedules/{schedule_id} to the FastAPI backend
// server-side, so the shared bearer token never reaches the browser.
export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ scheduleId: string }> }
) {
  const { scheduleId } = await params;
  const body = await req.json();
  return backendFetch(`/schedules/${encodeURIComponent(scheduleId)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ scheduleId: string }> }
) {
  const { scheduleId } = await params;
  return backendFetch(`/schedules/${encodeURIComponent(scheduleId)}`, { method: "DELETE" });
}
