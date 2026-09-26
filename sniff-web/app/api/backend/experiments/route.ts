import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

// Proxies POST /experiments to the FastAPI backend server-side.
// Body: {goal, url, personas: string[], parallel?: boolean}.
export async function POST(req: Request) {
  const body = await req.json();
  return backendFetch("/experiments", { method: "POST", body: JSON.stringify(body) });
}

export async function GET() {
  return NextResponse.json({ error: "Method not allowed" }, { status: 405 });
}
