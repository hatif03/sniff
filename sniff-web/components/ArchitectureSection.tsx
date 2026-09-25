"use client";

import { motion } from "framer-motion";
import { useInView } from "framer-motion";
import { useRef } from "react";

const architectureNodes = [
  { name: "CLI", description: "Command interface", position: "top" },
  { name: "Worker", description: "Execution engine", position: "middle-left" },
  { name: "Agent", description: "Persona simulator", position: "middle-center" },
  { name: "Diagnosis", description: "AI analysis", position: "middle-right" },
  { name: "Alerting", description: "Team notifications", position: "bottom" },
];

export default function ArchitectureSection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section ref={ref} className="py-32 px-6 bg-surface">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-display font-bold text-primary mb-4">
            Technical Architecture
          </h2>
          <p className="text-lg text-muted max-w-2xl mx-auto">
            A clean, scalable system built for production reliability.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={isInView ? { opacity: 1, scale: 1 } : {}}
          transition={{ duration: 0.5, delay: 0.2, ease: [0.33, 1, 0.68, 1] }}
          className="bg-background rounded-2xl p-12 border border-primary/5 relative overflow-hidden"
        >
          {/* Background grid */}
          <div className="absolute inset-0 bg-[linear-gradient(rgba(31,41,55,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(31,41,55,0.03)_1px,transparent_1px)] bg-[size:40px_40px]" />

          <div className="relative space-y-8">
            {/* CLI Node (Top) */}
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="flex justify-center"
            >
              <div className="bg-accent text-white px-8 py-4 rounded-xl font-mono text-sm font-medium shadow-lg">
                sherlock run
              </div>
            </motion.div>

            {/* Connector Line 1 */}
            <motion.div
              initial={{ scaleY: 0 }}
              animate={isInView ? { scaleY: 1 } : {}}
              transition={{ duration: 0.5, delay: 0.4 }}
              className="w-0.5 h-12 bg-gradient-to-b from-accent to-soft-accent mx-auto origin-top"
            />

            {/* Middle Layer */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {["Worker", "Agent", "Diagnosis"].map((node, index) => (
                <motion.div
                  key={node}
                  initial={{ opacity: 0, y: 20 }}
                  animate={isInView ? { opacity: 1, y: 0 } : {}}
                  transition={{ duration: 0.5, delay: 0.5 + index * 0.1 }}
                  className="bg-surface rounded-xl p-6 border-2 border-primary/10 hover:border-accent/30 transition-all shadow-sm hover:shadow-md"
                >
                  <div className="text-center">
                    <div className="font-display font-bold text-primary mb-2">{node}</div>
                    <div className="text-xs text-muted">
                      {node === "Worker" && "Execution engine"}
                      {node === "Agent" && "Persona simulator"}
                      {node === "Diagnosis" && "AI analysis"}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Connector Line 2 */}
            <motion.div
              initial={{ scaleY: 0 }}
              animate={isInView ? { scaleY: 1 } : {}}
              transition={{ duration: 0.5, delay: 0.8 }}
              className="w-0.5 h-12 bg-gradient-to-b from-soft-accent to-accent mx-auto origin-top"
            />

            {/* Alerting Node (Bottom) */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.9 }}
              className="flex justify-center"
            >
              <div className="bg-gradient-to-r from-accent to-soft-accent text-white px-8 py-4 rounded-xl font-display font-medium shadow-lg flex items-center gap-3">
                <span>📢</span>
                <span>Slack Alert</span>
              </div>
            </motion.div>
          </div>

          {/* Tech Stack badges */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ duration: 0.5, delay: 1 }}
            className="mt-12 flex flex-wrap justify-center gap-3"
          >
            {["TypeScript", "AWS Bedrock", "Playwright", "Slack API"].map((tech) => (
              <span
                key={tech}
                className="px-4 py-2 bg-surface border border-primary/10 rounded-full text-sm text-muted font-medium"
              >
                {tech}
              </span>
            ))}
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
