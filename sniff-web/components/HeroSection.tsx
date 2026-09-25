"use client";

import { motion } from "framer-motion";

export default function HeroSection() {
  return (
    <section className="min-h-screen flex items-center justify-center px-6 relative overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-background via-surface to-background opacity-60" />

      <div className="max-w-5xl mx-auto text-center relative z-10">
        {/* Eyebrow */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
          className="mb-6"
        >
          <span className="text-sm font-medium tracking-wide text-muted uppercase">
            Sherlock Personas
          </span>
        </motion.div>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1, ease: [0.33, 1, 0.68, 1] }}
          className="text-5xl md:text-6xl lg:text-7xl font-display font-bold text-primary mb-6 leading-tight"
        >
          Your Product Flow Is Breaking.{" "}
          <span className="relative inline-block">
            <span className="relative z-10">Sherlock Already Knows.</span>
            <motion.span
              initial={{ width: 0 }}
              animate={{ width: "100%" }}
              transition={{ duration: 0.5, delay: 0.6, ease: [0.33, 1, 0.68, 1] }}
              className="absolute bottom-2 left-0 h-3 bg-accent/20 -z-0"
            />
          </span>
        </motion.h1>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2, ease: [0.33, 1, 0.68, 1] }}
          className="text-lg md:text-xl text-muted max-w-3xl mx-auto mb-12 leading-relaxed"
        >
          Powered by Sherlock Personas for mobile/web product quality.
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3, ease: [0.33, 1, 0.68, 1] }}
          className="flex flex-col sm:flex-row gap-4 justify-center items-center"
        >
          <a
            href="/dashboard"
            className="px-8 py-4 bg-accent text-white rounded-lg font-medium hover:bg-accent/90 transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105 inline-block"
          >
            View Dashboard
          </a>
          <a
            href="/docs"
            className="px-8 py-4 bg-surface text-primary border-2 border-primary/10 rounded-lg font-medium hover:border-accent/30 hover:text-accent transition-all duration-200 inline-block"
          >
            View CLI Documentation
          </a>
        </motion.div>

        <motion.a
          href="/tech-stack"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.45, ease: [0.33, 1, 0.68, 1] }}
          className="mt-6 inline-block text-sm font-medium text-muted hover:text-accent transition-colors"
        >
          View Full Tech Stack →
        </motion.a>
      </div>

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
          className="w-6 h-10 border-2 border-muted/30 rounded-full flex items-start justify-center p-2"
        >
          <div className="w-1 h-2 bg-muted/50 rounded-full" />
        </motion.div>
      </motion.div>
    </section>
  );
}
