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

const INK_DARK = '#2A2A29';
const INK_PAPER = '#FBF7EC';
// Pure black only wins on bright reds, where neither house ink reaches 4.5:1.
const INK_BLACK = '#000000';
const GROUND = '#0F1114';
const CHALK = '#E9E6DF';

function luminance(hex: string): number {
  const h = hex.replace('#', '');
  const lin = (i: number) => {
    const c = parseInt(h.slice(i, i + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(0) + 0.7152 * lin(2) + 0.0722 * lin(4);
}

function contrast(a: string, b: string): number {
  const [la, lb] = [luminance(a), luminance(b)];
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

/** Ink on bright club inks, cream on dark ones — initials must never sink into the plate. */
export function clubTextColor(hex: string): string {
  return [INK_DARK, INK_PAPER, INK_BLACK].reduce((best, ink) => (contrast(ink, hex) > contrast(best, hex) ? ink : best));
}

/** A club colour made legible as text on the graphite ground: blended toward
 *  chalk just far enough to clear 4.5:1, so navy stays navy-toned. */
export function readableInk(hex: string, background = GROUND): string {
  const mix = (t: number) => {
    const channel = (i: number) => {
      const a = parseInt(hex.replace('#', '').slice(i, i + 2), 16);
      const b = parseInt(CHALK.slice(1 + i, 3 + i), 16);
      return Math.round(a + (b - a) * t).toString(16).padStart(2, '0');
    };
    return `#${channel(0)}${channel(2)}${channel(4)}`;
  };
  for (let t = 0; t <= 1; t += 0.05) {
    const ink = mix(t);
    if (contrast(ink, background) >= 4.5) return ink;
  }
  return CHALK;
}

/** Names as fans say them — long official names don't fit a fixture card. */
const DISPLAY_NAMES: Record<string, string> = {
  'Manchester United': 'Man Utd',
  'Manchester City': 'Man City',
  'Newcastle United': 'Newcastle',
  'Tottenham Hotspur': 'Spurs',
  'Tottenham': 'Spurs',
  'Brighton and Hove Albion': 'Brighton',
  'Brighton & Hove Albion': 'Brighton',
  'Wolverhampton Wanderers': 'Wolves',
  'Nottingham Forest': "Nott'm Forest",
  "Nott'ham Forest": "Nott'm Forest",
  'West Ham United': 'West Ham',
  'AFC Bournemouth': 'Bournemouth',
  'Leicester City': 'Leicester',
  'Leeds United': 'Leeds',
  'Ipswich Town': 'Ipswich',
  'Sheffield United': 'Sheffield Utd',
  'West Bromwich Albion': 'West Brom',
};

/** The short, spoken form of a club name for cards and call stamps. */
export function displayName(team: string | Team): string {
  const name = teamName(team);
  return DISPLAY_NAMES[name] ?? name.replace(/\s+(F\.?C\.?|A\.?F\.?C\.?)$/i, '');
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
