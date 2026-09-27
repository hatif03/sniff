"use client";

import { useState } from "react";
import { ImageOff } from "lucide-react";
import { auditImageSrc } from "@/lib/audits";

/**
 * Renders one audit screenshot - a real Supabase Storage URL for a new
 * audit (used directly), or the backend's image-proxy route for an older
 * row that only has a local path (see auditImageSrc in lib/audits.ts) -
 * falling back to a plain "unavailable" placeholder instead of a broken
 * <img> icon if even that 404s.
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
