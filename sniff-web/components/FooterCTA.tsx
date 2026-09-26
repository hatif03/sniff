"use client";

import { motion } from "framer-motion";
import { useInView } from "framer-motion";
import { useRef } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Container } from "@/components/ui/container";
import { Display2, BodyLg } from "@/components/ui/typography";

export default function FooterCTA() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section ref={ref} className="py-20 md:py-32 bg-gradient-to-br from-foreground to-foreground/90 text-white relative overflow-hidden">
      {/* Background pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:60px_60px]" />

      <Container className="text-center relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
        >
          <Display2 className="mb-6">
            Launch Sniff in 60 Seconds
          </Display2>
          <BodyLg className="text-white/80 mb-12 max-w-2xl mx-auto">
            Start running persona-driven experiments and catch product-flow bugs before your users do.
          </BodyLg>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">
            <Button asChild size="xl">
              <Link href="/dashboard/new-run">Get Started</Link>
            </Button>
            <Button
              asChild
              variant="outline"
              size="xl"
              className="bg-white/10 backdrop-blur-sm text-white border-white/20 hover:bg-white/20 hover:text-white"
            >
              <Link href="/tech-stack">View Tech Stack</Link>
            </Button>
          </div>
        </motion.div>
      </Container>

      {/* Footer */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={isInView ? { opacity: 1 } : {}}
        transition={{ duration: 0.5, delay: 0.4 }}
        className="mt-20 text-center text-white/60 text-sm relative z-10"
      >
        <p>Built with Claude Code and ❤️ for better product experiences.</p>
        <p className="mt-2">© 2026 Sniff. All rights reserved.</p>
      </motion.div>
    </section>
  );
}
