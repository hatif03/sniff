import type { Metadata } from "next";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Container } from "@/components/ui/container";
import { Display2 } from "@/components/ui/typography";

const stackGroups = [
  {
    area: "Browser Automation",
    tech: "Playwright",
    detail: "Drives the real browser session - navigation, screenshots, mobile device/network emulation.",
  },
  {
    area: "Vision Reasoning (Tier 3)",
    tech: "Gemini (Vertex AI)",
    detail: "The only provider with documented multimodal input - owns every decision that needs to see the screenshot.",
  },
  {
    area: "Text Reasoning (Tier 3)",
    tech: "k2-horizon (ifm.ai)",
    detail: "Text-only reasoning: goal enhancement, planning, persona review, copy rewrites.",
  },
  {
    area: "Fast Decisions (Tier 2)",
    tech: "Jev (Typesafe AI)",
    detail: "Ultra-fast sanity checks - goal-reached detection, context enrichment, decision critique.",
  },
  {
    area: "Backend API",
    tech: "FastAPI on Cloud Run",
    detail: "Triggers runs/audits, background-task execution, the shared-secret auth gate.",
  },
  {
    area: "Database",
    tech: "Supabase (Postgres)",
    detail: "Public-read persistence for runs, audits, and schedules - the real system of record.",
  },
  {
    area: "Scheduling",
    tech: "Cloud Scheduler",
    detail: "Ticks recurring runs/audits on a fixed cadence - a single external trigger, safe across autoscaled instances.",
  },
  {
    area: "Dashboard",
    tech: "Next.js + Vercel",
    detail: "Web-first frontend - the primary way to trigger and watch runs, not the CLI.",
  },
  {
    area: "CLI",
    tech: "Python",
    detail: "Secondary, developer/CI-facing entry point - sniff run/demo/experiment commands.",
  },
];

export const metadata: Metadata = {
  title: "Tech Stack - Sniff",
  description: "Technology stack used by Sniff.",
};

export default function TechStackPage() {
  return (
    <main className="min-h-screen py-24 bg-background">
      <Container>
        <Link
          href="/"
          className="text-sm text-muted-foreground hover:text-primary transition-colors inline-block mb-8"
        >
          ← Back to Home
        </Link>

        <header className="mb-12">
          <p className="text-sm font-medium tracking-wide text-muted-foreground uppercase mb-3">
            Sniff
          </p>
          <Display2 as="h1" className="text-foreground mb-4">
            Tech Stack
          </Display2>
          <p className="text-lg text-muted-foreground max-w-3xl">
            The current implementation stack across CLI, agents, multimodal reasoning,
            and dashboard infrastructure.
          </p>
        </header>

        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {stackGroups.map((item) => (
            <Card key={item.area}>
              <CardContent>
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                  {item.area}
                </p>
                <h2 className="text-xl font-display font-bold text-foreground mb-2">
                  {item.tech}
                </h2>
                <p className="text-sm text-muted-foreground leading-relaxed">{item.detail}</p>
              </CardContent>
            </Card>
          ))}
        </section>
      </Container>
    </main>
  );
}
