import { motion, useReducedMotion } from 'motion/react';
import EmptyState from '../components/EmptyState';
import { getReducedMotionVariants, headVariants } from '../lib/motion';

/** The Forecast — the season's full simulation printed in odds and points ranges. */
export default function ForecastPage() {
  const reduce = useReducedMotion();
  const headV = reduce ? getReducedMotionVariants(headVariants) : headVariants;

  return (
    <div className="mx-auto max-w-3xl px-4 pb-4">
      <motion.div variants={headV} initial="hidden" animate="show" className="pt-8">
        <h1 className="mt-1 font-sans text-2xl sm:text-3xl font-extrabold uppercase tracking-caps text-ink">
          The Forecast
        </h1>
        <p className="mt-2 font-serif text-sm italic text-ink-soft sm:text-base">
          The model runs the remainder of the season many thousand times and prints the odds.
        </p>
      </motion.div>
      <EmptyState
        title="Still on the presses"
        note="The full forecast page is being typeset. It will print the projected table, title odds, and remaining-fixture probabilities."
      />
    </div>
  );
}