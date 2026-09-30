import { describe, expect, it } from 'vitest';
import { clubTextColor, readableInk } from './teams';

const lum = (hex: string) => {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const contrast = (a: string, b: string) => {
  const [x, y] = [lum(a), lum(b)];
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
};

// Arsenal, Man Utd, Forest, Spurs, Chelsea, Wolves, Newcastle, Man City.
const CLUBS = ['#EF0107', '#DA291C', '#DD0000', '#132257', '#034694', '#FDB913', '#241F20', '#6CABDD'];

describe('club inks', () => {
  it('badge initials clear 4.5:1 on every club colour', () => {
    for (const club of CLUBS) expect(contrast(clubTextColor(club), club)).toBeGreaterThanOrEqual(4.5);
  });

  it('club-coloured text clears 4.5:1 on the ground and keeps passing colours as they are', () => {
    for (const club of CLUBS) expect(contrast(readableInk(club), '#0F1114')).toBeGreaterThanOrEqual(4.5);
    expect(readableInk('#FDB913')).toBe('#fdb913');
  });
});
