import { useCallback, useEffect, useState, type ChangeEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import Press from '../components/Press';
import OfflineSlate from '../components/OfflineSlate';
import EmptyState from '../components/EmptyState';
import TeamBadge from '../components/TeamBadge';
import FeatureReveal from '../components/FeatureReveal';
import { SvgLineChart } from '../lib/charts';
import { getHeadToHead, getTeamProfile, getTeams } from '../api/matches';
import { teamShort } from '../lib/teams';
import { percent, printDate } from '../lib/format';
import { getReducedMotionVariants, headVariants } from '../lib/motion';
import type { Match, TeamProfileData } from '../types';
import type { H2HData } from '../types';

type LoadState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; data: TeamProfileData };

/** Bridges /api/teams display names ("Arsenal F.C.") to match-derived slugs
 *  ("Arsenal") the same way backend.utils.normalize_team_name does. */
function canonicalClubName(name: string): string {
  return name
    .replace(/\s*[AF]\.?C\.?$/i, '')
    .replace(/^AFC\s+/i, '')
    .replace(/^Brighton (&|and) Hove Albion$/i, 'Brighton')
    .replace(/^Tottenham Hotspur$/i, 'Tottenham')
    .replace(/^Newcastle United$/i, 'Newcastle')
    .replace(/^Wolverhampton Wanderers$/i, 'Wolverhampton')
    .replace(/^West Ham United$/i, 'West Ham')
    .replace(/^Leeds United$/i, 'Leeds')
    .replace(/^Hull City$/i, 'Hull');
}

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

  const [vsList, setVsList] = useState<string[]>([]);
  const [vs, setVs] = useState<string>('');
  const [h2h, setH2h] = useState<H2HData | null>(null);
  const [h2hLoading, setH2hLoading] = useState(false);
  const [h2hError, setH2hError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getTeams()
      .then((teams) => {
        if (cancelled) return;
        const others = teams
          .map((t) => t.name)
          .filter((n) => canonicalClubName(n) !== canonicalClubName(teamName))
          .sort();
        setVsList(others);
        if (others.length > 0) {
          setVs(others[0]);
          setH2hLoading(true);
          setH2hError(false);
        }
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [teamName]);

  useEffect(() => {
    if (!vs) return;
    let cancelled = false;
    getHeadToHead(teamName, vs)
      .then((res) => { if (!cancelled) setH2h(res); })
      .catch(() => { if (!cancelled) setH2hError(true); })
      .finally(() => { if (!cancelled) setH2hLoading(false); });
    return () => { cancelled = true; };
  }, [teamName, vs]);

  const onVsChange = useCallback((e: ChangeEvent<HTMLSelectElement>) => {
    setH2hLoading(true);
    setH2hError(false);
    setVs(e.target.value);
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

      <section className="rule-double mt-10 pt-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="font-mono text-xl font-semibold text-rubric">Head to head</h2>
          <label className="flex items-center gap-2">
            <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">opponent</span>
            <select
              value={vs}
              onChange={onVsChange}
              className="border border-paper-line bg-paper-white px-2 py-1 font-mono text-xs uppercase tracking-wider-caps text-ink"
            >
              {vsList.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
        </div>

        {h2hLoading && <p className="mt-3 font-serif text-xs italic text-ink-faint" role="status">Setting the fixture…</p>}
        {h2hError && !h2hLoading && (
          <p className="mt-3 font-serif text-xs italic text-rubric">This fixture could not be set — try another opponent.</p>
        )}
        {h2h && !h2hLoading && !h2hError && (
          <>
            <p className="mt-3 font-serif text-sm italic text-ink-soft">
              {h2h.summary.meetings} meetings · {teamShort(h2h.team_a)} {h2h.summary.team_a_wins}–{h2h.summary.draws}–{h2h.summary.team_b_wins} {teamShort(h2h.team_b)}
              · {teamShort(h2h.team_a)} scored {h2h.summary.team_a_for}, conceded {h2h.summary.team_a_against}
            </p>
            <div className="mt-3">
              {h2h.meetings.length === 0 ? (
                <p className="font-serif text-xs italic text-ink-faint">No recorded meetings in the training ledger.</p>
              ) : (
                h2h.meetings.map((m) => (
                  <div key={m.date + m.home_team + m.away_team} className="flex flex-wrap items-center justify-between gap-x-3 border-t border-paper-line py-2.5">
                    <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">{m.date}</span>
                    <span className="min-w-0 truncate font-sans text-sm font-bold uppercase tracking-caps text-ink">
                      {teamShort(m.home_team)} <span className="font-mono font-normal text-ink-faint">{m.home_goals}–{m.away_goals}</span> {teamShort(m.away_team)}
                    </span>
                    <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-soft">
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