import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import Press from '../components/Press';
import OfflineSlate from '../components/OfflineSlate';
import EmptyState from '../components/EmptyState';
import TeamBadge from '../components/TeamBadge';
import FeatureReveal from '../components/FeatureReveal';
import { SvgLineChart } from '../lib/charts';
import { getTeamProfile } from '../api/matches';
import { teamShort } from '../lib/teams';
import { percent, printDate } from '../lib/format';
import { getReducedMotionVariants, headVariants } from '../lib/motion';
import type { Match, TeamProfileData } from '../types';

type LoadState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; data: TeamProfileData };

export default function TeamDetailPage() {
  const { teamName = '' } = useParams();
  const [state, setState] = useState<LoadState>({ status: 'loading' });
  const [reloadKey, setReloadKey] = useState(0);
  const reduce = useReducedMotion();
  const headV = reduce ? getReducedMotionVariants(headVariants) : headVariants;

  useEffect(() => {
    let cancelled = false;
    getTeamProfile(teamName)
      .then((data) => { if (!cancelled) setState({ status: 'ready', data }); })
      .catch(() => { if (!cancelled) setState({ status: 'error' }); });
    return () => { cancelled = true; };
  }, [teamName, reloadKey]);

  if (state.status === 'loading') return <div className="mx-auto max-w-3xl px-4 pb-4"><Press /></div>;
  if (state.status === 'error') {
    return (
      <div className="mx-auto max-w-3xl px-4 pb-4">
        <OfflineSlate
          message="This club's page could not be set. Check that the press (FastAPI) is running."
          onRetry={() => {
            setState({ status: 'loading' });
            setReloadKey((k) => k + 1);
          }}
        />
      </div>
    );
  }

  const { data } = state;
  const seasons = data.seasons ?? [];
  const form = data.form ?? [];
  const elo = data.elo_history ?? [];
  const upcoming = data.upcoming ?? [];
  const latest = seasons[0];

  return (
    <div className="mx-auto max-w-3xl px-4 pb-4">
      <motion.div variants={headV} initial="hidden" animate="show" className="pt-8">
        <Link to="/teams" className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-rubric no-underline hover:text-ink">
          ← The Teams Index
        </Link>
        <div className="mt-3 flex items-center gap-3">
          <TeamBadge team={data.team} info={data.team_info} size="lg" />
          <div className="min-w-0">
            <h1 className="truncate font-sans text-2xl sm:text-3xl font-extrabold uppercase tracking-caps text-ink">
              {data.team}
            </h1>
            {latest && (
              <p className="mt-1 font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
                season {latest.season_year} · {latest.played} played · {latest.wins} W · {latest.draws} D · {latest.losses} L · {latest.points} pts
              </p>
            )}
          </div>
        </div>
      </motion.div>

      {seasons.length > 0 && (
        <section className="rule-double mt-8 pt-3">
          <h2 className="font-mono text-xl font-semibold text-rubric">The ledger of the club</h2>
          <div className="mt-3">
            <div className="hidden sm:grid grid-cols-[5rem_1fr_1fr_1fr_1fr_1fr_1fr_3rem] gap-x-2 px-2 pb-1 font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">
              <span>Season</span><span className="text-right">P</span><span className="text-right">W</span>
              <span className="text-right">D</span><span className="text-right">L</span>
              <span className="text-right">GF</span><span className="text-right">GA</span><span className="text-right">Pts</span>
            </div>
            {seasons.map((s) => (
              <div key={s.season_year} className="grid grid-cols-4 items-center gap-x-2 border-t border-paper-line py-2.5 sm:grid-cols-[5rem_1fr_1fr_1fr_1fr_1fr_1fr_3rem] sm:px-2">
                <span className="font-mono text-sm text-ink">{s.season_year}-{String(s.season_year + 1).slice(2)}</span>
                <span className="text-right font-mono text-sm text-ink-soft tnum">{s.played}</span>
                <span className="text-right font-mono text-sm text-ink-soft tnum">{s.wins}</span>
                <span className="text-right font-mono text-sm text-ink-soft tnum">{s.draws}</span>
                <span className="text-right font-mono text-sm text-ink-soft tnum">{s.losses}</span>
                <span className="text-right font-mono text-sm text-ink-soft tnum">{s.gf}</span>
                <span className="text-right font-mono text-sm text-ink-soft tnum">{s.ga}</span>
                <span className="text-right font-mono text-sm font-semibold text-ink tnum">{s.points}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {form.length > 0 && (
        <section className="rule-double mt-10 pt-3">
          <h2 className="font-mono text-xl font-semibold text-rubric">Form — last {form.length}</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {form.map((f, i) => (
              <span key={f.date + i} className={`flex h-9 w-9 items-center justify-center border font-mono text-sm font-semibold ${
                f.result === 'W' ? 'border-ledger text-ledger' : f.result === 'L' ? 'border-rubric text-rubric' : 'border-ink text-ink'
              }`} title={`${f.date} · ${teamShort(f.home_team)} ${f.home_goals}-${f.away_goals} ${teamShort(f.away_team)}`}>
                {f.result}
              </span>
            ))}
          </div>
        </section>
      )}

      {elo.length > 0 && (
        <section className="rule-double mt-10 pt-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="font-mono text-xl font-semibold text-rubric">Club rating</h2>
            <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
              latest {elo[elo.length - 1].elo}
            </span>
          </div>
          <div className="mt-4">
            <SvgLineChart points={elo.map((e) => ({ x: e.date, y: e.elo }))} />
          </div>
          <p className="mt-2 font-serif text-xs italic text-ink-faint">
            The club's Elo rating before each of its matches, five seasons back.
          </p>
        </section>
      )}

      {upcoming.length > 0 && (
        <section className="rule-double mt-10 pt-3">
          <h2 className="font-mono text-xl font-semibold text-rubric">Fixtures to come</h2>
          <div className="mt-3">
            {upcoming.map((m: Match) => {
              const pred = m.prediction;
              const home = typeof m.home_team === 'string' ? m.home_team : m.home_team?.name ?? '';
              const away = typeof m.away_team === 'string' ? m.away_team : m.away_team?.name ?? '';
              return (
                <article key={m.id} className="border-t border-paper-line py-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-serif text-xs italic text-ink-faint">{printDate(m.date)}</span>
                    <span className="min-w-0 truncate font-sans text-sm font-bold uppercase tracking-caps text-ink">
                      {teamShort(home)} <span className="font-mono font-normal text-ink-faint">vs</span> {teamShort(away)}
                    </span>
                    {pred && (
                      <span className="stamp text-xs">{pred.winner ?? '—'} · {percent(pred.prob_home)}/{percent(pred.prob_draw)}/{percent(pred.prob_away)}</span>
                    )}
                  </div>
                  <FeatureReveal match={m} />
                </article>
              );
            })}
          </div>
        </section>
      )}

      {seasons.length === 0 && form.length === 0 && elo.length === 0 && (
        <div className="mt-8">
          <EmptyState
            title="This page is blank"
            note="No records for this club in the training ledger. It may be a newly promoted side."
          />
        </div>
      )}
    </div>
  );
}