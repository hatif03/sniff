# Sherlock One-Page Website Design + Technical Spec

## 1) Goal

Create a **high-impact single-page website** for Sherlock that feels clean, calm, and memorable for judges:
- Animation-first storytelling
- Strong product narrative in under 90 seconds scroll time
- Fast loading and smooth motion on modern laptops

---

## 2) Creative Direction

## Core Theme
**“Quiet confidence: issues found before users feel friction.”**

## Brand Personality
- Minimal
- Confident
- Human-friendly
- Premium

## Visual Mood
- Light neutral base with soft contrast
- Large whitespace and clean typography
- Subtle gradients (no heavy glow)
- Motion that feels calm and intentional

---

## 3) Single-Page Narrative Structure

## Section 1: Hero (Hook)
- Headline: “Your Signup Flow Is Breaking. Sherlock Already Knows.”
- Subheadline: “Powered by Sherlock Personas for mobile/web signup quality.”
- Primary CTA: `Watch Live Demo`
- Secondary CTA: `Run Sherlock CLI`
- Animation:
  - Gentle text fade/slide
  - Soft underline sweep on headline
  - Minimal background gradient drift

## Section 2: The Problem
- Short stats/claims about lost conversions and late bug detection.
- Animation:
  - Count-up metrics
  - Soft reveal on cards

## Section 3: How It Works (Core)
- 4-step flow:
  1. Simulate user
  2. Detect friction
  3. Diagnose cause
  4. Alert team instantly
- Animation:
  - Simple vertical timeline
  - Each step activates with subtle opacity + translate

## Section 4: Live Run Replay
- Mock terminal + mobile viewport replay.
- Show one bug detection event.
- Animation:
  - Typewriter CLI effect (short)
  - Crossfade between states
  - Alert card rise-in

## Section 5: Why Judges Will Love It
- Differentiators:
  - Persona-driven behavior
  - Root-cause intelligence
  - Bedrock-powered decisions
  - Slack escalation with evidence
- Animation:
  - Soft hover lift + shadow

## Section 6: Tech Stack + Architecture Snapshot
- Short architecture diagram (CLI, worker, agent, diagnosis, alerting).
- Animation:
  - Minimal line draw animation
  - Subtle node fade-in

## Section 7: CTA Footer
- “Launch Sherlock in 60 Seconds.”
- Buttons:
  - `Get Started`
  - `View Architecture`

---

## 4) Motion Design System

## Motion Principles
- Always purposeful, never decorative noise.
- Prefer subtle motion over dramatic effects.
- Motion depth from opacity + translate + small scale only.

## Recommended Motion Tokens
- Easing:
  - `easeOutCubic` for entrances
  - `easeInOutCubic` for section transitions
- Durations:
  - Micro: `0.14s`
  - Standard: `0.28s`
  - Narrative: `0.5s`
- Stagger: `30–50ms`

## Signature Animation Moments
- Hero headline reveal with soft underline sweep.
- Scroll progress indicator that gently fills.
- Slack alert card with clean rise + fade.
- Terminal command replay (`sherlock run ...`) with caret blink.

---

## 5) UI Design System

## Colors
- Background: `#F7F8FA`
- Surface: `#FFFFFF`
- Primary: `#1F2937`
- Accent: `#4F46E5`
- Soft Accent: `#7C83FD`
- Warning: `#D97706`
- Critical: `#DC2626`
- Text: `#111827`
- Muted: `#6B7280`

## Typography
- Display: `Space Grotesk` (headlines)
- Body/Code: `Inter` + `JetBrains Mono` for terminal snippets

## Components
- Minimal buttons with subtle accent fill
- Clean cards with soft radius and light shadow
- Timeline step nodes
- Terminal panel
- Alert badge pills (`P0`, `P1`, `P2`, `P3`)

---

## 6) Technical Architecture (Website)

