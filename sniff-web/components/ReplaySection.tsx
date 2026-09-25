"use client";

import { motion } from "framer-motion";
import { useInView } from "framer-motion";
import { useRef, useState, useEffect } from "react";

export default function ReplaySection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });
  const [terminalText, setTerminalText] = useState("");
  const [showAlert, setShowAlert] = useState(false);

  const fullCommand = "$ sherlock run --persona confused_first_time_user --device iphone13 --network 3g";

  useEffect(() => {
    if (!isInView) return;

    let index = 0;
    const interval = setInterval(() => {
      if (index <= fullCommand.length) {
        setTerminalText(fullCommand.slice(0, index));
        index++;
      } else {
        clearInterval(interval);
        setTimeout(() => setShowAlert(true), 500);
      }
    }, 30);

    return () => clearInterval(interval);
  }, [isInView]);

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
            See It In Action
          </h2>
          <p className="text-lg text-muted max-w-2xl mx-auto">
            Watch Sherlock detect a critical product-flow bug in real-time.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Terminal */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.5, delay: 0.2, ease: [0.33, 1, 0.68, 1] }}
            className="bg-primary rounded-2xl p-6 shadow-2xl overflow-hidden"
          >
            <div className="flex items-center gap-2 mb-4">
              <div className="w-3 h-3 rounded-full bg-critical" />
              <div className="w-3 h-3 rounded-full bg-warning" />
              <div className="w-3 h-3 rounded-full bg-[#10B981]" />
              <span className="ml-2 text-xs text-muted font-mono">sherlock-cli</span>
            </div>
            <div className="font-mono text-sm">
              <div className="text-[#10B981] mb-4">
                {terminalText}
                <span className="animate-pulse">|</span>
              </div>
              {terminalText.length === fullCommand.length && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.3 }}
                  className="space-y-2 text-muted/80"
                >
                  <div>→ Initializing persona: confused_first_time_user</div>
                  <div>→ Device: iPhone 13</div>
                  <div>→ Network: 3G throttling enabled</div>
                  <div className="mt-4">Running product flow...</div>
                  <div className="text-warning">⚠ Button not responding after 3s</div>
                  <div className="text-critical">✗ Critical: Product flow blocked</div>
                  <div className="text-accent">→ Generating diagnosis...</div>
                  <div className="text-[#10B981]">✓ Alert sent to #eng-mobile</div>
                </motion.div>
              )}
            </div>
          </motion.div>

          {/* Alert Card */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.5, delay: 0.3, ease: [0.33, 1, 0.68, 1] }}
            className="relative"
          >
            {showAlert && (
              <motion.div
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
                className="bg-background rounded-2xl p-8 border-2 border-critical/20 shadow-xl"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-critical/10 flex items-center justify-center">
                      <span className="text-xl">🚨</span>
                    </div>
                    <div>
                      <div className="font-display font-bold text-lg text-primary">
                        Product Flow Blocked
                      </div>
                      <div className="text-sm text-muted">2 minutes ago</div>
                    </div>
                  </div>
                  <span className="px-3 py-1 bg-critical/10 text-critical text-xs font-bold rounded-full">
                    P0
                  </span>
                </div>

                <div className="space-y-4">
                  <div>
                    <div className="text-sm font-medium text-primary mb-1">Issue</div>
                    <div className="text-sm text-muted">
                      Submit button unresponsive on iPhone 13 with 3G network
                    </div>
                  </div>

                  <div>
                    <div className="text-sm font-medium text-primary mb-1">Root Cause</div>
                    <div className="text-sm text-muted">
                      JavaScript event listener not attached due to slow bundle load
                    </div>
                  </div>

                  <div>
                    <div className="text-sm font-medium text-primary mb-1">Impact</div>
                    <div className="text-sm text-muted">
                      100% of product-flow attempts failing on slower connections
                    </div>
                  </div>

                  <div className="pt-4 border-t border-primary/10">
                    <button className="w-full px-4 py-3 bg-critical text-white rounded-lg font-medium hover:bg-critical/90 transition-colors">
                      View Full Diagnosis →
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
          </motion.div>
        </div>
      </div>
    </section>
  );
}
