import { useState } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'motion/react';
import TeamBadge from './TeamBadge';
import FeatureReveal from './FeatureReveal';
import { displayName, teamName, teamShort } from '../lib/teams';
import { percent, scoreline, printDate, kickoffDay, strongestCall } from '../lib/format';
import { ledgerVariants, stampVariants, getReducedMotionVariants } from '../lib/motion';
import type { Match, ResultEntry } from '../types';

interface FixtureCardProps {
  match: Match;
  verdict?: ResultEntry;
}

const OUTCOMES = ['H', 'D', 'A'] as const;

/** One fixture as a desk card: the call, the expected score, the split and the model's inputs. */
export default function FixtureCard({ match, verdict }: FixtureCardProps) {
  const [open, setOpen] = useState(false);
  const reduce = useReducedMotion();
  const variants = reduce ? getReducedMotionVariants(ledgerVariants) : ledgerVariants;
  const stampV = reduce ? getReducedMotionVariants(stampVariants) : stampVariants;

  const pred = match.prediction;
  const call = strongestCall(match);
  const home = match.home_team_info ?? match.home_team;
  const away = match.away_team_info ?? match.away_team;
  const homeName = teamName(match.home_team);
  const awayName = teamName(match.away_team);
  const homeLabel = displayName(match.home_team);
  const awayLabel = displayName(match.away_team);
  const winnerIsDraw = pred?.winner === 'Draw' || pred?.winner === 'draw';
  const callText = !pred?.winner
    ? null
    : winnerIsDraw
      ? 'Draw'
      : pred.winner === homeName
        ? homeLabel
        : awayLabel;

  const kickoff = match.time ? match.time.slice(0, 5) : null;
  const features = pred?.features;
  const homeElo = features?.home_elo ?? pred?.home_elo;
  const awayElo = features?.away_elo ?? pred?.away_elo;
  const probs = pred ? { H: pred.prob_home, D: pred.prob_draw, A: pred.prob_away } : null;
  const plateId = `plate-${match.id}`;
  // Calls rebuilt after kickoff from pre-match data (sync replaced a placeholder).
  const rebuilt = pred?.model_version?.endsWith('+rebuilt') ?? false;

  const actual = verdict?.actual?.score ?? (verdict?.actual ? `${verdict.actual.home_goals}-${verdict.actual.away_goals}` : null);

  return (
    <motion.article
      variants={variants}
      initial="hidden"
      animate="show"
      exit="exit"
      className={`fixture-card flex flex-col ${open ? 'sm:col-span-2' : ''}`}
      aria-label={`${homeName} versus ${awayName}`}
    >
      <div className="flex flex-col gap-3.5 px-4 pb-4 pt-4 sm:px-5">
        {/* Kickoff + the call */}
        <div className="flex items-center justify-between gap-3">
          <span className="shrink-0 whitespace-nowrap font-mono text-[0.6875rem] uppercase tracking-[0.1em] text-chalk-faint">
            {kickoffDay(match.date)}{kickoff ? ` · ${kickoff}` : ''}
          </span>
          {callText && (
            <motion.span variants={stampV} initial="hidden" animate="show" className="stamp min-w-0 truncate">
              Call · {callText}
            </motion.span>
          )}
        </div>

        {/* Teams + expected score */}
        <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-end gap-3">
          <span className="flex min-w-0 flex-col items-start gap-2">
            <TeamBadge team={match.home_team} info={match.home_team_info} size="md" />
            <span className="min-w-0 font-display text-[1.625rem] font-extrabold uppercase leading-[0.92] text-chalk [overflow-wrap:normal] sm:text-[1.75rem]">
              {homeLabel}
            </span>
          </span>
          <span className="bg-chalk px-3 py-1 font-mono text-xl font-semibold text-ground tnum">
            <span className="sr-only">Expected score: </span>
            {pred?.score ? scoreline(pred.score).replace(/\s/g, '') : '–'}
          </span>
          <span className="flex min-w-0 flex-col items-end gap-2 text-right">
            <TeamBadge team={match.away_team} info={match.away_team_info} size="md" />
            <span className="min-w-0 font-display text-[1.625rem] font-extrabold uppercase leading-[0.92] text-chalk [overflow-wrap:normal] sm:text-[1.75rem]">
              {awayLabel}
            </span>
          </span>
        </div>

        {probs ? (
          <>
            {/* Home · draw · away split */}
            <div className="split-bar" aria-hidden="true">
              <span className="split-home" style={{ flex: `${probs.H} 1 0` }} />
              <span className="split-draw" style={{ flex: `${probs.D} 1 0` }} />
              <span className="split-away" style={{ flex: `${probs.A} 1 0` }} />
            </div>
            <div className="flex justify-between font-mono text-[0.8125rem] tnum">
              {OUTCOMES.map((k) => (
                <span key={k} className={call?.key === k ? 'font-semibold text-amber' : 'text-chalk-soft'}>
                  {k} {percent(probs[k])}%
                </span>
              ))}
            </div>
          </>
        ) : (
          <p className="font-mono text-xs uppercase tracking-caps text-chalk-faint">No prediction recorded</p>
        )}

        {/* The model's inputs, home left · away right */}
        {(homeElo != null || features) && (
          <dl className="grid grid-cols-[4.5rem_minmax(0,1fr)_minmax(0,1fr)] items-center gap-y-1.5 border-t border-line pt-3 font-mono text-xs tnum">
            {homeElo != null && awayElo != null && (
              <>
                <dt className="text-[0.625rem] tracking-[0.1em] text-chalk-faint">ELO</dt>
                <dd>{Math.round(homeElo)}</dd>
                <dd className="text-right">{Math.round(awayElo)}</dd>
              </>
            )}
            {features && (
              <>
                <dt className="text-[0.625rem] tracking-[0.1em] text-chalk-faint">GOALS</dt>
                <dd>{features.home_rolling_goals.toFixed(2)}</dd>
                <dd className="text-right">{features.away_rolling_goals.toFixed(2)}</dd>
                <dt className="text-[0.625rem] tracking-[0.1em] text-chalk-faint">xG</dt>
                <dd>{features.home_rolling_xg.toFixed(2)}</dd>
                <dd className="text-right">{features.away_rolling_xg.toFixed(2)}</dd>
              </>
            )}
          </dl>
        )}

        {/* Verdict + fold-out toggle */}
        <div className="flex items-center justify-between gap-3 border-t border-line pt-3">
          <span className="flex items-center gap-2.5">
            {verdict?.status === 'CORRECT' && <span className="stamp-right">Right ✓</span>}
            {verdict?.status === 'INCORRECT' && <span className="stamp-wrong">Wrong</span>}
            {verdict?.status === 'PENDING' && <span className="chip">Pending</span>}
            {rebuilt && (
              <span className="chip" title="Rebuilt after the match from pre-match Elo and form; the original call was lost to a bug.">
                Rebuilt
              </span>
            )}
            {actual && (
              <span className="font-mono text-xs text-chalk-soft tnum">
                FT {scoreline(actual).replace(/\s/g, '')}
              </span>
            )}
          </span>
          {pred && (
            <button
              type="button"
              onClick={() => setOpen(!open)}
              aria-expanded={open}
              aria-controls={plateId}
              className="flex min-h-[44px] items-center gap-2 font-mono text-[0.6875rem] uppercase tracking-[0.1em] text-chalk-soft transition-colors hover:text-chalk"
            >
              {open ? 'Hide' : 'Why this call'}
              <span aria-hidden="true" className={`transition-transform duration-300 ${open ? 'rotate-90' : ''}`}>▸</span>
            </button>
          )}
        </div>
      </div>

      <AnimatePresence initial={false}>
        {open && pred && (
          <motion.div
            id={plateId}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.34, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
            aria-live="polite"
          >
            <div className="border-t border-line bg-ground/40 px-4 pb-5 pt-4 sm:px-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-faint">
                  Matchweek {match.gameweek} · {printDate(match.date)}
                  {kickoff ? ` · ${kickoff}` : ''}
                </span>
              </div>

              <div className="grid gap-5 pt-4 sm:grid-cols-2">
                <div>
                  <h4 className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-faint">Goal expectation</h4>
                  <p className="mt-1 flex items-baseline gap-3 font-mono text-3xl font-semibold text-chalk tnum">
                    <span>{pred.home_goals?.toFixed(1) ?? '—'}</span>
                    <span className="text-base text-chalk-faint">—</span>
                    <span>{pred.away_goals?.toFixed(1) ?? '—'}</span>
                  </p>
                  <p className="mt-1 text-xs italic text-chalk-faint">expected goals, model output</p>
                </div>

                <div>
                  <h4 className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-faint">Outcome odds</h4>
                  <div className="mt-3 space-y-2">
                    {[
                      { key: 'H', label: `Home — ${teamShort(home)}`, v: pred.prob_home },
                      { key: 'D', label: 'Draw', v: pred.prob_draw },
                      { key: 'A', label: `Away — ${teamShort(away)}`, v: pred.prob_away },
                    ].map((row) => (
                      <div key={row.key} className="flex items-center gap-2">
                        <span className="w-32 shrink-0 truncate font-mono text-[0.625rem] uppercase tracking-widest text-chalk-soft">
                          {row.label}
                        </span>
                        <span className="h-2 flex-1 overflow-hidden bg-raised">
                          <span
                            className={`block h-full ${row.key === call?.key ? 'bg-amber' : 'bg-chalk-faint'}`}
                            style={{ width: `${Math.min(100, Math.max(0, row.v * 100))}%` }}
                            aria-hidden="true"
                          />
                        </span>
                        <span className="w-9 text-right font-mono text-sm text-chalk tnum">{percent(row.v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <FeatureReveal match={match} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.article>
  );
}
