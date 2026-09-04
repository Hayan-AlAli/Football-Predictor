import { useEffect, useMemo, useState } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import Press from '../components/Press';
import OfflineSlate from '../components/OfflineSlate';
import EmptyState from '../components/EmptyState';
import TeamBadge from '../components/TeamBadge';
import { useData } from '../lib/data-context';
import { getResultEntries, getResultDates } from '../api/matches';
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
  }, [datesKey]);
  return { entries: state.key === datesKey ? state.entries : [], loading: state.key !== datesKey };
}

/** The Records — every verdict kept against the actual result, hits and misses alike. */
export default function RecordsPage() {
  const { status, matches, reload } = useData();
  const reduce = useReducedMotion();
  const headV = reduce ? getReducedMotionVariants(headVariants) : headVariants;
  const staggerV = reduce ? getReducedMotionVariants(staggerContainer) : staggerContainer;
  const rowV = reduce ? getReducedMotionVariants(ledgerVariants) : ledgerVariants;

  const [resultDates, setResultDates] = useState<string[]>([]);
  const [resultDatesLoading, setResultDatesLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const dates = await getResultDates();
        if (!cancelled) {
          setResultDates(dates);
          setResultDatesLoading(false);
        }
      } catch {
        if (!cancelled) setResultDatesLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const dateToGw = useMemo(() => {
    const byDate = new Map<string, number>();
    for (const m of matches) {
      if (m.gameweek != null) byDate.set(m.date, m.gameweek);
    }
    return byDate;
  }, [matches]);

  const candidateDates = useMemo(() => {
    return resultDates;
  }, [resultDates]);

  const { entries, loading } = useAllVerdicts(candidateDates);

  const grouped = useMemo(() => {
    const map = new Map<string, { gw: number | null; date: string; list: ResultEntry[] }>();
    for (const e of entries) {
      const date = e.match.date;
      const gw = dateToGw.get(date) ?? null;
      const key = gw != null ? `gw-${gw}` : `date-${date}`;
      const group = map.get(key) ?? { gw, date, list: [] };
      group.list.push(e);
      // Keep the earliest date as the group's representative date.
      if (date < group.date) group.date = date;
      map.set(key, group);
    }
    return [...map.values()].sort((a, b) =>
      a.gw != null && b.gw != null ? b.gw - a.gw : b.date.localeCompare(a.date)
    );
  }, [entries, dateToGw]);

  const correct = entries.filter((e) => e.status === 'CORRECT').length;
  const incorrect = entries.filter((e) => e.status === 'INCORRECT').length;
  const pending = entries.filter((e) => e.status === 'PENDING').length;
  const decided = correct + incorrect;
  const accuracy = decided > 0 ? Math.round((correct / decided) * 100) : null;

  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    if (reduce) return;
    if (grouped.length === 0) return;
    const observer = new IntersectionObserver(
      (observed) => {
        for (const entry of observed) {
          if (entry.isIntersecting) setActiveId(entry.target.id);
        }
      },
      { rootMargin: '-40% 0px -55% 0px' }
    );
    for (const group of grouped) {
      const id = group.gw != null ? `gw-${group.gw}` : `date-${group.date}`;
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [grouped, reduce]);

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
          {loading || resultDatesLoading ? (
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
              <nav aria-label="Index of matchweeks" className="scroll-smooth-motion sticky top-0 z-10 -mx-4 border-y border-paper-line bg-paper px-4 py-2">
                <span className="font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">Index</span>
                <span className="ml-3 inline-flex flex-wrap gap-x-3 gap-y-1">
                  {grouped.map((group) => {
                    const id = group.gw != null ? `gw-${group.gw}` : `date-${group.date}`;
                    const label = group.gw != null ? `${group.gw}` : group.date;
                    return (
                      <a
                        key={id}
                        href={`#${id}`}
                        data-index-link={id}
                        className={`font-mono text-[0.625rem] uppercase tracking-widest hover:text-rubric ${activeId === id ? 'text-rubric' : 'text-ink-soft'}`}
                      >
                        {label}
                      </a>
                    );
                  })}
                </span>
              </nav>
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
              {grouped.map((group) => {
                const sectionId = group.gw != null ? `gw-${group.gw}` : `date-${group.date}`;
                const groupCorrect = group.list.filter((e) => e.status === 'CORRECT').length;
                const groupIncorrect = group.list.filter((e) => e.status === 'INCORRECT').length;
                return (
                <section key={group.gw != null ? `gw-${group.gw}` : `date-${group.date}`} id={sectionId} className="mt-4" style={{ contentVisibility: 'auto' }}>
                  <h2 className="rule-double flex items-baseline justify-between gap-2 pt-3 font-sans text-lg font-bold uppercase tracking-caps text-ink">
                    {group.gw != null ? (
                      <span className="font-mono text-rubric">Matchweek {group.gw}</span>
                    ) : (
                      <span className="font-mono text-rubric">{group.date}</span>
                    )}
                    {(groupCorrect > 0 || groupIncorrect > 0) && (
                      <span className="font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">
                        {groupCorrect} correct · {groupIncorrect} incorrect
                      </span>
                    )}
                  </h2>
                  <motion.div variants={staggerV} initial="hidden" animate="show">
                    {group.list.map((entry) => {
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
                          className="border-t border-paper-line py-3.5"
                        >
                          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                            <span className="flex items-center gap-1.5 font-sans text-sm font-bold uppercase tracking-caps text-ink">
                              <TeamBadge team={m.home_team} info={m.home_team_info} size="sm" />
                              {teamShort(home)}
                              <span className="font-mono font-normal lowercase text-ink-faint">vs</span>
                              {teamShort(away)}
                              <TeamBadge team={m.away_team} info={m.away_team_info} size="sm" />
                            </span>
                          </div>
                          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
                            <span className="flex items-center gap-2 font-mono text-xs text-ink-soft tnum">
                              <span className="hidden sm:inline uppercase tracking-wider-caps text-[0.625rem] text-ink-faint">Called</span>
                              {pred ? `${pred.winner === 'Draw' ? 'Draw' : teamShort(pred.winner ?? '')} ${scoreline(pred.score)}` : '—'}
                            </span>
                            <span className="font-mono text-xs font-semibold text-ink tnum">
                              {actualScore ?? <span className="text-ink-faint">—</span>}
                            </span>
                            <span>
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
                          </div>
                        </motion.div>
                      );
                    })}
                  </motion.div>
                </section>
                );
              })}
            </>
          )}
        </>
      )}
    </div>
  );
}
