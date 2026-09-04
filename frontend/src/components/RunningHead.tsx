import { NavLink, useLocation } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import { headVariants, getReducedMotionVariants } from '../lib/motion';
import { gameweekLabel } from '../lib/format';
import { useBook } from '../lib/book';
import { useThisWeek } from '../lib/gameweek';

const SECTIONS = [
  { to: '/', label: 'MATCHDAY', folio: (gw?: number) => (gw == null ? '1' : gameweekLabel(gw)) },
  { to: '/method', label: 'METHOD', folio: () => '2' },
  { to: '/records', label: 'RECORDS', folio: () => '3' },
  { to: '/teams', label: 'TEAMS INDEX', folio: () => '4' },
  { to: '/forecast', label: 'FORECAST', folio: () => '5' },
  { to: '/calibration', label: 'CALIBRATION', folio: () => '6' },
] as const;

interface RunningHeadProps {
  gameweek?: number;
  isCurrentWeek?: boolean;
}

/** The almanack's running head: masthead rule, section nav, folio. */
export default function RunningHead({ gameweek, isCurrentWeek }: RunningHeadProps) {
  const reduce = useReducedMotion();
  const variants = reduce ? getReducedMotionVariants(headVariants) : headVariants;
  const location = useLocation();
  // The head is rendered by App (not MatchdayPage), so when no explicit prop
  // is passed, derive the same selected === thisWeek expression here — gated
  // to the matchday leaf so other sections' folios are unaffected.
  const { selectedGameweek } = useBook();
  const thisWeek = useThisWeek();
  const showStamp =
    isCurrentWeek ?? (location.pathname === '/' && thisWeek != null && (selectedGameweek ?? thisWeek) === thisWeek);

  const activeSection =
    SECTIONS.find((s) =>
      s.to === '/' ? location.pathname === '/' : location.pathname.startsWith(s.to)
    ) ?? SECTIONS[0];

  return (
    <motion.header
      variants={variants}
      initial="hidden"
      animate="show"
      className="sticky top-0 z-40 bg-paper/92 backdrop-blur-sm border-b border-paper-line"
    >
      <div className="mx-auto max-w-5xl px-4">
        <div className="flex items-center justify-between gap-4 py-2.5">
          <NavLink to="/" className="group flex min-w-0 items-center gap-2.5 no-underline">
            <span className="stamp group-hover:bg-ink transition-colors" aria-hidden="true">
              FP
            </span>
            <span className="truncate font-sans text-[0.8125rem] font-extrabold uppercase tracking-caps text-ink group-hover:text-rubric transition-colors">
              The Matchday Almanack
            </span>
          </NavLink>
          <span className="hidden sm:block font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
            Premier League · the model prints
          </span>
        </div>

        <div className="flex items-end justify-between gap-4 pb-2.5">
          <nav aria-label="Book sections" className="flex items-center gap-4 sm:gap-6 overflow-x-auto">
            {SECTIONS.map((s) => (
              <NavLink
                key={s.to}
                to={s.to}
                end={s.to === '/'}
                className={({ isActive }) =>
                  `whitespace-nowrap font-mono text-[0.75rem] uppercase tracking-wider-caps py-3 no-underline transition-colors min-h-[44px] flex items-center ${
                    isActive
                      ? 'text-rubric border-b-2 border-rubric font-semibold'
                      : 'text-ink-soft border-b-2 border-transparent hover:text-ink'
                  }`
                }
              >
                {s.label}
              </NavLink>
            ))}
          </nav>
          <span className="flex items-baseline gap-1.5 shrink-0" aria-label={`Page ${activeSection.folio(gameweek)}`}>
            <span className="hidden md:inline font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
              folio
            </span>
            <span key={activeSection.to + gameweek} className="folio-tick font-mono text-lg font-semibold text-ink tnum">
              {activeSection.folio(gameweek)}
            </span>
            {showStamp && (
              <span className="stamp" style={{ background: 'var(--rubric)' }}>
                This week
              </span>
            )}
          </span>
        </div>
      </div>
    </motion.header>
  );
}
