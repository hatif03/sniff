"use client";

import { useEffect, useRef, useState } from 'react';
import { useInView } from 'framer-motion';

/**
 * Count-up number for scores/metrics (persona rating, confidence %, etc).
 * Animates once, when it first scrolls into view.
 */
export function AnimatedNumber({
  value,
  duration = 900,
  decimals = 0,
  suffix = '',
}: {
  value: number;
  duration?: number;
  decimals?: number;
  suffix?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-50px' });
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (!isInView) return;
    let raf: number;
    const start = performance.now();

    const tick = (now: number) => {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      setDisplay(value * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [isInView, value, duration]);

  return (
    <span ref={ref} className="tabular-nums">
      {display.toFixed(decimals)}
      {suffix}
    </span>
  );
}
