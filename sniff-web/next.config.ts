import type { NextConfig } from "next";

// Derived from the actual configured project, not hardcoded - a stale,
// hand-copied hostname here from an earlier Supabase project silently
// blocked every screenshot Next/Image tried to render (no error, just a
// blank image), since Next.js only loads external images from an
// allowlisted host.
const supabaseHostname = process.env.NEXT_PUBLIC_SUPABASE_URL
  ? new URL(process.env.NEXT_PUBLIC_SUPABASE_URL).hostname
  : undefined;

const nextConfig: NextConfig = {
  // Performance optimizations
  reactStrictMode: true,

  // Compiler optimizations
  compiler: {
    removeConsole: process.env.NODE_ENV === "production",
  },

  // Experimental features for better performance
  experimental: {
    optimizePackageImports: ["framer-motion", "gsap"],
  },

  outputFileTracingRoot: __dirname,

  // Image optimization
  images: {
    formats: ["image/webp", "image/avif"],
    remotePatterns: supabaseHostname
      ? [
          {
            protocol: "https",
            hostname: supabaseHostname,
            port: "",
            pathname: "/storage/v1/object/public/**",
          },
        ]
      : [],
  },
};

export default nextConfig;