## Stack
- **Framework:** Next.js (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **Animation:** Framer Motion + GSAP (scroll timelines)
- **Smooth Scroll:** Lenis
- **Optional visuals:** Lottie for lightweight icon animations

## Why this stack
- Fast developer velocity
- Great animation capabilities
- Easy deployment
- Strong performance controls

---

## 7) Page Implementation Plan

## Component Map
- `HeroSection.tsx`
- `ProblemSection.tsx`
- `HowItWorksSection.tsx`
- `ReplaySection.tsx`
- `DifferentiatorsSection.tsx`
- `ArchitectureSection.tsx`
- `FooterCTA.tsx`
- `AnimatedBackground.tsx`

## Animation Layer
- `useSectionReveal.ts`
- `useParallax.ts`
- `useTerminalReplay.ts`
- `motion-tokens.ts`

## Content/Data Layer
- `site-content.ts`
- `metrics.ts`
- `stack.ts`

---

## 8) Performance + Accessibility Requirements

- LCP target: < 2.5s on laptop Wi-Fi
- Defer non-critical animation bundles
- Use `prefers-reduced-motion` to disable heavy motion
- Keep 60fps on scroll for core sections
- Compress assets (SVG/WebP)
- Avoid blocking fonts (use `font-display: swap`)

---

## 9) SEO + Social Preview

- Title: `Sherlock Personas — AI Signup Experiments With Instant Team Alerts`
- Description: `Persona-driven mobile/web signup experiments with diagnosis and instant team alerts.`
- OG image: dark neon hero with CLI + alert card visual
- Add structured metadata in Next.js `generateMetadata`

---

## 10) Demo Script for Website

1. Open page at hero and click `Watch Live Demo`.
2. Scroll through “How it works” timeline.
3. Pause at replay section to show bug detection + alert animation.
4. Jump to architecture snapshot and connect to CLI product story.
5. End on CTA with run command:
   - `sherlock run --persona confused_first_time_user --device iphone13 --network 3g`

---

## 11) Build Scope (Solo-Friendly)

## Must Have
- Hero, How It Works, Replay, CTA
- Signature animations in 3 key moments
- High visual polish in minimal style

## Nice to Have
- Architecture SVG node animation
- Subtle particles background
- Additional hover micro-interactions

## Avoid (for hackathon time)
- Heavy 3D scenes that risk lag
- Overcomplicated CMS/content pipelines
- Excessive glow, particles, or visual noise

---

## 12) Acceptance Criteria

- Website tells full Sherlock story in one-page scroll.
- Motion feels premium, smooth, and minimal.
- At least 3 standout animated moments are demo-ready.
- Page remains smooth and readable on standard laptop hardware.
- CTA clearly connects website to CLI product and live demo.

---

## 13) Branded Hero Copy Options (Experimentation + Alerts)

## Option A
- Eyebrow: `Sherlock Personas`
- Headline: `Run signup experiments before users feel friction.`
- Subheadline: `Sherlock Personas explores real user behavior patterns and alerts your team the moment risk appears.`

## Option B
- Eyebrow: `Sherlock Personas`
- Headline: `Experiment across signup journeys. Alert the right team instantly.`
- Subheadline: `From persona-driven journeys to clear incident context, Sherlock keeps your team ahead of drop-off.`

## Option C
- Eyebrow: `Sherlock Personas`
- Headline: `Turn signup uncertainty into continuous experiments.`
- Subheadline: `Sherlock runs realistic personas, detects friction early, and sends instant team alerts with evidence.`

## Option D
- Eyebrow: `Sherlock Personas`
- Headline: `Every signup flow is an experiment.`
- Subheadline: `Sherlock makes each run measurable, explainable, and immediately actionable for your team.`

## Option E
- Eyebrow: `Sherlock Personas`
- Headline: `See friction sooner. Respond faster as a team.`
- Subheadline: `Persona-led signup experiments with live team alerts and clear next actions.`

---

## 14) Separate Website Implementation Plan

Important execution note:
- Use **subagents wherever possible** (for design system setup, motion implementation, performance checks, and deployment tasks) to parallelize delivery.
- Maintain a single `WORKLOG.md` as the **source of truth** for:
  - progress updates
  - implementation thinking/decisions
  - active checklist and completed tasks
- Every implementation session should begin by reading `WORKLOG.md` and end by updating it.

Build/Deploy baseline:
- Framework: **Next.js**
- Language: **TypeScript**
- Styling: **Tailwind CSS**
- Hosting/Deployment: **Vercel**

## Phase 1 — Setup (30–45 mins)
- Create Next.js TypeScript app (strict mode on).
- Install `tailwindcss`, `framer-motion`, `gsap`, `lenis`.
- Add base layout, font setup, and global color tokens.
- Add section anchors for one-page navigation.

## Phase 2 — Content + Structure (45–60 mins)
- Build section components:
  - `HeroSection`
  - `ProblemSection`
  - `HowItWorksSection`
  - `ReplaySection`
  - `DifferentiatorsSection`
  - `ArchitectureSection`
  - `FooterCTA`
- Add copy from chosen hero option and core section text.
- Keep spacing and typography minimal and consistent.

## Phase 3 — Motion Pass (60–90 mins)
- Add `framer-motion` reveal variants for each section.
- Add soft headline underline sweep in hero.
- Add timeline activation animations in “How it works”.
- Add terminal typing effect + alert card rise-in for replay section.
- Add smooth-scroll behavior with subtle section transitions.

## Phase 4 — Polish Pass (45–60 mins)
- Tune animation timing to avoid visual noise.
- Standardize button/card hover micro-interactions.
- Improve visual rhythm: whitespace, card sizing, text widths.
- Add mobile/tablet responsive adjustments.

## Phase 5 — Performance + Accessibility (30–45 mins)
- Add `prefers-reduced-motion` fallback.
- Optimize images and defer non-critical animation code.
- Check LCP and scroll smoothness.
- Ensure contrast and keyboard accessibility.

## Phase 6 — Demo Readiness (30 mins)
- Add final CTA links (`Watch Demo`, `Read Architecture`).
- Validate one full narrative scroll path.
- Rehearse live presentation flow 2–3 times.
- Freeze copy and animation timings before submission.
- Deploy final build to Vercel and verify production URL.

## Task Checklist
- [ ] Scaffold Next.js + Tailwind app
- [ ] Enable TypeScript strict checks
- [ ] Implement all one-page sections
- [ ] Apply minimal design system (colors/type/spacing)
- [ ] Add hero + timeline + replay signature animations
- [ ] Add responsive behavior for laptop/tablet/mobile
- [ ] Add reduced-motion support
- [ ] Optimize performance (assets + bundle split)
- [ ] Connect Git repo and deploy on Vercel
- [ ] Validate production domain and metadata
- [ ] QA final copy and CTA links
- [ ] Rehearse demo and lock final build

## Definition of Done
- One-page site is fully scrollable with smooth minimal animations.
- Story clearly communicates experiments + instant team alerts.
- Hero, replay, and CTA sections are presentation-ready.
- Performance and accessibility checks pass for demo hardware.

