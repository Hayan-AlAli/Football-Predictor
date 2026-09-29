import { useState } from 'react';
import { teamName, teamShort, teamInk, teamBadges, clubTextColor } from '../lib/teams';
import type { Team } from '../types';

const SIZES = {
  sm: { cls: 'w-6 h-6', px: 24 },
  md: { cls: 'w-8 h-8', px: 32 },
  lg: { cls: 'w-10 h-10', px: 40 },
} as const;

interface TeamBadgeProps {
  team: string | Team;
  info?: Team;
  size?: keyof typeof SIZES;
  className?: string;
}

/**
 * A printed club plate: the crest, or the club's initials set in its own ink.
 * Crest sources are tried in order (hi-res ESPN, then the Premier League's),
 * so one CDN hiccup never leaves a blank.
 */
export default function TeamBadge({ team, info, size = 'md', className = '' }: TeamBadgeProps) {
  const subject = info ?? team;
  const sources = teamBadges(subject);
  const [failed, setFailed] = useState<string[]>([]);
  const { cls, px } = SIZES[size];
  const src = sources.find((s) => !failed.includes(s));

  if (src) {
    return (
      <span className={`inline-flex shrink-0 items-center justify-center overflow-hidden rounded-sm ${cls} ${className}`}>
        <img
          key={src}
          src={src}
          alt={`${teamName(subject)} club badge`}
          width={px}
          height={px}
          loading="lazy"
          decoding="async"
          className="aspect-square h-full w-full object-contain"
          onError={() => setFailed((f) => [...f, src])}
        />
      </span>
    );
  }

  const ink = teamInk(subject);
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-sm border border-line font-sans text-[10px] font-bold tracking-widest ${cls} ${className}`}
      style={{ backgroundColor: ink, color: clubTextColor(ink) }}
      aria-hidden="true"
    >
      {teamShort(subject)}
    </span>
  );
}
