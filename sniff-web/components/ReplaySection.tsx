"use client";

import { motion } from "framer-motion";
import { useInView } from "framer-motion";
import { useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Container } from "@/components/ui/container";
import { Display2, Body } from "@/components/ui/typography";

export default function ReplaySection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section ref={ref} className="py-20 md:py-32 bg-surface">
      <Container>
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
          className="text-center mb-16"
        >
          <Display2 className="text-foreground mb-4">
            See It In Action
          </Display2>
          <Body className="text-muted-foreground max-w-2xl mx-auto">
            A look at how Sniff reports a critical product-flow bug in the dashboard.
          </Body>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Run summary preview */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.5, delay: 0.2, ease: [0.33, 1, 0.68, 1] }}
          >
            <Card className="p-6 shadow-2xl">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-base">Run #a3f9c2</CardTitle>
                <Badge variant="destructive">Failed</Badge>
              </CardHeader>
              <CardContent className="space-y-3 font-mono text-sm">
                <div className="flex justify-between text-muted-foreground">
                  <span>Persona</span>
                  <span className="text-foreground">confused_first_time_user</span>
                </div>
                <div className="flex justify-between text-muted-foreground">
                  <span>Target</span>
                  <span className="text-foreground">app.example.com/signup</span>
                </div>
                <div className="flex justify-between text-muted-foreground">
                  <span>Device</span>
                  <span className="text-foreground">iPhone 13, 3G</span>
                </div>
                <div className="mt-4 space-y-2 border-t border-foreground/10 pt-4">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <span className="text-[#10B981]">✓</span> Loaded signup page
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <span className="text-[#10B981]">✓</span> Filled form fields
                  </div>
                  <div className="flex items-center gap-2 text-warning">
                    <span>⚠</span> Submit button not responding after 3s
                  </div>
                  <div className="flex items-center gap-2 text-critical">
                    <span>✗</span> Product flow blocked
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Diagnosis Card */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.5, delay: 0.3, ease: [0.33, 1, 0.68, 1] }}
          >
            <Card className="p-8 border-2 border-critical/20 shadow-xl">
              <CardContent className="space-y-4">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-critical/10 flex items-center justify-center">
                      <span className="text-xl">🚨</span>
                    </div>
                    <div>
                      <div className="font-display font-bold text-lg text-foreground">
                        Product Flow Blocked
                      </div>
                      <div className="text-sm text-muted-foreground">2 minutes ago</div>
                    </div>
                  </div>
                  <Badge variant="destructive">P0</Badge>
                </div>

                <div>
                  <div className="text-sm font-medium text-foreground mb-1">Issue</div>
                  <div className="text-sm text-muted-foreground">
                    Submit button unresponsive on iPhone 13 with 3G network
                  </div>
                </div>

                <div>
                  <div className="text-sm font-medium text-foreground mb-1">Root Cause</div>
                  <div className="text-sm text-muted-foreground">
                    JavaScript event listener not attached due to slow bundle load
                  </div>
                </div>

                <div>
                  <div className="text-sm font-medium text-foreground mb-1">Impact</div>
                  <div className="text-sm text-muted-foreground">
                    100% of product-flow attempts failing on slower connections
                  </div>
                </div>

                <div className="pt-4 border-t border-foreground/10">
                  <Button variant="destructive" className="w-full">
                    View Full Diagnosis →
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </Container>
    </section>
  );
}
