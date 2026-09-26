import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

// Proxies POST /audits to the FastAPI backend server-side, so the shared
// bearer token never reaches the browser. Body: {url, persona?}.
export async function POST(req: NextRequest) {
  const body = await req.json();
  return backendFetch("/audits", { method: "POST", body: JSON.stringify(body) });
}

export async function GET() {
  return NextResponse.json({ error: "Method not allowed" }, { status: 405 });
}
