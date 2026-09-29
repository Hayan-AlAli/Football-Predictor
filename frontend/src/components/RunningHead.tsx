import { NavLink, useLocation } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import { headVariants, getReducedMotionVariants } from '../lib/motion';
import { gameweekLabel } from '../lib/format';
import { useBook } from '../lib/book';
import { useThisWeek } from '../lib/gameweek';
import TouchlineMark from './TouchlineMark';

const SECTIONS = [
  { to: '/', label: 'Matchday' },
  { to: '/method', label: 'Method' },
  { to: '/records', label: 'Records' },
  { to: '/teams', label: 'Teams' },
  { to: '/forecast', label: 'Forecast' },
  { to: '/calibration', label: 'Calibration' },
] as const;

interface RunningHeadProps {
  gameweek?: number;
  isCurrentWeek?: boolean;
}

function SectionLinks({ className }: { className: string }) {
  return (
    <nav aria-label="Sections" className={className}>
      {SECTIONS.map((s) => (
        <NavLink
          key={s.to}
          to={s.to}
          end={s.to === '/'}
          className={({ isActive }) =>
            `flex min-h-[44px] items-center whitespace-nowrap border-b-[3px] font-display text-[1.0625rem] font-bold uppercase tracking-caps no-underline transition-colors ${
              isActive ? 'border-amber text-chalk' : 'border-transparent text-chalk-faint hover:text-chalk'
            }`
          }
        >
          {s.label}
        </NavLink>
      ))}
    </nav>
  );
}

/** The desk's masthead: mark, wordmark, sections, and the matchweek on view. */
export default function RunningHead({ gameweek, isCurrentWeek }: RunningHeadProps) {
  const reduce = useReducedMotion();
  const variants = reduce ? getReducedMotionVariants(headVariants) : headVariants;
  const location = useLocation();
  const { selectedGameweek } = useBook();
  const thisWeek = useThisWeek();
  const showThisWeek =
    isCurrentWeek ?? (location.pathname === '/' && thisWeek != null && (selectedGameweek ?? thisWeek) === thisWeek);

  return (
    <motion.header
      variants={variants}
      initial="hidden"
      animate="show"
      className="sticky top-0 z-40 bg-ground/95 backdrop-blur-sm"
    >
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="flex items-center justify-between gap-6">
          <div className="flex min-w-0 items-center gap-8 xl:gap-10">
            <NavLink to="/" className="group flex min-h-[56px] shrink-0 items-center gap-3 no-underline" aria-label="Touchline — matchday">
              <TouchlineMark size={30} />
              <span className="font-display text-[1.875rem] font-black leading-none text-chalk">TOUCHLINE</span>
              <span className="hidden border border-line-strong px-1.5 py-0.5 font-mono text-[0.625rem] tracking-wider-caps text-chalk-faint xl:inline">
                MATCHDAY DESK
              </span>
            </NavLink>
            <SectionLinks className="hidden items-center gap-6 lg:flex" />
          </div>
          <span className="hidden shrink-0 items-center gap-2 font-mono text-xs text-chalk-faint md:flex">
            <span className="h-1.5 w-1.5 rounded-full bg-amber" aria-hidden="true" />
            {gameweek != null ? `MATCHWEEK ${gameweekLabel(gameweek)}` : 'PREMIER LEAGUE'}
            {showThisWeek && <span className="chip ml-1">This week</span>}
          </span>
        </div>
        <SectionLinks className="-mb-px flex items-center gap-6 overflow-x-auto lg:hidden" />
      </div>
      <div className="h-1 bg-amber" aria-hidden="true" />
    </motion.header>
  );
}
