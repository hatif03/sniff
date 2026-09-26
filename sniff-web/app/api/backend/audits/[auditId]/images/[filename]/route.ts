import { NextResponse } from "next/server";

/**
 * Streams one audit screenshot from the FastAPI backend through to the
 * browser, same server-only BACKEND_URL/SNIFF_API_TOKEN pattern as
 * lib/backend.ts (not reused directly - that helper always returns JSON,
 * this needs to pass binary image bytes through).
 *
 * GAP: as of this writing, src/api/main.py has no route that serves audit
 * screenshot files - AuditReport.images.* are local filesystem paths on the
 * backend host (see AuditOrchestrator / ImagePaths in audit_models.py), and
 * nothing mounts them over HTTP (no StaticFiles, no FileResponse route).
 * This handler calls a guessed REST-shaped path, `/audits/{id}/images/{file}`,
 * so the frontend is wired up and works the moment that backend route exists.
 * Until then every request here 404s upstream and callers should treat that
 * as "screenshot unavailable", not a broken image.
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
