"use client";

import { motion } from "framer-motion";
import { useInView } from "framer-motion";
import { useRef } from "react";

export default function FooterCTA() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section ref={ref} className="py-32 px-6 bg-gradient-to-br from-foreground to-foreground/90 text-white relative overflow-hidden">
      {/* Background pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:60px_60px]" />

      <div className="max-w-4xl mx-auto text-center relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
        >
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-display font-bold mb-6 leading-tight">
            Launch Sniff in 60 Seconds
          </h2>
          <p className="text-lg md:text-xl text-white/80 mb-12 max-w-2xl mx-auto leading-relaxed">
            Start running persona-driven experiments and catch product-flow bugs before your users do.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="px-8 py-4 bg-primary text-white rounded-lg font-medium shadow-xl hover:shadow-2xl transition-all duration-200"
            >
              Get Started
            </motion.button>
            <motion.a
              href="/docs"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="px-8 py-4 bg-white/10 backdrop-blur-sm text-white border-2 border-white/20 rounded-lg font-medium hover:bg-white/20 transition-all duration-200 inline-block"
            >
              View Documentation
            </motion.a>
            <motion.a
              href="/tech-stack"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="px-8 py-4 bg-white/10 backdrop-blur-sm text-white border-2 border-white/20 rounded-lg font-medium hover:bg-white/20 transition-all duration-200 inline-block"
            >
              View Tech Stack
            </motion.a>
          </div>

          {/* CLI command */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, delay: 0.2, ease: [0.33, 1, 0.68, 1] }}
            className="bg-black/30 backdrop-blur-sm rounded-xl p-6 border border-white/10 max-w-2xl mx-auto"
          >
            <div className="flex items-center gap-2 mb-3">
              <div className="w-3 h-3 rounded-full bg-critical" />
              <div className="w-3 h-3 rounded-full bg-warning" />
              <div className="w-3 h-3 rounded-full bg-[#10B981]" />
            </div>
            <code className="font-mono text-sm md:text-base text-[#10B981] block text-left">
              $ sniff run --persona confused_first_time_user --device iphone13 --network 3g
            </code>
          </motion.div>
        </motion.div>
      </div>

      {/* Footer */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={isInView ? { opacity: 1 } : {}}
        transition={{ duration: 0.5, delay: 0.4 }}
        className="mt-20 text-center text-white/60 text-sm relative z-10"
      >
        <p>Built with Claude, Bedrock, and ❤️ for better product experiences.</p>
        <p className="mt-2">© 2026 Sniff. All rights reserved.</p>
      </motion.div>
    </section>
  );
}
