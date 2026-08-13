import type { Team } from '../types';

/**
 * Club ink — the printed colors of the Premier League.
 * Team identities are real product data, kept here once instead of
 * duplicated across components.
 */
export const TEAM_COLORS: Record<string, string> = {
  'Manchester United': '#DA291C',
  'Manchester City': '#6CABDD',
  'Liverpool': '#C8102E',
  'Arsenal': '#EF0107',
  'Chelsea': '#034694',
  'Tottenham Hotspur': '#132257',
  'Tottenham': '#132257',
  'Newcastle United': '#241F20',
  'Newcastle': '#241F20',
  'Aston Villa': '#670E36',
  'Brighton': '#0057B8',
  'Brighton and Hove Albion': '#0057B8',
  'West Ham': '#7A263A',
  'West Ham United': '#7A263A',
  'Everton': '#003399',
  'Wolves': '#FDB913',
  'Wolverhampton Wanderers': '#FDB913',
  'Crystal Palace': '#1B458F',
  'Nottingham Forest': '#DD0000',
  'Fulham': '#333333',
  'Brentford': '#D30000',
  'Leicester': '#003090',
  'Leicester City': '#003090',
  'Southampton': '#D71920',
  'Bournemouth': '#DA291C',
  'AFC Bournemouth': '#DA291C',
  'Ipswich': '#003399',
  'Ipswich Town': '#003399',
  'Coventry City': '#339ACC',
  'Hull City': '#FF6600',
  'Hull': '#FF6600',
  'Leeds United': '#1D4491',
  'Leeds': '#1D4491',
  'Sunderland': '#EB172B',
};

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
  const info = typeof team === 'string' ? null : team;
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
  const name = teamName(team);
  const lower = name.toLowerCase();
  for (const [key, color] of Object.entries(TEAM_COLORS)) {
    if (lower.includes(key.toLowerCase())) return color;
  }
  return DEFAULT_CLUB_INK;
}

export function teamBadge(team: string | Team): string | null {
  const info = typeof team === 'string' ? null : team;
  return info?.badge_url ?? null;
}

/** The team's short name for a fixture row (favours the backend's short_name). */
export function fixtureTeamShort(team: string | Team, info?: Team): string {
  if (info?.short_name) return info.short_name;
  return teamShort(team);
}
