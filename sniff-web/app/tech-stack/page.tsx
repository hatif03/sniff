import type { Metadata } from "next";
import Link from "next/link";

const stackGroups = [
  {
    area: "CLI",
    tech: "Python",
    detail: "Primary language for local and CI execution commands.",
  },
  {
    area: "Agent Runtime",
    tech: "AWS Strands Agent",
    detail: "Coordinates agent execution, state, and orchestration flow.",
  },
  {
    area: "Decision Agent",
    tech: "DeepSeek V3",
    detail: "Handles decision-making and reasoning paths for run outcomes.",
  },
  {
    area: "Image Capability",
    tech: "NVIDIA Nemotron Nano 12B v2 VL",
    detail: "Multimodal model for image-aware reasoning and visual understanding.",
  },
  {
    area: "Dashboard",
    tech: "Next.js + Supabase",
    detail: "Frontend and backend data layer for run history and analysis views.",
  },
];

export const metadata: Metadata = {
  title: "Tech Stack - Sherlock Personas",
  description: "Technology stack used by Sherlock Personas.",
};

export default function TechStackPage() {
  return (
    <main className="min-h-screen py-24 px-6 bg-background">
      <div className="max-w-6xl mx-auto">
        <Link
          href="/"
          className="text-sm text-muted hover:text-accent transition-colors inline-block mb-8"
        >
          ← Back to Home
        </Link>

        <header className="mb-12">
          <p className="text-sm font-medium tracking-wide text-muted uppercase mb-3">
            Sherlock Personas
          </p>
          <h1 className="text-4xl md:text-5xl font-display font-bold text-primary mb-4">
            Tech Stack
          </h1>
          <p className="text-lg text-muted max-w-3xl">
            The current implementation stack across CLI, agents, multimodal reasoning,
            and dashboard infrastructure.
          </p>
        </header>

        <section className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {stackGroups.map((item) => (
            <article
              key={item.area}
              className="bg-surface border border-primary/10 rounded-xl p-6 shadow-sm"
            >
              <p className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">
                {item.area}
              </p>
              <h2 className="text-xl font-display font-bold text-primary mb-2">
                {item.tech}
              </h2>
              <p className="text-sm text-muted leading-relaxed">{item.detail}</p>
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}
