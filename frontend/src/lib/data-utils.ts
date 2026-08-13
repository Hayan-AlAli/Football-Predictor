import type { Match, Team } from '../types';

/** Season of a "YYYY-MM-DD" date (August cut, as the backend computes it). */
export function seasonOf(date: string): string {
  const [y, m] = date.split('-').map(Number);
  if (!y || !m) return '';
  const start = m >= 8 ? y : y - 1;
  return `${start}/${String(start + 1).slice(2)}`;
}

export function seasonFromMatches(matches: Match[]): string {
  if (matches.length === 0) return '';
  const dates = matches.map((m) => m.date).sort();
  return seasonOf(dates[0]) || seasonOf(dates[dates.length - 1]);
}

export interface TeamMeta {
  name: string;
  short_name: string;
  badge_url: string | null;
}

/** team names present in the ledger (from matches), as TeamMeta-like shapes. */
export function teamsFromMatches(matches: Match[]): TeamMeta[] {
  const map = new Map<string, TeamMeta>();
  for (const m of matches) {
    for (const side of [m.home_team_info ?? m.home_team, m.away_team_info ?? m.away_team] as (string | Team)[]) {
      const name = typeof side === 'string' ? side : side.name;
      if (!name || map.has(name)) continue;
      map.set(name, {
        name,
        short_name: typeof side === 'string' ? '' : (side.short_name ?? ''),
        badge_url: typeof side === 'string' ? null : (side.badge_url ?? null),
      });
    }
  }
  return [...map.values()];
}
