import { motion, useReducedMotion } from 'motion/react';

const PHASES = ['Fetching fixtures', "Fetching the evening's results", 'Pressing the ledger'];

/** The print press at work — loader. */
export default function Press({ phase = 0 }: { phase?: number }) {
  const reduce = useReducedMotion();

  return (
    <motion.div
      initial={reduce ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="py-16"
      role="status"
      aria-live="polite"
    >
      <div className="mx-auto max-w-md text-center">
        <p className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-rubric">
          The press is running
        </p>
        <h2 className="mt-2 font-sans text-xl font-bold uppercase tracking-caps text-ink">
          Setting the ledger
        </h2>
        <p className="mt-1 font-serif text-sm italic text-ink-soft">{PHASES[phase % PHASES.length]}</p>
        <div className="press-track mt-6" aria-hidden="true">
          <div className="press-fill" />
        </div>
      </div>
    </motion.div>
  );
}
