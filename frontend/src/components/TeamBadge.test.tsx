import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import TeamBadge from './TeamBadge';
import { registerTeams, teamBadges, teamInk } from '../lib/teams';

describe('TeamBadge', () => {
  it('renders an image badge without a background plate or border', () => {
    const markup = renderToStaticMarkup(
      <TeamBadge
        team="Arsenal"
        info={{ name: 'Arsenal', short_name: 'ARS', badge_url: 'https://example.com/arsenal.svg' }}
      />,
    );

    expect(markup).toContain('inline-flex');
    expect(markup).toContain('rounded-sm');
    expect(markup).toContain('width="32"');
    expect(markup).not.toContain('bg-raised');
    expect(markup).not.toContain('border-line');
    expect(markup).not.toMatch(/\bborder\b/);
  });

  it('prints initials in the club colour when no crest is known', () => {
    const markup = renderToStaticMarkup(
      <TeamBadge team={{ name: 'Nowhere Rovers', short_name: 'NOW', color: '#003399' }} />,
    );
    expect(markup).toContain('NOW');
    expect(markup).toContain('background-color:#003399');
  });
});

describe('team registry', () => {
  it('resolves colour and crests from a bare name once teams are registered', () => {
    registerTeams([{
      name: 'Hull', slug: 'hull-city', color: '#FF6600',
      badge_url: 'https://a.example/306.png', badge_fallback_url: 'https://b.example/t88.png',
    }]);
    expect(teamInk('Hull')).toBe('#FF6600');
    expect(teamBadges('Hull')).toEqual(['https://a.example/306.png', 'https://b.example/t88.png']);
  });

  it('falls back to the default ink for unknown or malformed colours', () => {
    expect(teamInk('Unknown FC')).toBe('#6A6355');
    expect(teamInk({ name: 'X', color: 'red' })).toBe('#6A6355');
  });
});
