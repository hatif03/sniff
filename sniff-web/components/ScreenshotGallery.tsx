"use client";

import { useEffect, useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import Image from 'next/image';
import { getObservations } from '@/lib/queries';

interface Observation {
  step: number;
  screenshot_url: string;
  url: string;
}

export default function ScreenshotGallery({ runId }: { runId: string }) {
  const [observations, setObservations] = useState<Observation[]>([]);
  const [selectedStep, setSelectedStep] = useState(0);
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  useEffect(() => {
    async function fetchScreenshots() {
      const data = await getObservations(runId);
      setObservations(data);
    }

    if (runId) {
      fetchScreenshots();
    }
  }, [runId]);

  if (observations.length === 0) return null;

  return (
    <div ref={ref}>
      <motion.h3
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.33, 1, 0.68, 1] }}
        className="text-2xl font-display font-bold text-foreground mb-6"
      >
        Journey Screenshots
      </motion.h3>

      {/* Screenshot viewer */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.2, ease: [0.33, 1, 0.68, 1] }}
        className="bg-surface rounded-2xl overflow-hidden border border-foreground/10 shadow-lg mb-4"
      >
        {observations[selectedStep] && (
          <div className="relative">
            <div className="relative w-full aspect-video bg-background">
              <Image
                src={observations[selectedStep].screenshot_url}
                alt={`Step ${observations[selectedStep].step}`}
                fill
                className="object-contain"
              />
            </div>
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-foreground/90 to-transparent p-6">
              <p className="text-surface font-display font-bold text-lg">
                Step {observations[selectedStep].step}
              </p>
              <p className="text-surface/90 text-sm font-mono truncate">
                {observations[selectedStep].url}
              </p>
            </div>
          </div>
        )}
      </motion.div>

      {/* Thumbnail navigation */}
      <div className="flex gap-3 overflow-x-auto pb-2">
        {observations.map((obs, i) => (
          <motion.button
            key={obs.step}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 + i * 0.05, ease: [0.33, 1, 0.68, 1] }}
            onClick={() => setSelectedStep(i)}
            className={`flex-shrink-0 w-24 h-16 rounded-lg overflow-hidden border-2 transition-all relative ${
              selectedStep === i
                ? 'border-primary shadow-lg scale-105'
                : 'border-foreground/10 hover:border-primary/50 opacity-60 hover:opacity-100'
            }`}
          >
            <Image
              src={obs.screenshot_url}
              alt={`Step ${obs.step}`}
              fill
              className="object-cover"
            />
          </motion.button>
        ))}
      </div>
    </div>
  );
}
