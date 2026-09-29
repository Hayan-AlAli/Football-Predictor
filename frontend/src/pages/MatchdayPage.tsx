import { useMemo } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import FixtureCard from '../components/FixtureCard';
import RecordPanel from '../components/RecordPanel';
import Press from '../components/Press';
import OfflineSlate from '../components/OfflineSlate';
import EmptyState from '../components/EmptyState';
import { useData } from '../lib/data-context';
import { useBook } from '../lib/book';
import { useThisWeek } from '../lib/gameweek';
import { resultEntries } from '../lib/data-utils';
import { gameweekLabel, kickoffDay, sortMatchesByDate } from '../lib/format';
import { staggerContainer, getReducedMotionVariants } from '../lib/motion';
import type { ResultEntry } from '../types';

/** The matchday page: this matchweek's fixtures as cards, with the model's record alongside. */
export default function MatchdayPage() {
  const { status, matches, gameweeks, reload } = useData();
  const reduce = useReducedMotion();
  const { selectedGameweek: selected, setSelectedGameweek: setSelected } = useBook();

  const thisWeekFromHook = useThisWeek();

  const view = selected ?? thisWeekFromHook;

  const weekMatches = useMemo(
    () => sortMatchesByDate(matches.filter((m) => m.gameweek === view)),
    [matches, view]
  );
  const weekDates = useMemo(() => [...new Set(weekMatches.map((m) => m.date))], [weekMatches]);
  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const verdicts = useMemo(() => resultEntries(weekMatches, today), [weekMatches, today]);
  const verdictsLoading = false;
  const verdictByMatch = useMemo(() => new Map<string, ResultEntry>(verdicts.map((v) => [v.match.id, v])), [verdicts]);

  const correct = verdicts.filter((v) => v.status === 'CORRECT').length;
  const incorrect = verdicts.filter((v) => v.status === 'INCORRECT').length;
  const pending = verdicts.filter((v) => v.status === 'PENDING').length;
  const decided = correct + incorrect;
  const accuracy = decided > 0 ? Math.round((correct / decided) * 100) : null;

  const staggerV = reduce ? getReducedMotionVariants(staggerContainer) : staggerContainer;

  const index = view != null ? gameweeks.indexOf(view) : -1;
  const prev = index > 0 ? gameweeks[index - 1] : null;
  const next = index >= 0 && index < gameweeks.length - 1 ? gameweeks[index + 1] : null;
  const firstDate = weekDates[0];
  const lastDate = weekDates[weekDates.length - 1];
  const dateRange = firstDate
    ? firstDate === lastDate
      ? kickoffDay(firstDate)
      : `${kickoffDay(firstDate)} – ${kickoffDay(lastDate)}`
    : null;

  return (
    <div className="mx-auto max-w-6xl px-4 pb-8 sm:px-6">
      {status === 'loading' && <Press />}
      {status === 'offline' && (
        <OfflineSlate
          message="The backend could not be reached, so the fixtures cannot be loaded. Check that the FastAPI server is running."
          onRetry={reload}
        />
      )}

      {status === 'online' && gameweeks.length > 0 && view != null && (
        <div className="grid gap-8 pt-8 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="flex min-w-0 flex-col gap-5">
            {/* Title + matchweek nav */}
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div className="flex flex-col gap-1.5">
                <span className="font-mono text-xs uppercase tracking-[0.1em] text-chalk-faint">
                  {weekMatches.length} fixture{weekMatches.length === 1 ? '' : 's'}
                  {dateRange ? ` · ${dateRange}` : ''}
                </span>
                <h1 key={view} className="rise-in font-display text-[3.5rem] font-black uppercase leading-[0.85] text-chalk sm:text-[4.5rem]">
                  Matchweek {gameweekLabel(view)}
                </h1>
              </div>
              <nav aria-label="Matchweeks" className="flex items-center gap-1.5">
                <button
                  type="button"
                  className="btn-turn font-mono text-xs tracking-[0.08em]"
                  onClick={() => prev != null && setSelected(prev)}
                  disabled={prev == null}
                  aria-label={prev != null ? `Previous matchweek, ${prev}` : 'No previous matchweek'}
                >
                  ‹ {prev != null ? `GW${prev}` : ''}
                </button>
                {thisWeekFromHook != null && view !== thisWeekFromHook && (
                  <button
                    type="button"
                    className="btn-turn font-mono text-xs tracking-[0.08em]"
                    onClick={() => setSelected(thisWeekFromHook)}
                  >
                    This week
                  </button>
                )}
                <button
                  type="button"
                  className="btn-turn font-mono text-xs tracking-[0.08em]"
                  onClick={() => next != null && setSelected(next)}
                  disabled={next == null}
                  aria-label={next != null ? `Next matchweek, ${next}` : 'No next matchweek'}
                >
                  {next != null ? `GW${next}` : ''} ›
                </button>
              </nav>
            </div>

            {/* This matchweek's record */}
            <div className="flex flex-wrap items-center justify-between gap-2 border-y border-line py-2.5" aria-live="polite">
              <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-faint">
                This matchweek's record
              </span>
              {verdicts.length > 0 ? (
                <span
                  className={`flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[0.6875rem] uppercase tracking-wider-caps ${
                    verdictsLoading ? 'opacity-60' : ''
                  }`}
                >
                  <span className="text-chalk">✓ {correct} right</span>
                  <span className="text-chalk-faint">✗ {incorrect} wrong</span>
                  {pending > 0 && <span className="text-chalk-faint">{pending} pending</span>}
                  {accuracy != null && <span className="chip">{decided} decided · {accuracy}%</span>}
                </span>
              ) : verdictsLoading ? (
                <span className="text-xs italic text-chalk-faint" role="status">
                  Checking results…
                </span>
              ) : (
                <span className="text-xs italic text-chalk-faint">
                  No results yet — verdicts appear after the evening job compares predictions with results.
                </span>
              )}
            </div>

            {weekMatches.length === 0 ? (
              <EmptyState
                title="No fixtures for this matchweek"
                note="Nothing has been predicted for this matchweek yet."
              />
            ) : (
              <motion.div
                variants={staggerV}
                initial="hidden"
                animate="show"
                key={view}
                className="grid gap-5 sm:grid-cols-2"
              >
                {weekMatches.map((m) => (
                  <FixtureCard key={m.id} match={m} verdict={verdictByMatch.get(m.id)} />
                ))}
              </motion.div>
            )}
          </div>

          <div className="lg:sticky lg:top-24 lg:self-start">
            <RecordPanel />
          </div>
        </div>
      )}

      {status === 'online' && gameweeks.length === 0 && (
        <EmptyState
          title="No matchweeks yet"
          note="No predictions have been generated yet. Run the morning job to generate them."
        />
      )}
    </div>
  );
}
