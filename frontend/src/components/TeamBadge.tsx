import { useState } from 'react';
import type { Team } from '../types';

interface TeamBadgeProps {
  team: Team;
  size?: 'small' | 'medium' | 'large';
}

export default function TeamBadge({ team, size = 'medium' }: TeamBadgeProps) {
    const [hasError, setHasError] = useState(false);

    const sizeClasses: Record<string, { wrapper: string; img: string }> = {
        small: { wrapper: '36px', img: '28px' },
        medium: { wrapper: '56px', img: '40px' },
        large: { wrapper: '72px', img: '56px' }
    };

    const dimensions = sizeClasses[size] || sizeClasses.medium;

    const getInitials = (name: string) => {
        if (!name) return '??';
        return name
            .split(' ')
            .map(word => word[0])
            .join('')
            .substring(0, 3)
            .toUpperCase();
    };

    const badgeUrl = team?.badge_url;
    const teamName = team?.name || 'Unknown';
    const shortName = team?.short_name || getInitials(teamName);

    return (
        <div
            className="team-badge"
            style={{ width: dimensions.wrapper, height: dimensions.wrapper }}
            title={teamName}
        >
            {badgeUrl && !hasError ? (
                <img
                    src={badgeUrl}
                    alt={`${teamName} badge`}
                    style={{ width: dimensions.img, height: dimensions.img }}
                    onError={() => setHasError(true)}
                    loading="lazy"
                />
            ) : (
                <span className="team-badge-fallback">{shortName}</span>
            )}
        </div>
    );
}
