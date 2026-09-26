import { NextResponse } from "next/server";

/**
 * Server-only proxy to the Sniff FastAPI backend (src/api/main.py).
 *
 * BACKEND_URL and SNIFF_API_TOKEN are read here, not NEXT_PUBLIC_-prefixed,
 * so they're never bundled into client JS. Only Next.js Route Handlers
 * (app/api/backend/**) call this - the browser only ever talks to those
 * same-origin routes, with no Authorization header of its own.
 */
export async function backendFetch(
  path: string,
  init: { method: "GET" | "POST"; body?: string }
): Promise<NextResponse> {
  const baseUrl = process.env.BACKEND_URL;
  const token = process.env.SNIFF_API_TOKEN;

  if (!baseUrl) {
    return NextResponse.json(
      { error: "BACKEND_URL is not configured on the server" },
      { status: 503 }
    );
  }

  try {
    const res = await fetch(`${baseUrl}${path}`, {
      method: init.method,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: init.body,
      // Never cache a run/experiment trigger or status poll.
      cache: "no-store",
    });

    const data = await res.json().catch(() => null);
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json(
      { error: `Could not reach backend: ${error instanceof Error ? error.message : "unknown error"}` },
      { status: 502 }
    );
  }
}
