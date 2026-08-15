import { useParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import EmptyState from '../components/EmptyState';
import { getReducedMotionVariants, headVariants } from '../lib/motion';

/** Team detail — a club's season record, form, and head-to-head history. */
export default function TeamDetailPage() {
  const reduce = useReducedMotion();
  const headV = reduce ? getReducedMotionVariants(headVariants) : headVariants;
  const { teamName } = useParams<{ teamName: string }>();
  const name = teamName ? decodeURIComponent(teamName) : '';

  return (
    <div className="mx-auto max-w-3xl px-4 pb-4">
      <motion.div variants={headV} initial="hidden" animate="show" className="pt-8">
        <h1 className="mt-1 font-sans text-2xl sm:text-3xl font-extrabold uppercase tracking-caps text-ink">
          {name}
        </h1>
        <p className="mt-2 font-serif text-sm italic text-ink-soft sm:text-base">
          The club's page in the almanack.
        </p>
      </motion.div>
      <EmptyState
        title="Still on the presses"
        note="The full team page is being typeset. It will print the season record, current form, elo history, and head-to-head against selected opponents."
      />
    </div>
  );
}