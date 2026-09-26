"use client";

import { useState } from "react";
import { ImageOff } from "lucide-react";
import { auditImageSrc } from "@/lib/audits";

/**
 * Renders one audit screenshot via the image-proxy route handler, falling
 * back to a plain "unavailable" placeholder instead of a broken <img> icon.
 *
 * The backend does not yet expose these files over HTTP (see the GAP
 * comment in app/api/backend/audits/[auditId]/images/[filename]/route.ts),
 * so today this will always render the placeholder - that's expected, not
 * a bug in this component.
 */
export function AuditScreenshot({
  auditId,
  path,
  alt,
  className = "",
}: {
  auditId: string;
  path: string;
  alt: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <div
        className={`flex flex-col items-center justify-center gap-2 bg-muted/50 text-muted-foreground ${className}`}
      >
        <ImageOff className="size-6" />
        <span className="text-xs">Screenshot unavailable</span>
      </div>
    );
  }

  return (
    // Proxied bytes of unknown dimensions from the backend - a plain <img>
    // keeps onError-driven fallback simple, vs next/image's stricter sizing.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={auditImageSrc(auditId, path)}
      alt={alt}
      className={className}
      onError={() => setFailed(true)}
    />
  );
}
