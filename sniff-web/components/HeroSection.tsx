"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Container } from "@/components/ui/container";
import { Display1, BodyLg } from "@/components/ui/typography";

export default function HeroSection() {
  return (
    <section className="min-h-screen flex items-center justify-center relative overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-background via-surface to-background opacity-60" />

      <Container className="text-center relative z-10">
        {/* Eyebrow */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
          className="mb-6"
        >
          <span className="text-sm font-medium tracking-wide text-muted-foreground uppercase">
            Sniff
          </span>
        </motion.div>

        {/* Headline */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1, ease: [0.33, 1, 0.68, 1] }}
        >
          <Display1 className="text-foreground mb-6">
            Your Product Flow Is Breaking.{" "}
            <span className="text-primary">Sniff Already Knows.</span>
          </Display1>
        </motion.div>

        {/* Subheadline */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2, ease: [0.33, 1, 0.68, 1] }}
        >
          <BodyLg className="text-muted-foreground max-w-3xl mx-auto mb-12">
            An AI agent that signs up, clicks, and scrolls through your product like a real user
            — then tells you exactly where it broke and audits your landing page for what&apos;s costing you conversions.
          </BodyLg>
        </motion.div>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3, ease: [0.33, 1, 0.68, 1] }}
          className="flex flex-col sm:flex-row gap-4 justify-center items-center"
        >
          <Button asChild size="xl">
            <Link href="/dashboard/new-run">Run an Audit</Link>
          </Button>
          <Button asChild variant="outline" size="xl">
            <Link href="/dashboard">View Dashboard</Link>
          </Button>
        </motion.div>

        <motion.a
          href="/tech-stack"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.45, ease: [0.33, 1, 0.68, 1] }}
          className="mt-6 inline-block text-sm font-medium text-muted-foreground hover:text-primary transition-colors"
        >
          View Full Tech Stack →
        </motion.a>
      </Container>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 1 }}
        className="absolute bottom-12 left-1/2 -translate-x-1/2"
      >
        <motion.div
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
          className="w-6 h-10 border-2 border-muted-foreground/30 rounded-full flex items-start justify-center p-2"
        >
          <div className="w-1 h-2 bg-muted-foreground/50 rounded-full" />
        </motion.div>
      </motion.div>
    </section>
  );
}
