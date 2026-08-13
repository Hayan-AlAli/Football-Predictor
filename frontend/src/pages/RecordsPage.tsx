import { useEffect, useMemo, useState } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import Press from '../components/Press';
import OfflineSlate from '../components/OfflineSlate';
import EmptyState from '../components/EmptyState';
import TeamBadge from '../components/TeamBadge';
import { useData } from '../lib/data-context';
import { getResultEntries } from '../api/matches';
import { teamShort } from '../lib/teams';
import { scoreline } from '../lib/format';
import { getReducedMotionVariants, headVariants, ledgerVariants, staggerContainer } from '../lib/motion';
import type { ResultEntry } from '../types';

function useAllVerdicts(dates: string[]) {
  const [state, setState] = useState<{ key: string; entries: ResultEntry[] }>({ key: '', entries: [] });
  const datesKey = dates.join(',');
  useEffect(() => {
    let cancelled = false;
    if (!datesKey) return;
    (async () => {
      const res = await Promise.allSettled(dates.map((d) => getResultEntries(d)));
      if (cancelled) return;
      setState({
        key: datesKey,
        entries: res
          .filter((r) => r.status === 'fulfilled')
          .flatMap((r) => r.value),
      });
    })();
    return () => {
      cancelled = true;
    };
  }, [datesKey, dates]);
  return { entries: state.key === datesKey ? state.entries : [], loading: state.key !== datesKey };
}

/** The Records — every verdict kept against the actual result, hits and misses alike. */
export default function RecordsPage() {
  const { status, matches, reload } = useData();
  const reduce = useReducedMotion();
  const headV = reduce ? getReducedMotionVariants(headVariants) : headVariants;
  const staggerV = reduce ? getReducedMotionVariants(staggerContainer) : staggerContainer;
  const rowV = reduce ? getReducedMotionVariants(ledgerVariants) : ledgerVariants;

  const dateToGw = useMemo(() => {
    const byDate = new Map<string, number>();
    for (const m of matches) {
      if (m.gameweek != null) byDate.set(m.date, m.gameweek);
    }
    return byDate;
  }, [matches]);

  const candidateDates = useMemo(() => {
    const set = new Set(matches.map((m) => m.date));
    return [...set].sort().slice(-5).reverse();
  }, [matches]);

  const { entries, loading } = useAllVerdicts(candidateDates);

  const grouped = useMemo(() => {
    const map = new Map<number, ResultEntry[]>();
    for (const e of entries) {
      const gw = dateToGw.get(e.match.date) ?? 0;
      const list = map.get(gw) ?? [];
      list.push(e);
      map.set(gw, list);
    }
    return [...map.entries()].sort((a, b) => a[0] - b[0]).reverse();
  }, [entries, dateToGw]);

  const correct = entries.filter((e) => e.status === 'CORRECT').length;
  const incorrect = entries.filter((e) => e.status === 'INCORRECT').length;
  const pending = entries.filter((e) => e.status === 'PENDING').length;
  const decided = correct + incorrect;
  const accuracy = decided > 0 ? Math.round((correct / decided) * 100) : null;

  return (
    <div className="mx-auto max-w-3xl px-4 pb-4">
      <motion.div variants={headV} initial="hidden" animate="show" className="pt-8">
        <h1 className="mt-1 font-sans text-2xl sm:text-3xl font-extrabold uppercase tracking-caps text-ink">
          The Records
        </h1>
        <p className="mt-2 font-serif text-sm italic text-ink-soft sm:text-base">
          The evening press keeps every verdict against the actual result. Hits and misses are both printed here —
          the record is honest by design.
        </p>
      </motion.div>

      {status === 'loading' && <Press />}
      {status === 'offline' && (
        <OfflineSlate
          message="The record cannot be consulted while the backend is unreachable."
          onRetry={reload}
        />
      )}

      {status === 'online' && (
        <>
          {loading ? (
            <Press phase={1} />
          ) : entries.length === 0 ? (
            <div className="mt-6">
              <EmptyState
                title="No verdicts recorded yet"
                note="The evening press has not run, or no results could be fetched. When it runs, each matchweek's predictions are kept here against the actual results."
              />
            </div>
          ) : (
            <>
              {/* Summary */}
              <div className="rule-draw mt-6 flex flex-wrap items-center justify-between gap-2 py-3">
                <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
                  The record so far
                </span>
                <span className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[0.6875rem] uppercase tracking-wider-caps">
                  <span className="text-ledger">✓ {correct} correct</span>
                  <span className="text-rubric">✗ {incorrect} incorrect</span>
                  {pending > 0 && <span className="text-ink-faint">{pending} pending</span>}
                  {accuracy != null && <span className="chip">{decided} decided · {accuracy}%</span>}
                </span>
              </div>

              {/* The verdict ledger */}
              {grouped.map(([gw, group]) => (
                <section key={gw} className="mt-4">
                  <h2 className="rule-double pt-3 font-sans text-lg font-bold uppercase tracking-caps text-ink">
                    <span className="font-mono text-rubric">Matchweek {gw}</span>
                  </h2>
                  <motion.div variants={staggerV} initial="hidden" animate="show">
                    {group.map((entry) => {
                      const m = entry.match;
                      const home = m.home_team_info ?? m.home_team;
                      const away = m.away_team_info ?? m.away_team;
                      const pred = m.prediction;
                      const actualScore = entry.actual?.score ? scoreline(entry.actual.score) : null;
                      return (
                        <motion.div
                          key={m.id ?? `${m.home_team}-${m.away_team}`}
                          variants={rowV}
                          initial="hidden"
                          animate="show"
                          className="grid grid-cols-[auto_1fr] items-center gap-x-3 border-t border-paper-line py-3.5 sm:grid-cols-[1fr_auto_auto_auto]"
                        >
                          <span className="flex items-center gap-2 font-sans text-sm font-bold uppercase tracking-caps text-ink sm:justify-start">
                            <TeamBadge team={m.home_team} info={m.home_team_info} size="sm" />
                            {teamShort(home)}
                            <span className="font-mono font-normal lowercase text-ink-faint">vs</span>
                            {teamShort(away)}
                            <TeamBadge team={m.away_team} info={m.away_team_info} size="sm" />
                          </span>
                          <span className="flex items-center gap-2 justify-self-end sm:justify-self-auto font-mono text-xs text-ink-soft tnum">
                            <span className="hidden sm:inline uppercase tracking-wider-caps text-[0.625rem] text-ink-faint">Called</span>
                            {pred ? `${pred.winner === 'Draw' ? 'Draw' : teamShort(pred.winner ?? '')} ${scoreline(pred.score)}` : '—'}
                          </span>
                          <span className="justify-self-end font-mono text-xs font-semibold text-ink tnum">
                            {actualScore ?? <span className="text-ink-faint">—</span>}
                          </span>
                          <span className="justify-self-end">
                            {entry.status === 'CORRECT' && (
                              <span className="stamp" style={{ background: 'var(--ledger)' }}>
                                ✓ Correct
                              </span>
                            )}
                            {entry.status === 'INCORRECT' && (
                              <span className="stamp">✗ Incorrect</span>
                            )}
                            {entry.status === 'PENDING' && (
                              <span className="chip">Pending</span>
                            )}
                          </span>
                        </motion.div>
                      );
                    })}
                  </motion.div>
                </section>
              ))}
            </>
          )}
        </>
      )}
    </div>
  );
}
