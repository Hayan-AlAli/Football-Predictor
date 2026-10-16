import { useState, type CSSProperties, type ReactNode } from 'react';
import { motion, AnimatePresence, type Variants } from 'motion/react';
import TeamBadge from './TeamBadge';
import FeatureReveal from './FeatureReveal';
import { displayName, teamName, teamShort } from '../lib/teams';
import { percent, scoreline, printDate, kickoffDay, strongestCall } from '../lib/format';
import { useMotionVariants } from '../lib/motion';
import type { Match, Prediction, ResultEntry } from '../types';

interface FixtureCardProps {
  match: Match;
  verdict?: ResultEntry;
}

type OutcomeKey = 'H' | 'D' | 'A';

const OUTCOMES = ['H', 'D', 'A'] as const;

/** Team names fit their column: sized by the card width over the longest
 *  word (see .team-name), so a long name shrinks and a short one stays full. */
function fitName(label: string): CSSProperties {
  const longest = Math.max(...label.split(/\s+/).map((w) => w.length));
  return { '--chars': longest } as CSSProperties;
}

/** The called side as the card prints it: a club's short name, or Draw. */
function callLabel(match: Match): string | null {
  const winner = match.prediction?.winner;
  if (!winner) return null;
  if (winner === 'Draw' || winner === 'draw') return 'Draw';
  return winner === teamName(match.home_team) ? displayName(match.home_team) : displayName(match.away_team);
}

function kickoffTime(match: Match): string | null {
  return match.time ? match.time.slice(0, 5) : null;
}

/** One fixture as a desk card: the call, the expected score, the split and the model's inputs. */
export default function FixtureCard({ match, verdict }: FixtureCardProps) {
  const [open, setOpen] = useState(false);
  const { ledger: variants, stamp: stampV } = useMotionVariants();
  const pred = match.prediction;
  const callKey = strongestCall(match)?.key;
  const homeName = teamName(match.home_team);
  const awayName = teamName(match.away_team);
  const plateId = `plate-${match.id}`;

  return (
    <motion.article
      variants={variants}
      initial="hidden"
      animate="show"
      exit="exit"
      className={`fixture-card flex flex-col ${open ? 'sm:col-span-2' : ''}`}
      aria-label={`${homeName} versus ${awayName}`}
    >
      <h2 className="sr-only">{homeName} v {awayName}</h2>
      <div className="flex flex-col gap-3.5 px-4 pb-4 pt-4 sm:px-5">
        <CallRow match={match} stampVariants={stampV} />
        <TeamsRow match={match} />
        {pred ? (
          <OutcomeSplit pred={pred} callKey={callKey} />
        ) : (
          <p className="font-mono text-xs uppercase tracking-caps text-chalk-faint">No prediction recorded</p>
        )}
        {pred && <ModelInputs pred={pred} />}
        <VerdictRow verdict={verdict} pred={pred}>
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
        </VerdictRow>
      </div>

      <AnimatePresence initial={false}>
        {open && pred && <WhyPlate id={plateId} match={match} pred={pred} callKey={callKey} />}
      </AnimatePresence>
    </motion.article>
  );
}

/** Kickoff on the left, the model's call stamped on the right. */
function CallRow({ match, stampVariants }: { match: Match; stampVariants: Variants }) {
  const kickoff = kickoffTime(match);
  const callText = callLabel(match);
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="shrink-0 whitespace-nowrap font-mono text-[0.6875rem] uppercase tracking-[0.1em] text-chalk-faint">
        {kickoffDay(match.date)}{kickoff ? ` · ${kickoff}` : ''}
      </span>
      {callText && (
        <motion.span variants={stampVariants} initial="hidden" animate="show" className="stamp min-w-0 truncate">
          Call · {callText}
        </motion.span>
      )}
    </div>
  );
}

/** Both clubs either side of the expected score. */
function TeamsRow({ match }: { match: Match }) {
  const score = match.prediction?.score;
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-end gap-3 [container-type:inline-size]">
      <TeamSide team={match.home_team} info={match.home_team_info} align="start" />
      <span className="bg-chalk px-3 py-1 font-mono text-xl font-semibold text-ground tnum">
        <span className="sr-only">Expected score: </span>
        {score ? scoreline(score).replace(/\s/g, '') : '–'}
      </span>
      <TeamSide team={match.away_team} info={match.away_team_info} align="end" />
    </div>
  );
}

function TeamSide({ team, info, align }: { team: Match['home_team']; info: Match['home_team_info']; align: 'start' | 'end' }) {
  const label = displayName(team);
  return (
    <span className={`flex min-w-0 flex-col gap-2 ${align === 'start' ? 'items-start' : 'items-end text-right'}`}>
      <TeamBadge team={team} info={info} size="md" />
      <span className="team-name min-w-0 font-display font-extrabold uppercase leading-[0.92] text-chalk [--name-max:1.625rem] sm:[--name-max:1.75rem]" style={fitName(label)}>
        {label}
      </span>
    </span>
  );
}

