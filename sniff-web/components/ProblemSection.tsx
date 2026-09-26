"use client";

import { motion } from "framer-motion";
import { useInView } from "framer-motion";
import { useRef } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Container } from "@/components/ui/container";
import { Display2, Body } from "@/components/ui/typography";

const stats = [
  {
    value: "68%",
    label: "of users abandon broken product flows",
    color: "critical",
  },
  {
    value: "3.2x",
    label: "longer to detect mobile-specific bugs",
    color: "warning",
  },
  {
    value: "~$40K",
    label: "average revenue lost per product-flow incident",
    color: "accent",
  },
];

export default function ProblemSection() {
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
            Most Teams Find Out Too Late
          </Display2>
          <Body className="text-muted-foreground max-w-2xl mx-auto">
            By the time you hear from users, conversions have already dropped.
          </Body>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {stats.map((stat, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 30 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{
                duration: 0.5,
                delay: 0.2 + index * 0.1,
                ease: [0.33, 1, 0.68, 1],
              }}
            >
              <Card className="p-8 border-foreground/5 hover:border-primary/20 transition-all duration-300 hover:shadow-lg">
                <CardContent>
                  <div
                    className={`text-5xl font-display font-bold mb-3 ${
                      stat.color === "critical"
                        ? "text-critical"
                        : stat.color === "warning"
                        ? "text-warning"
                        : "text-primary"
                    }`}
                  >
                    {stat.value}
                  </div>
                  <Body className="text-muted-foreground">{stat.label}</Body>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </Container>
    </section>
  );
}
