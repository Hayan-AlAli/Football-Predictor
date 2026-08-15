import { motion, useReducedMotion } from 'motion/react';
import EmptyState from '../components/EmptyState';
import { getReducedMotionVariants, headVariants } from '../lib/motion';

/** Calibration — how the model's printed probabilities square with what actually happened. */
export default function CalibrationPage() {
  const reduce = useReducedMotion();
  const headV = reduce ? getReducedMotionVariants(headVariants) : headVariants;

  return (
    <div className="mx-auto max-w-3xl px-4 pb-4">
      <motion.div variants={headV} initial="hidden" animate="show" className="pt-8">
        <h1 className="mt-1 font-sans text-2xl sm:text-3xl font-extrabold uppercase tracking-caps text-ink">
          Calibration
        </h1>
        <p className="mt-2 font-serif text-sm italic text-ink-soft sm:text-base">
          The honesty ledger of the model: predicted odds against actual frequencies.
        </p>
      </motion.div>
      <EmptyState
        title="Still on the presses"
        note="The full calibration page is being typeset. It will print Brier score, accuracy, and the binned calibration record."
      />
    </div>
  );
}