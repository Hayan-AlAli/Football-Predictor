import { useEffect, useMemo, useState } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import PageTurnNav from '../components/PageTurnNav';
import LedgerRow from '../components/LedgerRow';
import Press from '../components/Press';
import OfflineSlate from '../components/OfflineSlate';
import EmptyState from '../components/EmptyState';
import { useData } from '../lib/data-context';
import { useBook } from '../lib/book';
import { useThisWeek } from '../lib/gameweek';
import { getResultEntries } from '../api/matches';
import { sortMatchesByDate } from '../lib/format';
import { staggerContainer, getReducedMotionVariants } from '../lib/motion';
import type { ResultEntry } from '../types';

function useVerdicts(dates: string[]) {
  const [state, setState] = useState<{ key: string; entries: ResultEntry[] }>({
    key: '',
    entries: [],
  });
  const key = dates.join(',');
  useEffect(() => {
    let cancelled = false;
    if (!key) return;
    (async () => {
      const res = await Promise.allSettled(dates.map((d) => getResultEntries(d)));
      if (cancelled) return;
      setState({
        key,
        entries: res
          .filter((r) => r.status === 'fulfilled')
          .flatMap((r) => r.value),
      });
    })();
    return () => {
      cancelled = true;
    };
  }, [key, dates]);
  return {
    entries: state.entries,
    loading: key ? state.key !== key : false,
  };
}

/** The matchday page: this matchweek's ledger, printed by the model. */
export default function MatchdayPage() {
  const { status, matches, gameweeks, season, reload } = useData();
  const reduce = useReducedMotion();
  const { selectedGameweek: selected, setSelectedGameweek: setSelected } = useBook();

  const thisWeekFromHook = useThisWeek();

  const view = selected ?? thisWeekFromHook;

  const weekMatches = useMemo(
    () => sortMatchesByDate(matches.filter((m) => m.gameweek === view)),
    [matches, view]
  );
  const weekDates = useMemo(() => [...new Set(weekMatches.map((m) => m.date))], [weekMatches]);
  const { entries: verdicts, loading: verdictsLoading } = useVerdicts(weekDates);

  const correct = verdicts.filter((v) => v.status === 'CORRECT').length;
  const incorrect = verdicts.filter((v) => v.status === 'INCORRECT').length;
  const pending = verdicts.filter((v) => v.status === 'PENDING').length;
  const decided = correct + incorrect;
  const accuracy = decided > 0 ? Math.round((correct / decided) * 100) : null;

  const staggerV = reduce ? getReducedMotionVariants(staggerContainer) : staggerContainer;

  return (
    <div className="mx-auto max-w-5xl px-4 pb-4">
      {/* Title band */}
      <div className="pt-8">
        <div className="flex items-end justify-between gap-4">
          <h1 className="font-sans text-2xl sm:text-3xl font-extrabold uppercase tracking-caps text-ink">
            The Matchday Almanack
          </h1>
          {season && <span className="chip hidden sm:inline-block">Season {season}</span>}
        </div>
        <p className="mt-1.5 font-serif text-sm italic text-ink-soft sm:text-base">
          Printed by the model: every fixture of this matchweek, set as the season's ledger.
        </p>
      </div>

      {status === 'loading' && <Press />}
      {status === 'offline' && (
        <OfflineSlate
          message="The backend could not be reached, so the ledger cannot be set. Check that the press (FastAPI) is running."
          onRetry={reload}
        />
      )}

      {status === 'online' && gameweeks.length > 0 && view != null && (
        <>
          <PageTurnNav
            gameweeks={gameweeks}
            selected={view}
            fixtureCount={weekMatches.length}
            onSelect={setSelected}
          />
          {view === thisWeekFromHook && thisWeekFromHook != null && (
            <div className="flex justify-center pb-2">
              <span className="stamp" style={{ background: 'var(--rubric)' }}>
                This week
              </span>
            </div>
          )}

          {/* The record of this matchweek */}
          <div className="rule-draw flex flex-wrap items-center justify-between gap-2 py-3" aria-live="polite">
            <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
              The record of this matchweek
            </span>
            {verdicts.length > 0 ? (
              <span
                className={`flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[0.6875rem] uppercase tracking-wider-caps ${
                  verdictsLoading ? 'opacity-60' : ''
                }`}
              >
                <span className="text-ledger">✓ {correct} correct</span>
                <span className="text-rubric">✗ {incorrect} incorrect</span>
                {pending > 0 && <span className="text-ink-faint">{pending} pending</span>}
                {accuracy != null && <span className="chip">{decided} decided · {accuracy}%</span>}
                {verdictsLoading && (
                  <>
                    <span className="text-ink-faint" aria-hidden="true">·</span>
                    <span className="text-rubric">setting…</span>
                  </>
                )}
              </span>
            ) : verdictsLoading ? (
              <span className="font-serif text-xs italic text-ink-faint" role="status">
                Comparing the evening's results…
              </span>
            ) : (
              <span className="font-serif text-xs italic text-ink-faint">
                No verdicts recorded yet — the evening press compares these predictions against results.
              </span>
            )}
          </div>

          {weekMatches.length === 0 ? (
            <EmptyState
              title="No fixtures set for this matchweek"
              note="The press has nothing printed on this page of the ledger."
            />
          ) : (
            <motion.div
              variants={staggerV}
              initial="hidden"
              animate="show"
              key={view}
              className="rule-double page-turn-in pb-8"
            >
              {/* Column heads */}
              <div className="hidden sm:grid grid-cols-[2.75rem_1fr_10rem_1fr_auto] gap-x-3 px-2 pb-1 pt-3">
                <span className="font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">Time</span>
                <span className="font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">Home</span>
                <span className="text-center font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">
                  The line · score
                </span>
                <span className="font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">Away</span>
                <span className="text-right font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">Call</span>
              </div>

              <div className="pb-6">
                {weekMatches.map((m, i) => (
                  <LedgerRow key={m.id} match={m} index={i} />
                ))}
              </div>
            </motion.div>
          )}
        </>
      )}

      {status === 'online' && gameweeks.length === 0 && (
        <EmptyState
          title="The ledger is empty"
          note="No matchweeks have been printed yet. Run the morning press to generate predictions."
        />
      )}
    </div>
  );
}
