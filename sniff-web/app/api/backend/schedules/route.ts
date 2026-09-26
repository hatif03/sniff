import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

// Proxies POST /schedules (create) and GET /schedules (list) to the FastAPI
// backend server-side, so the shared bearer token never reaches the browser.
export async function POST(req: NextRequest) {
  const body = await req.json();
  return backendFetch("/schedules", { method: "POST", body: JSON.stringify(body) });
}

export async function GET() {
  return backendFetch("/schedules", { method: "GET" });
}

export async function DELETE() {
  return NextResponse.json({ error: "Method not allowed" }, { status: 405 });
}
