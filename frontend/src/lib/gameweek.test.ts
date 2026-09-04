import { describe, expect, it } from 'vitest';
import { currentGameweek } from './gameweek';
import type { Match } from '../types';

const mk = (date: string, gameweek: number): Match =>
  ({ id: `${date}`, date, gameweek, home_team: 'A', away_team: 'B' }) as Match;

describe('currentGameweek', () => {
  const matches = [mk('2026-08-22', 1), mk('2026-08-29', 2), mk('2026-09-05', 3)];

  it('picks the gameweek containing today', () => {
    expect(currentGameweek([1, 2, 3], matches, '2026-08-29')).toBe(2);
  });

  it('falls back to the nearest upcoming gameweek', () => {
    expect(currentGameweek([1, 2, 3], matches, '2026-08-25')).toBe(2);
  });

  it('falls back to the latest gameweek past the end', () => {
    expect(currentGameweek([1, 2, 3], matches, '2026-12-01')).toBe(3);
  });

  it('returns null for empty input', () => {
    expect(currentGameweek([], [], '2026-08-29')).toBeNull();
  });
});
