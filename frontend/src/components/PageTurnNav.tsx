import { motion, useReducedMotion } from 'motion/react';
import { pageTurnVariants, getReducedMotionVariants } from '../lib/motion';

interface PageTurnNavProps {
  gameweeks: number[];
  selected: number;
  fixtureCount: number;
  onSelect: (gw: number) => void;
}

/** The page-turn: neighbour folios, a ticking matchweek numeral, and leaf arrows. */
export default function PageTurnNav({ gameweeks, selected, fixtureCount, onSelect }: PageTurnNavProps) {
  const reduce = useReducedMotion();
  const variants = reduce ? getReducedMotionVariants(pageTurnVariants) : pageTurnVariants;
  const index = gameweeks.indexOf(selected);
  const hasPrev = index > 0;
  const hasNext = index < gameweeks.length - 1;
  const prevNeighbors = gameweeks.slice(Math.max(0, index - 3), index);
  const nextNeighbors = gameweeks.slice(index + 1, index + 4);

  return (
    <motion.div
      variants={variants}
      initial="hidden"
      animate="show"
      className="rule-double pt-6 pb-5"
    >
      <div className="flex items-center justify-center gap-5 sm:gap-8">
        <button
          type="button"
          onClick={() => hasPrev && onSelect(gameweeks[index - 1])}
          disabled={!hasPrev}
          className="btn-turn"
          aria-label="Previous matchweek"
        >
          <span aria-hidden="true" className="font-mono text-lg leading-none -mt-0.5">‹</span>
        </button>

        <div className="flex items-center gap-3 sm:gap-4">
          <div className="hidden sm:flex items-end gap-2">
            {prevNeighbors.map((gw) => (
              <button
                key={gw}
                type="button"
                onClick={() => onSelect(gw)}
                className="font-mono text-sm text-ink-faint hover:text-rubric transition-colors pb-1"
                aria-label={`Matchweek ${gw}`}
              >
                {String(gw).padStart(2, '0')}
              </button>
            ))}
          </div>

          <div className="flex flex-col items-center min-w-[7rem]">
            <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
              Matchweek
            </span>
            <span
              key={selected}
              className="folio-tick font-mono text-5xl sm:text-6xl font-semibold leading-none text-ink tnum"
              aria-label={`Matchweek ${selected}`}
            >
              {String(selected).padStart(2, '0')}
            </span>
            <span className="mt-1 font-mono text-[0.6875rem] uppercase tracking-wider-caps text-rubric">
              {fixtureCount} fixture{fixtureCount === 1 ? '' : 's'}
            </span>
          </div>

          <div className="hidden sm:flex items-end gap-2">
            {nextNeighbors.map((gw) => (
              <button
                key={gw}
                type="button"
                onClick={() => onSelect(gw)}
                className="font-mono text-sm text-ink-faint hover:text-rubric transition-colors pb-1"
                aria-label={`Matchweek ${gw}`}
              >
                {String(gw).padStart(2, '0')}
              </button>
            ))}
          </div>
        </div>

        <button
          type="button"
          onClick={() => hasNext && onSelect(gameweeks[index + 1])}
          disabled={!hasNext}
          className="btn-turn"
          aria-label="Next matchweek"
        >
          <span aria-hidden="true" className="font-mono text-lg leading-none -mt-0.5">›</span>
        </button>
      </div>
    </motion.div>
  );
}
