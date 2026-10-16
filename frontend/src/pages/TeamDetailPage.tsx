import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link, useParams } from 'react-router-dom';
import { motion, type Variants } from 'motion/react';
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
import { useLoad } from '../lib/load';
import { useMotionVariants } from '../lib/motion';
import type { EloPoint, FormEntry, H2HData, Match, SeasonRow, TeamProfileData } from '../types';

export default function TeamDetailPage() {
  const { teamName = '' } = useParams();
  const [state, reload] = useLoad(() => getTeamProfile(teamName), [teamName]);
  const { head: headV } = useMotionVariants();

  if (state.status === 'loading') return <div className="mx-auto max-w-3xl px-4 pb-4"><Press /></div>;
  if (state.status === 'error') {
    return (
      <div className="mx-auto max-w-3xl px-4 pb-4">
        <OfflineSlate
          message="This club's page could not be set. Check that the press (FastAPI) is running."
          onRetry={reload}
        />
      </div>
    );
  }

  const { data } = state;
  const seasons = data.seasons ?? [];
  const form = data.form ?? [];
  const elo = data.elo_history ?? [];
  const upcoming = data.upcoming ?? [];

  return (
    <div className="mx-auto max-w-3xl px-4 pb-4">
      <ClubHeader data={data} variants={headV} />
      {seasons.length > 0 && <SeasonLedger seasons={seasons} />}
      {form.length > 0 && <FormStrip form={form} />}
      {elo.length > 0 && <RatingChart elo={elo} />}
      {upcoming.length > 0 && <UpcomingFixtures upcoming={upcoming} />}
      {seasons.length === 0 && form.length === 0 && elo.length === 0 && (
        <div className="mt-8">
          <EmptyState
            title="This page is blank"
            note="No records for this club in the training ledger. It may be a newly promoted side."
          />
        </div>
      )}
      <HeadToHead teamName={teamName} profileTeam={data.team} />
    </div>
  );
}

/** One ruled section of the club's page: a display title, an optional aside, the body. */
function Section({ title, aside, first = false, children }: { title: ReactNode; aside?: ReactNode; first?: boolean; children: ReactNode }) {
  const heading = <h2 className="font-display text-[1.75rem] font-extrabold uppercase leading-none text-chalk">{title}</h2>;
  return (
    <section className={`rule-double ${first ? 'mt-8' : 'mt-10'} pt-3`}>
      {aside ? <div className="flex flex-wrap items-baseline justify-between gap-2">{heading}{aside}</div> : heading}
      {children}
    </section>
  );
}

/** Back link, crest, club name and this season's line. */
function ClubHeader({ data, variants }: { data: TeamProfileData; variants: Variants }) {
  const latest = data.seasons?.[0];
  return (
    <motion.div variants={variants} initial="hidden" animate="show" className="pt-4">
      {/* 44px hit area; the padding above is trimmed so the text stays put. */}
      <Link to="/teams" className="inline-flex min-h-[44px] items-center font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-faint no-underline hover:text-chalk">
        ← The Teams Index
      </Link>
      <div className="flex items-center gap-3">
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
  );
}

const LEDGER_COLS = 'sm:grid-cols-[5rem_1fr_1fr_1fr_1fr_1fr_1fr_3rem]';

/** Season-by-season table: played, won, drawn, lost, goals and points. */
function SeasonLedger({ seasons }: { seasons: SeasonRow[] }) {
  return (
    <Section title="The ledger of the club" first>
      <div className="mt-3">
        <div className={`hidden sm:grid ${LEDGER_COLS} gap-x-2 px-2 pb-1 font-mono text-micro uppercase tracking-widest text-chalk-faint`}>
          <span>Season</span><span className="text-right">P</span><span className="text-right">W</span>
          <span className="text-right">D</span><span className="text-right">L</span>
          <span className="text-right">GF</span><span className="text-right">GA</span><span className="text-right">Pts</span>
        </div>
        {seasons.map((s) => (
          <div key={s.season_year} className={`grid grid-cols-4 items-center gap-x-2 border-t border-line py-2.5 ${LEDGER_COLS} sm:px-2`}>
            <span className="font-mono text-sm text-chalk">{s.season_year}-{String(s.season_year + 1).slice(2)}</span>
            {[s.played, s.wins, s.draws, s.losses, s.gf, s.ga].map((v, i) => (
              <span key={i} className="text-right font-mono text-sm text-chalk-soft tnum">{v}</span>
            ))}
            <span className="text-right font-mono text-sm font-semibold text-chalk tnum">{s.points}</span>
          </div>
        ))}
      </div>
    </Section>
  );
}

const FORM_STYLE: Record<string, string> = {
  W: 'border-chalk bg-chalk text-ground',
  L: 'border-line-strong text-chalk-faint',
};

