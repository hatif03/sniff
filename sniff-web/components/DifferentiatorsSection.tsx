"use client";

import { motion } from "framer-motion";
import { useInView } from "framer-motion";
import { useRef } from "react";

const differentiators = [
  {
    title: "Persona-Driven Behavior",
    description: "Real user patterns, not scripted tests. Confused first-timers to power users.",
    icon: "🎭",
    gradient: "from-accent/10 to-soft-accent/10",
  },
  {
    title: "Root-Cause Intelligence",
    description: "AI diagnosis that tells you exactly what broke and how to fix it.",
    icon: "🔬",
    gradient: "from-warning/10 to-warning/5",
  },
  {
    title: "Bedrock-Powered Decisions",
    description: "Claude analyzes context and makes smart decisions about severity and routing.",
    icon: "⚡",
    gradient: "from-accent/10 to-accent/5",
  },
  {
    title: "Slack Escalation with Evidence",
    description: "Instant team alerts with screenshots, traces, and actionable next steps.",
    icon: "📢",
    gradient: "from-critical/10 to-critical/5",
  },
];

export default function DifferentiatorsSection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section ref={ref} className="py-32 px-6 bg-background">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-display font-bold text-primary mb-4">
            Why Judges Will Love It
          </h2>
          <p className="text-lg text-muted max-w-2xl mx-auto">
            Built for the real world, powered by cutting-edge AI.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {differentiators.map((item, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 30 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{
                duration: 0.5,
                delay: 0.1 + index * 0.1,
                ease: [0.33, 1, 0.68, 1],
              }}
              whileHover={{ y: -8, transition: { duration: 0.2 } }}
              className={`bg-gradient-to-br ${item.gradient} rounded-2xl p-8 border border-primary/5 hover:border-accent/20 transition-all duration-300 hover:shadow-xl cursor-pointer group`}
            >
              <div className="text-4xl mb-4 transform group-hover:scale-110 transition-transform duration-300">
                {item.icon}
              </div>
              <h3 className="text-xl font-display font-bold text-primary mb-3">
                {item.title}
              </h3>
              <p className="text-muted leading-relaxed">{item.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
