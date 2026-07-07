import { useState } from 'react';

/**
 * TeamBadge Component
 * Displays team badge/logo with fallback to initials
 */
export default function TeamBadge({ team, size = 'medium' }) {
    const [hasError, setHasError] = useState(false);

    const sizeClasses = {
        small: { wrapper: '40px', img: '32px' },
        medium: { wrapper: '64px', img: '48px' },
        large: { wrapper: '80px', img: '64px' }
    };

    const dimensions = sizeClasses[size] || sizeClasses.medium;

    // Generate initials fallback
    const getInitials = (name) => {
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
