/**
 * postcss.config.mjs — PostCSS configuration for sniff-web
 *
 * Tailwind v4 Migration (ADR-002):
 * - Replaced `tailwindcss` plugin with `@tailwindcss/postcss`
 * - Removed `autoprefixer` — Tailwind v4 handles vendor prefixes natively
 *   via built-in browser targeting. No separate autoprefixer needed.
 *
 * Reference: https://tailwindcss.com/docs/installation/using-postcss
 */

/** @type {import('postcss-load-config').Config} */
const config = {
  plugins: {
    // Tailwind v4 PostCSS plugin — replaces the old `tailwindcss` plugin
    "@tailwindcss/postcss": {},
  },
};

export default config;
