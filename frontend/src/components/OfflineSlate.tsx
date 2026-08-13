import { motion, useReducedMotion } from 'motion/react';

interface OfflineSlateProps {
  message: string;
  onRetry: () => void;
}

/** The press is unreachable — an honest binding miss, with a retry. */
export default function OfflineSlate({ message, onRetry }: OfflineSlateProps) {
  const reduce = useReducedMotion();

  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      role="alert"
      className="mt-10"
    >
      <div className="plate p-6 sm:p-8 text-center">
        <p className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-rubric">Binding miss</p>
        <h2 className="mt-2 font-sans text-xl font-bold uppercase tracking-caps text-ink">
          The press is offline
        </h2>
        <p className="mx-auto mt-2 max-w-md font-serif text-sm italic text-ink-soft">{message}</p>
        <button type="button" onClick={onRetry} className="btn-print mt-6">
          Retry the press
        </button>
      </div>
    </motion.div>
  );
}
