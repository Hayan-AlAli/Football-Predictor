import { useReducedMotion, type Variants } from 'motion/react';

/**
 * Shared motion presets — Touchline
 * Print registers: rules draw, stamps press, folios tick, pages turn.
 */

// The book's motion curve
const print = {
  duration: 0.42,
  ease: [0.22, 1, 0.36, 1] as const,
};

// The stamp's press curve
const press = {
  type: 'spring' as const,
  stiffness: 380,
  damping: 22,
  mass: 0.7,
};

// A ledger row drawing itself in, staggered down the page
const ledgerVariants: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: {
    opacity: 1,
    y: 0,
    transition: print,
  },
  exit: {
    opacity: 0,
    transition: { duration: 0.16, ease: 'easeOut' },
  },
};

// The rubric stamp pressing onto the page
const stampVariants: Variants = {
  hidden: { opacity: 0, scale: 0.82 },
  show: {
    opacity: 1,
    scale: 1,
    transition: press,
  },
};

// Running-head furniture
const headVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { duration: 0.35 },
  },
};

// Stagger container for ledger rows (50ms, print-like)
const staggerContainer: Variants = {
  hidden: {},
  show: {
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1,
    },
  },
  exit: {
    transition: { staggerChildren: 0.02, staggerDirection: -1 },
  },
};

// Reduced motion: the book stands still
const reducedCache = new Map<Variants, Variants>();

const getReducedMotionVariants = (variants: Variants): Variants => {
  const cached = reducedCache.get(variants);
  if (cached) return cached;

  const reduced: Variants = {};
  for (const [key, value] of Object.entries(variants)) {
    if (typeof value === 'object' && value !== null && 'transition' in value) {
      reduced[key] = { ...value, transition: { duration: 0 } };
    } else {
      reduced[key] = value;
    }
  }
  reducedCache.set(variants, reduced);
  return reduced;
};

/** The shared presets, stilled when the visitor prefers reduced motion. */
export function useMotionVariants() {
  const reduce = useReducedMotion();
  const pick = (variants: Variants) => (reduce ? getReducedMotionVariants(variants) : variants);
  return {
    head: pick(headVariants),
    ledger: pick(ledgerVariants),
    stamp: pick(stampVariants),
    stagger: pick(staggerContainer),
  };
}
