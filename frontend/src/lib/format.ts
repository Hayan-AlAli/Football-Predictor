import type { Match } from '../types';

/** Probability 0..1 → printed percentage figure, no decimals for the page. */
export function percent(p: number | undefined | null, decimals = 0): string {
  if (p == null || Number.isNaN(p)) return '—';
  const v = p * 100;
  if (decimals > 0) return v.toFixed(decimals);
  const r = Math.round(v);
  if (r === 0 && v > 0) return '<1%';
  if (r === 100 && v < 100) return '>99%';
  return r.toString();
}

/** Expected scoreline "2 – 1" from the backend's "2-1" or components. */
export function scoreline(score: string | undefined | null): string {
  if (!score) return '—';
  return score.replace(/\s*-\s*/g, ' – ');
}

/** Backend dates are "YYYY-MM-DD"; print them like a fixture list. */
export function printDate(date: string): string {
  const d = new Date(`${date}T00:00:00`);
  if (Number.isNaN(d.getTime())) return date;
  return d.toLocaleDateString('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  });
}

export function shortDate(date: string): string {
  const d = new Date(`${date}T00:00:00`);
  if (Number.isNaN(d.getTime())) return date;
  return d.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
  });
}

export function sortMatchesByDate(matches: Match[]): Match[] {
  return [...matches].sort((a, b) => a.date.localeCompare(b.date) || (a.time ?? '').localeCompare(b.time ?? ''));
}

/** The model's strongest call in a fixture, from the real probabilities. */
export function strongestCall(match: Match) {
  const p = match.prediction;
  if (!p) return null;
  const entries = [
    { key: 'H' as const, value: p.prob_home },
    { key: 'D' as const, value: p.prob_draw },
    { key: 'A' as const, value: p.prob_away },
  ];
  const best = entries.reduce((a, b) => (b.value > a.value ? b : a));
  return { ...best, confidence: best.value };
}

export function gameweekLabel(gameweek: number | undefined): string {
  return gameweek == null ? '—' : String(gameweek).padStart(2, '0');
}
