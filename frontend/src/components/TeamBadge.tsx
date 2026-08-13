import { useState } from 'react';
import { teamShort, teamInk, clubTextColor } from '../lib/teams';
import type { Team } from '../types';

const SIZES = {
  sm: 'w-6 h-6',
  md: 'w-8 h-8',
  lg: 'w-10 h-10',
} as const;

interface TeamBadgeProps {
  team: string | Team;
  info?: Team;
  size?: keyof typeof SIZES;
  className?: string;
}

/** A printed club plate: the badge, or the club's initials set in its own ink. */
export default function TeamBadge({ team, info, size = 'md', className = '' }: TeamBadgeProps) {
  const [failed, setFailed] = useState(false);
  const badge = info?.badge_url ?? (typeof team !== 'string' ? team.badge_url : undefined);
  const ink = teamInk(info ?? team);

  if (badge && !failed) {
    return (
      <span
        className={`inline-flex shrink-0 items-center justify-center overflow-hidden rounded-sm bg-paper-white border border-paper-line ${SIZES[size]} ${className}`}
      >
        <img
          src={badge}
          alt=""
          loading="lazy"
          className="h-full w-full object-contain"
          onError={() => setFailed(true)}
        />
      </span>
    );
  }

  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-sm border border-paper-line font-sans text-[10px] font-bold tracking-widest ${SIZES[size]} ${className}`}
      style={{ backgroundColor: ink, color: clubTextColor(ink) }}
      aria-hidden="true"
    >
      {teamShort(info ?? team)}
    </span>
  );
}