/** The last few results as W / D / L tiles. */
function FormStrip({ form }: { form: FormEntry[] }) {
  return (
    <Section title={`Form — last ${form.length}`}>
      <div className="mt-3 flex flex-wrap gap-2">
        {form.map((f, i) => (
          <span
            key={f.date + i}
            className={`flex h-9 w-9 items-center justify-center border font-mono text-sm font-semibold ${FORM_STYLE[f.result] ?? 'border-draw bg-draw text-chalk'}`}
            title={`${f.date} · ${teamShort(f.home_team)} ${f.home_goals}-${f.away_goals} ${teamShort(f.away_team)}`}
          >
            {f.result}
          </span>
        ))}
      </div>
    </Section>
  );
}

/** The club's Elo over time. */
function RatingChart({ elo }: { elo: EloPoint[] }) {
  return (
    <Section
      title="Club rating"
      aside={<span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-faint">latest {elo[elo.length - 1].elo}</span>}
    >
      <div className="mt-4">
        <SvgLineChart points={elo.map((e) => ({ x: e.date, y: e.elo }))} />
      </div>
      <p className="mt-2 font-sans text-xs italic text-chalk-faint">
        The club's Elo rating before each of its matches, five seasons back.
      </p>
    </Section>
  );
}

function sideName(team: Match['home_team']): string {
  return typeof team === 'string' ? team : team?.name ?? '';
}

/** The club's next fixtures with the model's call and its inputs. */
function UpcomingFixtures({ upcoming }: { upcoming: Match[] }) {
  return (
    <Section title="Fixtures to come">
      <div className="mt-3">
        {upcoming.map((m) => {
          const pred = m.prediction;
          return (
            <article key={m.id} className="border-t border-line py-3">
              <div className="flex items-center justify-between gap-2">
                <span className="font-sans text-xs italic text-chalk-faint">{printDate(m.date)}</span>
                <span className="min-w-0 truncate font-sans text-sm font-bold uppercase tracking-caps text-chalk">
                  {teamShort(sideName(m.home_team))} <span className="font-mono font-normal text-chalk-faint">vs</span> {teamShort(sideName(m.away_team))}
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
    </Section>
  );
}

type H2HLoad = { key: string; data: H2HData | null; error: boolean };

/** Head-to-head record against an opponent picked from this season's clubs. */
function HeadToHead({ teamName, profileTeam }: { teamName: string; profileTeam: string }) {
  const { teams } = useData();
  // Opponents by slug; the club itself is excluded.
  const vsList = useMemo(
    () => teams
      .filter((t) => t.name !== profileTeam && t.slug !== teamName && t.name !== teamName)
      .map((t) => ({ value: t.slug || t.name, label: t.name }))
      .sort((a, b) => a.label.localeCompare(b.label)),
    [teams, profileTeam, teamName],
  );
  const [picked, setPicked] = useState('');
  const vs = picked || vsList[0]?.value || '';
  const key = vs ? `${teamName}|${vs}` : '';
  const [loaded, setLoaded] = useState<H2HLoad>({ key: '', data: null, error: false });

  useEffect(() => {
    if (!key) return;
    let cancelled = false;
    getHeadToHead(teamName, vs)
      .then((data) => { if (!cancelled) setLoaded({ key, data, error: false }); })
      .catch(() => { if (!cancelled) setLoaded({ key, data: null, error: true }); });
    return () => { cancelled = true; };
  }, [teamName, vs, key]);

  const loading = !!key && loaded.key !== key;
  const h2h = loading ? null : loaded.data;

  return (
    <Section
      title="Head to head"
      aside={
        <label className="flex items-center gap-2">
          <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-faint">opponent</span>
          <select
            value={vs}
            onChange={(e) => setPicked(e.target.value)}
            className="border border-line bg-raised px-2 py-1 font-mono text-xs uppercase tracking-wider-caps text-chalk [@media(pointer:coarse)]:min-h-[44px]"
          >
            {vsList.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </label>
      }
    >
      {loading && <p className="mt-3 font-sans text-xs italic text-chalk-faint" role="status">Setting the fixture…</p>}
      {!loading && loaded.error && (
        <p className="mt-3 font-sans text-xs italic text-chalk-faint">This fixture could not be set — try another opponent.</p>
      )}
      {h2h && !loaded.error && <H2HRecord h2h={h2h} />}
    </Section>
  );
}

function H2HRecord({ h2h }: { h2h: H2HData }) {
  const { summary } = h2h;
  return (
    <>
      <p className="mt-3 font-sans text-sm italic text-chalk-soft">
        {summary.meetings} meetings · {teamShort(h2h.team_a)} {summary.team_a_wins}–{summary.draws}–{summary.team_b_wins} {teamShort(h2h.team_b)}
        · {teamShort(h2h.team_a)} scored {summary.team_a_for}, conceded {summary.team_a_against}
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
  );
}
