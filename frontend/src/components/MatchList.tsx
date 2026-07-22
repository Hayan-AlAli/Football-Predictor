import MatchCard from './MatchCard';
import type { Match } from '../types';

interface MatchListProps {
  matches: Match[];
}

export default function MatchList({ matches }: MatchListProps) {
    if (!matches || matches.length === 0) {
        return (
            <div className="empty-state glass-card">
                <h3 className="empty-title">No Matches Found</h3>
                <p className="empty-description">
                    Check back later for upcoming Premier League fixtures and predictions.
                </p>
            </div>
        );
    }

    const grouped = matches.reduce<Record<string, Match[]>>((acc, match) => {
        const date = match.date || 'Unknown';
        if (!acc[date]) {
            acc[date] = [];
        }
        acc[date].push(match);
        return acc;
    }, {});

    const sortedDates = Object.keys(grouped).sort();

    return (
        <div className="pl-match-list">
            {sortedDates.map(date => (
                <div key={date} className="pl-date-group">
                    <div className="pl-date-header">
                        <span className="pl-date-label">{formatDateHeader(date)}</span>
                        <span className="pl-date-count">{grouped[date].length} matches</span>
                    </div>
                    <div className="pl-date-matches">
                        {grouped[date].map((match, index) => (
                            <MatchCard
                                key={match.id || `${match.home_team}-${match.away_team}-${index}`}
                                match={match}
                            />
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}

function formatDateHeader(dateStr: string) {
    if (!dateStr || dateStr === 'Unknown') return 'Upcoming';

    const date = new Date(dateStr);

    return date.toLocaleDateString('en-GB', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    });
}
