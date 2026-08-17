import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import Press from '../components/Press';
import OfflineSlate from '../components/OfflineSlate';
import EmptyState from '../components/EmptyState';
import TeamBadge from '../components/TeamBadge';
import { useData } from '../lib/data-context';
import { teamsFromMatches } from '../lib/data-utils';
import { teamShort, teamInk } from '../lib/teams';
import { getReducedMotionVariants, headVariants, ledgerVariants, staggerContainer } from '../lib/motion';
import type { Match } from '../types';

interface ClubRow {
  name: string;
  short_name: string;
  badge_url: string | null;
  fixtures: number;
  expFor: number | null;
  elo: number | null;
}

function clubStats(matches: Match[], name: string): Omit<ClubRow, 'name' | 'short_name' | 'badge_url'> {
  let fixtures = 0;
  let expSum = 0;
  let expN = 0;
  let elo: number | null = null;
  let eloDate = '';
  for (const m of matches) {
    const homeName = typeof m.home_team === 'string' ? m.home_team : m.home_team.name;
    const awayName = typeof m.away_team === 'string' ? m.away_team : m.away_team.name;
    const isHome = homeName === name;
    const isAway = awayName === name;
    if (!isHome && !isAway) continue;
    fixtures += 1;
    const pred = m.prediction;
    if (pred) {
      const gf = isHome ? pred.home_goals : pred.away_goals;
      if (gf != null && !Number.isNaN(gf)) {
        expSum += gf;
        expN += 1;
      }
      const e = isHome ? pred.home_elo : pred.away_elo;
      if (e != null && m.date >= eloDate) {
        elo = e;
        eloDate = m.date;
      }
    }
  }
  return {
    fixtures,
    expFor: expN > 0 ? expSum / expN : null,
    elo,
  };
}

/** The Teams Index — every club's page of the ledger. */
export default function TeamsPage() {
  const { status, matches, teams, reload } = useData();
  const reduce = useReducedMotion();
  const headV = reduce ? getReducedMotionVariants(headVariants) : headVariants;
  const staggerV = reduce ? getReducedMotionVariants(staggerContainer) : staggerContainer;
  const rowV = reduce ? getReducedMotionVariants(ledgerVariants) : ledgerVariants;

  const clubs = useMemo(() => {
    const known = teams.length > 0 ? teams : teamsFromMatches(matches);
    const rows: ClubRow[] = known.map((t) => ({ ...t, ...clubStats(matches, t.name) }));
    rows.sort((a, b) => a.name.localeCompare(b.name));
    return rows;
  }, [teams, matches]);

  const letters = useMemo(() => [...new Set(clubs.map((c) => c.name[0]?.toUpperCase() ?? '?'))], [clubs]);

  const groups = useMemo(() => {
    const map = new Map<string, ClubRow[]>();
    for (const c of clubs) {
      const letter = c.name[0]?.toUpperCase() ?? '?';
      const list = map.get(letter) ?? [];
      list.push(c);
      map.set(letter, list);
    }
    return [...map.entries()];
  }, [clubs]);

  return (
    <div className="mx-auto max-w-3xl px-4 pb-4">
      <motion.div variants={headV} initial="hidden" animate="show" className="pt-8">
        <h1 className="mt-1 font-sans text-2xl sm:text-3xl font-extrabold uppercase tracking-caps text-ink">
          The Teams Index
        </h1>
        <p className="mt-2 font-serif text-sm italic text-ink-soft sm:text-base">
          Each club's page of the ledger: the fixtures the press has set them in, their average expected goals,
          and their latest club rating.
        </p>
      </motion.div>

      {status === 'loading' && <Press />}
      {status === 'offline' && (
        <OfflineSlate message="The index cannot be set while the backend is unreachable." onRetry={reload} />
      )}

      {status === 'online' && (
        <>
          {clubs.length === 0 ? (
            <EmptyState
              title="The index is blank"
              note="No clubs have been printed yet. Once the press has run, every club appears here."
            />
          ) : (
            <>
              {/* Index letters */}
              <nav aria-label="Club index letters" className="rule-draw mt-6 flex flex-wrap gap-1.5 py-2">
                {letters.map((l) => (
                  <a
                    key={l}
                    href={`#letter-${l}`}
                    className="flex h-7 w-7 items-center justify-center border border-paper-line bg-paper-white font-mono text-xs text-ink-soft no-underline transition-colors hover:border-rubric hover:text-rubric"
                  >
                    {l}
                  </a>
                ))}
              </nav>

              {groups.map(([letter, list]) => (
                <section key={letter} id={`letter-${letter}`} className="mt-6 scroll-mt-24" style={{ contentVisibility: 'auto' }}>
                  <h2 className="rule-double pt-3 font-mono text-xl font-semibold text-rubric">{letter}</h2>
                  <motion.div variants={staggerV} initial="hidden" animate="show">
                    {list.map((club) => {
                      const ink = teamInk(club.name);
                      const short = club.short_name || teamShort(club.name);
                      return (
                        <motion.div
                          key={club.name}
                          variants={rowV}
                          initial="hidden"
                          animate="show"
                          className="grid grid-cols-[auto_1fr_auto] items-center gap-x-3 border-t border-paper-line py-3.5"
                        >
                          <Link
                            to={`/teams/${encodeURIComponent(club.name)}`}
                            className="col-span-2 flex min-w-0 items-center gap-3 no-underline"
                          >
                          <TeamBadge team={club.name} info={club} size="md" />
                          <span className="min-w-0">
                            <span className="flex items-center gap-2">
                              <span className="truncate font-sans text-sm font-bold uppercase tracking-caps text-ink">
                                {club.name}
                              </span>
                              <span
                                className="hidden sm:inline font-mono text-[0.625rem] uppercase tracking-widest"
                                style={{ color: ink }}
                              >
                                {short}
                              </span>
                            </span>
                            <span className="mt-0.5 block font-mono text-[0.625rem] uppercase tracking-wider-caps text-ink-faint">
                              {club.fixtures} fixture{club.fixtures === 1 ? '' : 's'} in the ledger
                              {club.expFor != null && ` · expected gf ${club.expFor.toFixed(1)}`}
                              {club.elo != null && ` · club rating ${club.elo}`}
                            </span>
                          </span>
                          </Link>
                          <span
                            className="hidden h-2 w-2 shrink-0 rounded-none border border-black/10 sm:block"
                            style={{ backgroundColor: ink }}
                            aria-hidden="true"
                          />
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
