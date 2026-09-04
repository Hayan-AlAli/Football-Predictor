import type { Match } from '../types';

/** Gameweek whose matches contain today; else nearest upcoming, else latest. */
export function currentGameweek(
  gameweeks: number[],
  matches: Match[],
  today: string,
): number | null {
  if (gameweeks.length === 0) return null;
  const byGw = new Map<number, string[]>();
  for (const m of matches) {
    if (m.gameweek == null) continue;
    const list = byGw.get(m.gameweek) ?? [];
    list.push(m.date);
    byGw.set(m.gameweek, list);
  }
  // Exact-date match first (match dates are single days; every date of a
  // multi-day gameweek is in the list, so this covers whole weeks).
  const containing = gameweeks.find((gw) =>
    (byGw.get(gw) ?? []).includes(today),
  );
  if (containing != null) return containing;
  const upcoming = gameweeks
    .map((gw) => ({
      gw,
      first: (byGw.get(gw) ?? []).slice().sort()[0],
    }))
    .filter((x) => x.first != null && x.first >= today)
    .sort((a, b) => (a.first as string).localeCompare(b.first as string));
  if (upcoming.length > 0) return upcoming[0].gw;
  return gameweeks[gameweeks.length - 1];
}
