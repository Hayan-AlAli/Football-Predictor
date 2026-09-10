import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import TeamBadge from './TeamBadge';

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
    expect(markup).not.toContain('bg-paper-white');
    expect(markup).not.toContain('border-paper-line');
    expect(markup).not.toMatch(/\bborder\b/);
  });
});
