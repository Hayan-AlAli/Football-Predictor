import { useEffect, useMemo, useState } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import Press from '../components/Press';
import OfflineSlate from '../components/OfflineSlate';
import EmptyState from '../components/EmptyState';
import TeamBadge from '../components/TeamBadge';
import { MeterBar } from '../lib/charts';
import { getForecast } from '../api/matches';
import { percent } from '../lib/format';
import { getReducedMotionVariants, headVariants, ledgerVariants, staggerContainer } from '../lib/motion';
import type { ForecastData } from '../types';

type LoadState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; data: ForecastData };

export default function ForecastPage() {
  const [state, setState] = useState<LoadState>({ status: 'loading' });
  const [reloadKey, setReloadKey] = useState(0);
  const reduce = useReducedMotion();
  const headV = reduce ? getReducedMotionVariants(headVariants) : headVariants;
  const staggerV = reduce ? getReducedMotionVariants(staggerContainer) : staggerContainer;
  const rowV = reduce ? getReducedMotionVariants(ledgerVariants) : ledgerVariants;

  useEffect(() => {
    let cancelled = false;
    getForecast()
      .then((data) => { if (!cancelled) setState({ status: 'ready', data }); })
      .catch(() => { if (!cancelled) setState({ status: 'error' }); });
    return () => { cancelled = true; };
  }, [reloadKey]);

  const standingsByTeam = useMemo(() => {
    if (state.status !== 'ready') return new Map<string, ForecastData['standings'][number]>();
    return new Map(state.data.standings.map((s) => [s.team, s]));
  }, [state]);

  if (state.status === 'loading') return <div className="mx-auto max-w-5xl px-4 pb-4"><Press /></div>;
  if (state.status === 'error') {
    return (
      <div className="mx-auto max-w-5xl px-4 pb-4">
        <OfflineSlate
          message="The forecast could not be computed. Check that the press (FastAPI) is running."
          onRetry={() => {
            setState({ status: 'loading' });
            setReloadKey((k) => k + 1);
          }}
        />
      </div>
    );
  }

  const { data } = state;
  const rows = data.projected;

  return (
    <div className="mx-auto max-w-5xl px-4 pb-4">
      <motion.div variants={headV} initial="hidden" animate="show" className="pt-8">
        <h1 className="font-sans text-2xl sm:text-3xl font-extrabold uppercase tracking-caps text-ink">
          The Season Forecast
        </h1>
        <p className="mt-1.5 font-serif text-sm italic text-ink-soft sm:text-base">
          The model plays every remaining fixture ten thousand times, and prints the distribution.
        </p>
        {data.stale && (
          <p className="mt-1 font-mono text-[0.6875rem] uppercase tracking-wider-caps text-rubric">
            served from the forecast of {data.stale}
          </p>
        )}
      </motion.div>

      {data.season_complete && rows.length === 0 ? (
        <>
          <h2 className="rule-double mt-8 pt-3 font-mono text-xl font-semibold text-rubric">
            The season is complete
          </h2>
          <p className="mt-2 font-serif text-sm italic text-ink-soft">
            No fixtures remain — here is the final league table as the model saw it.
          </p>
          <div className="mt-6">
              {data.standings.map((s, i) => (
                <div key={s.team} className="grid grid-cols-[2rem_1fr_4rem] items-center gap-x-3 border-t border-paper-line py-3">
                  <span className="font-mono text-sm text-ink-faint tnum">{i + 1}</span>
                  <span className="flex min-w-0 items-center gap-2.5 truncate font-sans text-sm font-bold uppercase tracking-caps text-ink" title={s.team}>
                    <TeamBadge team={s.team} info={s.team_info} size="md" /> {s.team}
                  </span>
                  <span className="text-right font-mono text-sm text-ink tnum">{s.points}</span>
                </div>
              ))}
          </div>
        </>
      ) : rows.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            title="The forecast has not been printed"
            note="Once the press runs against a new season's fixtures, the season forecast appears here."
          />
        </div>
      ) : (
        <>
          <div className="rule-draw mt-6 flex flex-wrap items-center justify-between gap-2 py-3">
            <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
              Projected final table · {data.n_sims.toLocaleString()} runs
            </span>
            <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
              generated {data.generated}
            </span>
          </div>

          <div className="hidden sm:grid grid-cols-[2.5rem_1fr_10rem_4.5rem_12rem] gap-x-3 px-2 pb-1 pt-3">
            <span className="font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">#</span>
            <span className="font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">Club</span>
            <span className="text-center font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">Points P10–P90</span>
            <span className="text-center font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">Median pos</span>
            <span className="text-right font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">Title · Top-4 · Relegation</span>
          </div>

          <motion.div variants={staggerV} initial="hidden" animate="show" className="pb-8">
            {rows.map((r, i) => {
              const current = standingsByTeam.get(r.team);
              return (
                <motion.div
                  key={r.team}
                  variants={rowV}
                  initial="hidden"
                  animate="show"
                  className="grid grid-cols-[2rem_1fr_auto] items-center gap-x-3 border-t border-paper-line py-3.5 sm:grid-cols-[2.5rem_1fr_10rem_4.5rem_12rem] sm:px-2"
                >
                  <span className="font-mono text-sm text-ink-faint tnum">{i + 1}</span>
                  <span className="flex min-w-0 items-center gap-2.5">
                    <TeamBadge team={r.team} info={r.team_info} size="lg" />
                    <span className="truncate font-sans text-sm font-bold uppercase tracking-caps text-ink" title={r.team}>{r.team}</span>
                    {current && (
                      <span className="hidden sm:inline font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">
                        {current.points} pts · {current.played} played
                      </span>
                    )}
                  </span>
                  <span className="flex w-24 items-center gap-1.5 sm:w-auto sm:flex-1" aria-label={`Points range ${r.points_p10} to ${r.points_p90}`}>
                    <span className="font-mono text-[0.625rem] text-ink-faint tnum">{Math.round(r.points_p10)}</span>
                    <span className="relative h-2 flex-1 bg-paper-white border border-paper-line overflow-hidden">
                      <span className="absolute inset-y-0 left-0 bg-ink/25" style={{ width: `${(r.points_p50 / 90) * 100}%` }} aria-hidden="true" />
                      <span className="absolute top-1/2 h-full w-0.5 -translate-y-1/2 bg-rubric" style={{ left: `${(r.points_p50 / 90) * 100}%` }} aria-hidden="true" />
                    </span>
                    <span className="font-mono text-[0.625rem] text-ink-faint tnum">{Math.round(r.points_p90)}</span>
                  </span>
                  <span className="text-center font-mono text-sm text-ink tnum">{r.median_position}</span>
                  <span className="hidden sm:block">
                    <span className="flex items-center gap-1.5">
                      <span className="w-16 truncate font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">title</span>
                      <MeterBar value={r.title_odds} tone={r.title_odds > 0.2 ? 'rubric' : 'ink'} />
                      <span className="w-9 text-right font-mono text-[0.625rem] text-ink tnum">{percent(r.title_odds)}</span>
                    </span>
                    <span className="mt-1 flex items-center gap-1.5">
                      <span className="w-16 truncate font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">top-4</span>
                      <MeterBar value={r.top4_odds} />
                      <span className="w-9 text-right font-mono text-[0.625rem] text-ink tnum">{percent(r.top4_odds)}</span>
                    </span>
                    <span className="mt-1 flex items-center gap-1.5">
                      <span className="w-16 truncate font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">releg.</span>
                      <MeterBar value={r.relegation_odds} tone={r.relegation_odds > 0.2 ? 'rubric' : 'ink'} />
                      <span className="w-9 text-right font-mono text-[0.625rem] text-ink tnum">{percent(r.relegation_odds)}</span>
                    </span>
                  </span>
                </motion.div>
              );
            })}
          </motion.div>

          <p className="rule-double pt-3 pb-8 font-serif text-xs italic text-ink-faint">
            Odds are the model's own probabilities, not betting advice. The simulation samples scorelines from
            each fixture's expected goals and assumes independence between matches.
          </p>
        </>
      )}
    </div>
  );
}