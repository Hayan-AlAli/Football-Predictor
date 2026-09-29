import type { Team } from '../types';

/**
 * Club identity comes from the API (backend data/teams.json, refreshed from
 * the fixtures feed). The data provider registers every club it loads, so
 * code holding only a team's name can still find its colour and badge.
 */
const registry = new Map<string, Team>();

export function registerTeams(teams: Team[]): void {
  for (const t of teams) {
    registry.set(t.name, t);
    if (t.slug) registry.set(t.slug, t);
    if (t.full_name) registry.set(t.full_name, t);
  }
}

/** The fullest description known for a team: the given object merged over the registry entry. */
export function teamInfo(team: string | Team): Team {
  const name = typeof team === 'string' ? team : team.name;
  const known = registry.get(name);
  if (typeof team === 'string') return known ?? { name };
  return { ...known, ...Object.fromEntries(Object.entries(team).filter(([, v]) => v != null && v !== '')), name };
}

export const DEFAULT_CLUB_INK = '#6A6355';

/** Ink on bright club inks, cream on dark ones — initials must never sink into the plate. */
export function clubTextColor(hex: string): string {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16) / 255;
  const g = parseInt(h.slice(2, 4), 16) / 255;
  const b = parseInt(h.slice(4, 6), 16) / 255;
  const lin = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  const l = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  return l > 0.15 ? '#2A2A29' : '#FBF7EC';
}

export function teamName(team: string | Team): string {
  return typeof team === 'string' ? team : team.name;
}

export function teamShort(team: string | Team): string {
  const info = teamInfo(team);
  if (info?.short_name) return info.short_name;
  const name = teamName(team);
  return name
    .replace(/^(AFC|Brighton and Hove Albion)\s*/i, '')
    .replace(/^(Manchester|Newcastle|Nottingham|Tottenham|West Bromwich)\s+/i, '')
    .split(/[\s&'\-.]/)
    .filter(Boolean)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('')
    .slice(0, 3);
}

export function teamInk(team: string | Team): string {
  const color = teamInfo(team).color;
  return color && /^#[0-9a-f]{6}$/i.test(color) ? color : DEFAULT_CLUB_INK;
}

/** Badge sources in the order to try them: the primary crest, then the fallback. */
export function teamBadges(team: string | Team): string[] {
  const info = teamInfo(team);
  return [info.badge_url, info.badge_fallback_url].filter((u): u is string => !!u);
}

/** The team's short name for a fixture row (favours the backend's short_name). */
export function fixtureTeamShort(team: string | Team, info?: Team): string {
  if (info?.short_name) return info.short_name;
  return teamShort(team);
}