/** Home · draw · away split bar with the three percentages; the call in amber. */
function OutcomeSplit({ pred, callKey }: { pred: Prediction; callKey?: OutcomeKey }) {
  const probs = { H: pred.prob_home, D: pred.prob_draw, A: pred.prob_away };
  return (
    <>
      <div className="split-bar" aria-hidden="true">
        <span className="split-home" style={{ flex: `${probs.H} 1 0` }} />
        <span className="split-draw" style={{ flex: `${probs.D} 1 0` }} />
        <span className="split-away" style={{ flex: `${probs.A} 1 0` }} />
      </div>
      <div className="flex justify-between font-mono text-[0.8125rem] tnum">
        {OUTCOMES.map((k) => (
          <span key={k} className={callKey === k ? 'font-semibold text-amber' : 'text-chalk-soft'}>
            {k} {percent(probs[k])}%
          </span>
        ))}
      </div>
    </>
  );
}

/** The model's inputs, home left · away right. */
function ModelInputs({ pred }: { pred: Prediction }) {
  const features = pred.features;
  const homeElo = features?.home_elo ?? pred.home_elo;
  const awayElo = features?.away_elo ?? pred.away_elo;
  if (homeElo == null && !features) return null;
  return (
    <dl className="grid grid-cols-[4.5rem_minmax(0,1fr)_minmax(0,1fr)] items-center gap-y-1.5 border-t border-line pt-3 font-mono text-xs tnum">
      {homeElo != null && awayElo != null && (
        <InputRow label="ELO" home={Math.round(homeElo)} away={Math.round(awayElo)} />
      )}
      {features && (
        <>
          <InputRow label="GOALS" home={features.home_rolling_goals.toFixed(2)} away={features.away_rolling_goals.toFixed(2)} />
          <InputRow label="xG" home={features.home_rolling_xg.toFixed(2)} away={features.away_rolling_xg.toFixed(2)} />
        </>
      )}
    </dl>
  );
}

function InputRow({ label, home, away }: { label: string; home: string | number; away: string | number }) {
  return (
    <>
      <dt className="text-micro tracking-[0.1em] text-chalk-faint">{label}</dt>
      <dd>{home}</dd>
      <dd className="text-right">{away}</dd>
    </>
  );
}

/** Right / wrong / pending, the rebuilt tag and the full-time score; `children` is the fold-out toggle. */
function VerdictRow({ verdict, pred, children }: { verdict?: ResultEntry; pred: Prediction | null | undefined; children: ReactNode }) {
  // Calls rebuilt after kickoff from pre-match data (sync replaced a placeholder).
  const rebuilt = pred?.model_version?.endsWith('+rebuilt') ?? false;
  const actual = verdict?.actual?.score ?? (verdict?.actual ? `${verdict.actual.home_goals}-${verdict.actual.away_goals}` : null);
  return (
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
      {children}
    </div>
  );
}

/** The fold-out: goal expectation, outcome odds and the feature inputs behind the call. */
function WhyPlate({ id, match, pred, callKey }: { id: string; match: Match; pred: Prediction; callKey?: OutcomeKey }) {
  const kickoff = kickoffTime(match);
  const home = match.home_team_info ?? match.home_team;
  const away = match.away_team_info ?? match.away_team;
  const odds = [
    { key: 'H', label: `Home — ${teamShort(home)}`, v: pred.prob_home },
    { key: 'D', label: 'Draw', v: pred.prob_draw },
    { key: 'A', label: `Away — ${teamShort(away)}`, v: pred.prob_away },
  ];
  return (
    <motion.div
      id={id}
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
            <h3 className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-faint">Goal expectation</h3>
            <p className="mt-1 flex items-baseline gap-3 font-mono text-3xl font-semibold text-chalk tnum">
              <span>{pred.home_goals?.toFixed(1) ?? '—'}</span>
              <span className="text-base text-chalk-faint">—</span>
              <span>{pred.away_goals?.toFixed(1) ?? '—'}</span>
            </p>
            <p className="mt-1 text-xs italic text-chalk-faint">expected goals, model output</p>
          </div>

          <div>
            <h3 className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-chalk-faint">Outcome odds</h3>
            <div className="mt-3 space-y-2">
              {odds.map((row) => (
                <div key={row.key} className="flex items-center gap-2">
                  <span className="w-32 shrink-0 truncate font-mono text-micro uppercase tracking-widest text-chalk-soft">
                    {row.label}
                  </span>
                  <span className="h-2 flex-1 overflow-hidden bg-raised">
                    <span
                      className={`block h-full ${row.key === callKey ? 'bg-amber' : 'bg-chalk-faint'}`}
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
  );
}
