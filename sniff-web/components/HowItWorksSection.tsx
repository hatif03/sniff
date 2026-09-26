"use client";

import { motion } from "framer-motion";
import { useInView } from "framer-motion";
import { useRef } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Container } from "@/components/ui/container";
import { Display2, Heading3, Body } from "@/components/ui/typography";

const steps = [
  {
    number: "01",
    title: "Simulate User",
    description: "Sniff acts like a real user across devices and network conditions.",
    icon: "👤",
  },
  {
    number: "02",
    title: "Detect Friction",
    description: "Identifies broken flows, slow loads, and user experience blockers in real-time.",
    icon: "🔍",
  },
  {
    number: "03",
    title: "Diagnose Cause",
    description: "AI-powered root cause analysis pinpoints exactly what went wrong and why.",
    icon: "🧠",
  },
  {
    number: "04",
    title: "Alert Team Instantly",
    description: "Send contextualized alerts to Slack with evidence and clear next steps.",
    icon: "⚡",
  },
];

export default function HowItWorksSection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section ref={ref} className="py-20 md:py-32 bg-background">
      <Container>
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
          className="text-center mb-20"
        >
          <Display2 className="text-foreground mb-4">
            How It Works
          </Display2>
          <Body className="text-muted-foreground max-w-2xl mx-auto">
            Four simple steps from persona to production-ready insights.
          </Body>
        </motion.div>

        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-8 md:left-1/2 top-0 bottom-0 w-0.5 bg-gradient-to-b from-primary/20 via-primary/40 to-primary/20" />

          <div className="space-y-16">
            {steps.map((step, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: index % 2 === 0 ? -30 : 30 }}
                animate={isInView ? { opacity: 1, x: 0 } : {}}
                transition={{
                  duration: 0.5,
                  delay: 0.2 + index * 0.15,
                  ease: [0.33, 1, 0.68, 1],
                }}
                className={`relative flex items-center ${
                  index % 2 === 0 ? "md:flex-row" : "md:flex-row-reverse"
                }`}
              >
                {/* Timeline node */}
                <div className="absolute left-8 md:left-1/2 -translate-x-1/2 w-16 h-16 rounded-full bg-primary flex items-center justify-center text-2xl shadow-lg z-10">
                  {step.icon}
                </div>

                {/* Content card */}
                <div className={`flex-1 ${index % 2 === 0 ? "md:pr-24" : "md:pl-24"} pl-24 md:pl-0 md:pr-0`}>
                  <Card
                    className={`p-8 shadow-sm hover:shadow-md hover:border-primary/20 transition-all duration-300 ${
                      index % 2 === 0 ? "md:ml-0 md:mr-auto md:text-right" : "md:ml-auto md:mr-0"
                    } max-w-md`}
                  >
                    <CardContent>
                      <div className="text-sm font-mono text-primary mb-2">{step.number}</div>
                      <Heading3 className="text-foreground mb-3">
                        {step.title}
                      </Heading3>
                      <Body className="text-muted-foreground">{step.description}</Body>
                    </CardContent>
                  </Card>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </Container>
    </section>
  );
}
