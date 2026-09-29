import { useCallback, useEffect, useMemo, useState, type ChangeEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import Press from '../components/Press';
import OfflineSlate from '../components/OfflineSlate';
import EmptyState from '../components/EmptyState';
import TeamBadge from '../components/TeamBadge';
import FeatureReveal from '../components/FeatureReveal';
import { SvgLineChart } from '../lib/charts';
import { getHeadToHead, getTeamProfile } from '../api/matches';
import { useData } from '../lib/data-context';
import { teamShort } from '../lib/teams';
import { percent, printDate } from '../lib/format';
import { getReducedMotionVariants, headVariants } from '../lib/motion';
import type { Match, TeamProfileData } from '../types';
import type { H2HData } from '../types';

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

  const { teams } = useData();
  const profileTeam = state.status === 'ready' ? state.data.team : null;
  // Opponents by slug; the club itself is excluded once its profile names it.
  const vsList = useMemo(
    () => teams
      .filter((t) => t.name !== profileTeam && t.slug !== teamName && t.name !== teamName)
      .map((t) => ({ value: t.slug || t.name, label: t.name }))
      .sort((a, b) => a.label.localeCompare(b.label)),
    [teams, profileTeam, teamName],
  );
  const [picked, setPicked] = useState<string>('');
  const vs = picked || vsList[0]?.value || '';
  const h2hKey = vs ? `${teamName}|${vs}` : '';
  const [h2hState, setH2hState] = useState<{ key: string; data: H2HData | null; error: boolean }>(
    { key: '', data: null, error: false },
  );

  useEffect(() => {
    if (!h2hKey) return;
    let cancelled = false;
    getHeadToHead(teamName, vs)
      .then((data) => { if (!cancelled) setH2hState({ key: h2hKey, data, error: false }); })
      .catch(() => { if (!cancelled) setH2hState({ key: h2hKey, data: null, error: true }); });
    return () => { cancelled = true; };
  }, [teamName, vs, h2hKey]);

  const h2hLoading = !!h2hKey && h2hState.key !== h2hKey;
  const h2hError = !h2hLoading && h2hState.error;
  const h2h = h2hState.key === h2hKey ? h2hState.data : null;

  const onVsChange = useCallback((e: ChangeEvent<HTMLSelectElement>) => {
    setPicked(e.target.value);
  }, []);

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
        <Link to="/teams" className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-faint no-underline hover:text-chalk">
          ← The Teams Index
        </Link>
        <div className="mt-3 flex items-center gap-3">
          <TeamBadge team={data.team} info={data.team_info} size="lg" />
          <div className="min-w-0">
            <h1 className="truncate font-display text-[2.75rem] sm:text-[3.5rem] font-black uppercase leading-[0.9] text-chalk">
              {data.team}
            </h1>
            {latest && (
              <p className="mt-1 font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-faint">
                season {latest.season_year} · {latest.played} played · {latest.wins} W · {latest.draws} D · {latest.losses} L · {latest.points} pts
              </p>
            )}
          </div>
        </div>
      </motion.div>

      {seasons.length > 0 && (
        <section className="rule-double mt-8 pt-3">
          <h2 className="font-display text-[1.75rem] font-extrabold uppercase leading-none text-chalk">The ledger of the club</h2>
          <div className="mt-3">
            <div className="hidden sm:grid grid-cols-[5rem_1fr_1fr_1fr_1fr_1fr_1fr_3rem] gap-x-2 px-2 pb-1 font-mono text-[0.625rem] uppercase tracking-widest text-chalk-faint">
              <span>Season</span><span className="text-right">P</span><span className="text-right">W</span>
              <span className="text-right">D</span><span className="text-right">L</span>
              <span className="text-right">GF</span><span className="text-right">GA</span><span className="text-right">Pts</span>
            </div>
            {seasons.map((s) => (
              <div key={s.season_year} className="grid grid-cols-4 items-center gap-x-2 border-t border-line py-2.5 sm:grid-cols-[5rem_1fr_1fr_1fr_1fr_1fr_1fr_3rem] sm:px-2">
                <span className="font-mono text-sm text-chalk">{s.season_year}-{String(s.season_year + 1).slice(2)}</span>
                <span className="text-right font-mono text-sm text-chalk-soft tnum">{s.played}</span>
                <span className="text-right font-mono text-sm text-chalk-soft tnum">{s.wins}</span>
                <span className="text-right font-mono text-sm text-chalk-soft tnum">{s.draws}</span>
                <span className="text-right font-mono text-sm text-chalk-soft tnum">{s.losses}</span>
                <span className="text-right font-mono text-sm text-chalk-soft tnum">{s.gf}</span>
                <span className="text-right font-mono text-sm text-chalk-soft tnum">{s.ga}</span>
                <span className="text-right font-mono text-sm font-semibold text-chalk tnum">{s.points}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {form.length > 0 && (
        <section className="rule-double mt-10 pt-3">
          <h2 className="font-display text-[1.75rem] font-extrabold uppercase leading-none text-chalk">Form — last {form.length}</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {form.map((f, i) => (
              <span key={f.date + i} className={`flex h-9 w-9 items-center justify-center border font-mono text-sm font-semibold ${
                f.result === 'W' ? 'border-chalk bg-chalk text-ground' : f.result === 'L' ? 'border-line-strong text-chalk-faint' : 'border-draw bg-draw text-chalk'
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
            <h2 className="font-display text-[1.75rem] font-extrabold uppercase leading-none text-chalk">Club rating</h2>
            <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-faint">
              latest {elo[elo.length - 1].elo}
            </span>
          </div>
          <div className="mt-4">
            <SvgLineChart points={elo.map((e) => ({ x: e.date, y: e.elo }))} />
          </div>
          <p className="mt-2 font-sans text-xs italic text-chalk-faint">
            The club's Elo rating before each of its matches, five seasons back.
          </p>
        </section>
      )}

      {upcoming.length > 0 && (
        <section className="rule-double mt-10 pt-3">
          <h2 className="font-display text-[1.75rem] font-extrabold uppercase leading-none text-chalk">Fixtures to come</h2>
          <div className="mt-3">
            {upcoming.map((m: Match) => {
              const pred = m.prediction;
              const home = typeof m.home_team === 'string' ? m.home_team : m.home_team?.name ?? '';
              const away = typeof m.away_team === 'string' ? m.away_team : m.away_team?.name ?? '';
              return (
                <article key={m.id} className="border-t border-line py-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-sans text-xs italic text-chalk-faint">{printDate(m.date)}</span>
                    <span className="min-w-0 truncate font-sans text-sm font-bold uppercase tracking-caps text-chalk">
                      {teamShort(home)} <span className="font-mono font-normal text-chalk-faint">vs</span> {teamShort(away)}
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

      <section className="rule-double mt-10 pt-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="font-display text-[1.75rem] font-extrabold uppercase leading-none text-chalk">Head to head</h2>
          <label className="flex items-center gap-2">
            <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-faint">opponent</span>
            <select
              value={vs}
              onChange={onVsChange}
              className="border border-line bg-raised px-2 py-1 font-mono text-xs uppercase tracking-wider-caps text-chalk"
            >
              {vsList.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
        </div>

        {h2hLoading && <p className="mt-3 font-sans text-xs italic text-chalk-faint" role="status">Setting the fixture…</p>}
        {h2hError && !h2hLoading && (
          <p className="mt-3 font-sans text-xs italic text-chalk-faint">This fixture could not be set — try another opponent.</p>
        )}
        {h2h && !h2hLoading && !h2hError && (
          <>
            <p className="mt-3 font-sans text-sm italic text-chalk-soft">
              {h2h.summary.meetings} meetings · {teamShort(h2h.team_a)} {h2h.summary.team_a_wins}–{h2h.summary.draws}–{h2h.summary.team_b_wins} {teamShort(h2h.team_b)}
              · {teamShort(h2h.team_a)} scored {h2h.summary.team_a_for}, conceded {h2h.summary.team_a_against}
            </p>
            <div className="mt-3">
              {h2h.meetings.length === 0 ? (
                <p className="font-sans text-xs italic text-chalk-faint">No recorded meetings in the training ledger.</p>
              ) : (
                h2h.meetings.map((m) => (
                  <div key={m.date + m.home_team + m.away_team} className="flex flex-wrap items-center justify-between gap-x-3 border-t border-line py-2.5">
                    <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-faint">{m.date}</span>
                    <span className="min-w-0 truncate font-sans text-sm font-bold uppercase tracking-caps text-chalk">
                      {teamShort(m.home_team)} <span className="font-mono font-normal text-chalk-faint">{m.home_goals}–{m.away_goals}</span> {teamShort(m.away_team)}
                    </span>
                    <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-soft">
                      {m.winner === 'Draw' ? 'draw' : `${teamShort(m.winner)} win`}
                    </span>
                  </div>
                ))
              )}
            </div>
          </>
        )}
      </section>
    </div>
  );
}