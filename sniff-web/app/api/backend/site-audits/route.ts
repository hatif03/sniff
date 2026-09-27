import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

// Proxies POST /site-audits to the FastAPI backend server-side, so the
// shared bearer token never reaches the browser. Body: {seed_url, persona?,
// max_pages?, max_depth?, login?, storage_state?}. There's no list-all
// endpoint on the backend (site audits are listed from Supabase directly,
// see lib/queries.ts's getRecentSiteAudits), so GET here is a no-op.
export async function POST(req: NextRequest) {
  const body = await req.json();
  return backendFetch("/site-audits", { method: "POST", body: JSON.stringify(body) });
}

export async function GET() {
  return NextResponse.json({ error: "Method not allowed" }, { status: 405 });
}
