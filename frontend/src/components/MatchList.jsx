import MatchCard from './MatchCard';

/**
 * MatchList Component
 * Displays list of matches, optionally grouped by date
 */
export default function MatchList({ matches, groupByDate = false }) {
    if (!matches || matches.length === 0) {
        return (
            <div className="empty-state glass-card">
                <div className="empty-icon">📅</div>
                <h3 className="empty-title">No Matches Found</h3>
                <p className="empty-description">
                    Check back later for upcoming Premier League fixtures and predictions.
                </p>
            </div>
        );
    }

    // Group matches by date if requested
    if (groupByDate) {
        const grouped = matches.reduce((acc, match) => {
            const date = match.date || 'Unknown';
            if (!acc[date]) {
                acc[date] = [];
            }
            acc[date].push(match);
            return acc;
        }, {});

        const sortedDates = Object.keys(grouped).sort();

        return (
            <div className="match-list">
                {sortedDates.map(date => (
                    <div key={date} className="date-group">
                        <div className="date-header">
                            <span className="date-label">{formatDateHeader(date)}</span>
                            <span className="date-count">{grouped[date].length} matches</span>
                        </div>
                        {grouped[date].map((match, index) => (
                            <MatchCard
                                key={match.id || `${match.home_team}-${match.away_team}-${index}`}
                                match={match}
                                index={index}
                            />
                        ))}
                    </div>
                ))}
            </div>
        );
    }

    // Simple list without grouping
    return (
        <div className="match-list">
            {matches.map((match, index) => (
                <MatchCard
                    key={match.id || `${match.home_team}-${match.away_team}-${index}`}
                    match={match}
                    index={index}
                />
            ))}
        </div>
    );
}

/**
 * Format date for group header
 */
function formatDateHeader(dateStr) {
    if (!dateStr || dateStr === 'Unknown') return 'Upcoming';

    const date = new Date(dateStr);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    // Check if it's today or tomorrow
    if (date.toDateString() === today.toDateString()) {
        return 'Today';
    }
    if (date.toDateString() === tomorrow.toDateString()) {
        return 'Tomorrow';
    }

    return date.toLocaleDateString('en-GB', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    });
}
