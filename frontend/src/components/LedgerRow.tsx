import { useState } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'motion/react';
import TeamBadge from './TeamBadge';
import FeatureReveal from './FeatureReveal';
import { teamShort } from '../lib/teams';
import { percent, scoreline, printDate, strongestCall } from '../lib/format';
import { ledgerVariants, stampVariants, getReducedMotionVariants } from '../lib/motion';
import type { Match } from '../types';

interface LedgerRowProps {
  match: Match;
  index: number;
}

/** One fixture as a ruled ledger entry; clicking unfolds the fold-out plate. */
export default function LedgerRow({ match, index }: LedgerRowProps) {
  const [open, setOpen] = useState(false);
  const reduce = useReducedMotion();
  const variants = reduce ? getReducedMotionVariants(ledgerVariants) : ledgerVariants;
  const stampV = reduce ? getReducedMotionVariants(stampVariants) : stampVariants;

  const pred = match.prediction;
  const call = strongestCall(match);
  const home = match.home_team_info ?? match.home_team;
  const away = match.away_team_info ?? match.away_team;
  const homeName = typeof home === 'string' ? home : home.name;
  const awayName = typeof away === 'string' ? away : away.name;
  const winnerIsDraw = pred?.winner && (pred.winner === 'Draw' || pred.winner === 'draw');
  const winnerTeam = winnerIsDraw ? null : teamShort(winnerTeamOf(match));

  const kickoff = match.time ? match.time.slice(0, 5) : null;
  const elo = pred?.home_elo && pred?.away_elo
    ? { home: pred.home_elo, away: pred.away_elo, max: Math.max(pred.home_elo, pred.away_elo), min: Math.min(pred.home_elo, pred.away_elo) }
    : null;

  return (
    <motion.article
      variants={variants}
      initial="hidden"
      animate="show"
      exit="exit"
      className="border-t border-paper-line"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-controls={`plate-${match.id}`}
        className="ledger-row group grid w-full cursor-pointer grid-cols-[2.75rem_1fr_auto_1fr] items-center gap-x-2 px-1 py-4 text-left sm:grid-cols-[2.75rem_1fr_10rem_1fr_auto] sm:gap-x-3 sm:px-2"
      >
        {/* Kickoff */}
        <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
          {kickoff ?? '—'}
        </span>

        {/* Home — right aligned */}
        <span className="flex min-w-0 items-center justify-end gap-2">
          <span className="truncate font-sans text-sm sm:text-base font-bold uppercase tracking-caps text-ink">
            {teamShort(home)}
          </span>
          <TeamBadge team={match.home_team} info={match.home_team_info} size="md" />
        </span>

        {/* Readout + expected score */}
        <span className="flex flex-col items-center gap-1 px-1">
          {pred ? (
            <span className="font-mono text-[0.6875rem] sm:text-xs whitespace-nowrap text-ink-soft tnum">
              <span className={call?.key === 'H' ? 'font-semibold text-rubric' : ''}>H {percent(pred.prob_home)}</span>
              <span aria-hidden="true" className="text-ink-faint"> · </span>
              <span className={call?.key === 'D' ? 'font-semibold text-rubric' : ''}>D {percent(pred.prob_draw)}</span>
              <span aria-hidden="true" className="text-ink-faint"> · </span>
              <span className={call?.key === 'A' ? 'font-semibold text-rubric' : ''}>A {percent(pred.prob_away)}</span>
            </span>
          ) : (
            <span className="font-mono text-xs text-ink-faint">NO PREDICTION</span>
          )}
          <span className="font-mono text-xl sm:text-2xl font-semibold text-ink leading-none tnum">
            <span className="sr-only">Expected score: </span>
            {pred?.score ? scoreline(pred.score) : '–'}
          </span>
        </span>

        {/* Away — left aligned */}
        <span className="flex min-w-0 items-center justify-start gap-2">
          <TeamBadge team={match.away_team} info={match.away_team_info} size="md" />
          <span className="truncate font-sans text-sm sm:text-base font-bold uppercase tracking-caps text-ink">
            {teamShort(away)}
          </span>
        </span>

        {/* Call + chevron */}
        <span className="col-span-2 mt-3 flex items-center justify-center gap-3 sm:col-span-1 sm:mt-0 sm:justify-end">
          {winnerTeam && (
            <motion.span variants={stampV} initial="hidden" animate="show" className="stamp">
              {winnerTeam}
            </motion.span>
          )}
          <span
            aria-hidden="true"
            className={`font-mono text-sm text-ink-faint transition-transform duration-300 ${open ? 'rotate-90' : ''}`}
          >
            ▸
          </span>
        </span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            id={`plate-${match.id}`}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.34, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
            aria-live="polite"
          >
            <div className="plate mb-5 p-4 sm:p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-paper-line pb-3">
                <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
                  Fold-out plate · Matchweek {match.gameweek}
                </span>
                <span className="min-w-0 truncate font-sans text-sm font-semibold uppercase tracking-caps text-ink">
                  {homeName} <span className="font-mono font-normal text-ink-faint">vs</span> {awayName}
                </span>
                <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-soft">
                  {printDate(match.date)}
                  {kickoff ? ` · ${kickoff}` : ''}
                </span>
              </div>

              {!pred ? (
                <p className="mt-4 font-serif italic text-ink-soft">
                  No prediction has been recorded for this fixture. The press only prints what it has set.
                </p>
              ) : (
                <>
                <div className="grid gap-5 pt-4 sm:grid-cols-3">
                  {/* Goal expectation */}
                  <div>
                    <h4 className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">Goal expectation</h4>
                    <p className="mt-1 flex items-baseline gap-3 font-mono text-3xl font-semibold text-ink tnum">
                      <span>{pred.home_goals?.toFixed(1) ?? '—'}</span>
                      <span className="text-base text-ink-faint">—</span>
                      <span>{pred.away_goals?.toFixed(1) ?? '—'}</span>
                    </p>
                    <p className="mt-1 font-serif text-xs italic text-ink-faint">expected goals, model output</p>
                  </div>

                  {/* Club rating */}
                  <div>
                    <h4 className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">Club rating</h4>
                    {elo ? (
                      <>
                        <div className="mt-3 h-1.5 bg-paper-white border border-paper-line relative">
                          <span
                            className="absolute top-0 h-full bg-ink transition-all duration-700"
                            style={{ left: `${((elo.home - elo.min) / Math.max(elo.max - elo.min, 1)) * 100}%`, width: 3 }}
                            aria-hidden="true"
                          />
                          <span
                            className="absolute top-0 h-full bg-rubric transition-all duration-700"
                            style={{ left: `${((elo.away - elo.min) / Math.max(elo.max - elo.min, 1)) * 100}%`, width: 3 }}
                            aria-hidden="true"
                          />
                        </div>
                        <div className="mt-2 flex justify-between font-mono text-sm text-ink tnum">
                          <span className="flex items-center gap-1.5">
                            <span className="inline-block h-2 w-2 bg-ink" aria-hidden="true" />
                            {teamShort(home)} {elo.home}
                          </span>
                          <span className="flex items-center gap-1.5">
                            {teamShort(away)} {elo.away}
                            <span className="inline-block h-2 w-2 bg-rubric" aria-hidden="true" />
                          </span>
                        </div>
                      </>
                    ) : (
                      <p className="mt-1 font-serif text-xs italic text-ink-faint">no rating recorded</p>
                    )}
                    <p className="mt-1 font-serif text-xs italic text-ink-faint">live club Elo, model input</p>
                  </div>

                  {/* Outcome odds */}
                  <div>
                    <h4 className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">Outcome odds</h4>
                    <div className="mt-3 space-y-2">
                      {[
                        { key: 'H', label: `HOME — ${teamShort(home)}`, v: pred.prob_home },
                        { key: 'D', label: 'DRAW', v: pred.prob_draw },
                        { key: 'A', label: `AWAY — ${teamShort(away)}`, v: pred.prob_away },
                      ].map((row) => (
                        <div key={row.key} className="flex items-center gap-2">
                          <span className="w-40 shrink-0 truncate font-mono text-[0.625rem] uppercase tracking-widest text-ink-soft">
                            {row.label}
                          </span>
                          <span className="h-2 flex-1 bg-paper-white border border-paper-line overflow-hidden">
                            <motion.span
                              className={`block h-full ${row.key === call?.key ? 'bg-rubric' : 'bg-ink'}`}
                              initial={{ scaleX: 0 }}
                              animate={{ scaleX: 1 }}
                              transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                              style={{ width: `${Math.min(100, Math.max(0, row.v * 100))}%`, transformOrigin: 'left' }}
                              aria-hidden="true"
                            />
                          </span>
                          <span className="w-9 text-right font-mono text-sm text-ink tnum">{percent(row.v)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                <FeatureReveal match={match} />
                </>
              )}

              {pred && (
                <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-paper-line pt-4">
                  <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
                    The model calls
                  </span>
                  <motion.span variants={stampV} initial="hidden" animate="show" className="stamp text-sm">
                    {pred.winner ?? '—'} · {scoreline(pred.score)}
                  </motion.span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.article>
  );
}

function winnerTeamOf(match: Match): string | Match['home_team'] {
  const pred = match.prediction;
  if (!pred?.winner || pred.winner === 'Draw' || pred.winner === 'draw') return '';
  const homeName = typeof match.home_team === 'string' ? match.home_team : match.home_team.name;
  if (pred.winner === homeName) return match.home_team;
  return match.away_team;
}
