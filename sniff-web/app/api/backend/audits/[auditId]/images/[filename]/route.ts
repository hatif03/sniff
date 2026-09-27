import { NextResponse } from "next/server";

/**
 * Streams one audit screenshot from the FastAPI backend through to the
 * browser, same server-only BACKEND_URL/SNIFF_API_TOKEN pattern as
 * lib/backend.ts (not reused directly - that helper always returns JSON,
 * this needs to pass binary image bytes through).
 *
 * The backend does have this route (GET /audits/{id}/images/{file}), but it
 * serves the file straight off local disk, keyed by the in-process
 * AUDIT_STORE - both ephemeral, gone after a redeploy/restart/scale event.
 * A new audit's screenshots are Supabase Storage URLs (see auditImageSrc in
 * lib/audits.ts) and never reach this route at all; this path is now only
 * the fallback for an older row that predates that upload, where a 404 here
 * genuinely does mean "gone," not "not wired up yet."
 */
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ auditId: string; filename: string }> }
) {
  const { auditId, filename } = await params;
  const baseUrl = process.env.BACKEND_URL;
  const token = process.env.SNIFF_API_TOKEN;

  if (!baseUrl) {
    return NextResponse.json(
      { error: "BACKEND_URL is not configured on the server" },
      { status: 503 }
    );
  }

  try {
    const res = await fetch(
      `${baseUrl}/audits/${encodeURIComponent(auditId)}/images/${encodeURIComponent(filename)}`,
      {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        cache: "no-store",
      }
    );

    if (!res.ok || !res.body) {
      return NextResponse.json(
        { error: `Backend has no image at this path (status ${res.status})` },
        { status: res.status === 404 ? 404 : 502 }
      );
    }

    return new NextResponse(res.body, {
      status: 200,
      headers: {
        "Content-Type": res.headers.get("content-type") ?? "image/png",
        "Cache-Control": "private, max-age=3600",
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: `Could not reach backend: ${error instanceof Error ? error.message : "unknown error"}` },
      { status: 502 }
    );
  }
}
