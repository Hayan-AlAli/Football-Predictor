import TeamBadge from './TeamBadge';
import PredictionBar from './PredictionBar';

/**
 * MatchCard Component
 * Displays a single match with teams, time, and prediction
 */
export default function MatchCard({ match, index = 0 }) {
    // Determine team info based on data structure
    const homeTeam = match.home_team_info || match.home_team || {};
    const awayTeam = match.away_team_info || match.away_team || {};

    const homeTeamName = typeof homeTeam === 'string' ? homeTeam : homeTeam.name;
    const awayTeamName = typeof awayTeam === 'string' ? awayTeam : awayTeam.name;

    // Format date
    const formatDate = (dateStr) => {
        if (!dateStr) return 'TBD';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-GB', {
            weekday: 'short',
            day: 'numeric',
            month: 'short'
        });
    };

    // Format time
    const formatTime = (timeStr) => {
        if (!timeStr || timeStr === 'Unknown' || timeStr === 'TBD') return 'TBD';
        return timeStr;
    };

    const prediction = match.prediction;

    return (
        <div
            className={`glass-card match-card fade-in stagger-${(index % 5) + 1}`}
            id={`match-${match.id}`}
        >
            {/* Match Header */}
            <div className="match-header">
                <div className="match-meta">
                    <span className="match-date">{formatDate(match.date)}</span>
                    <span className="match-time">{formatTime(match.time)}</span>
                </div>
                {match.gameweek && (
                    <span className="match-gameweek">GW{match.gameweek}</span>
                )}
            </div>

            {/* Teams */}
            <div className="teams-container">
                {/* Home Team */}
                <div className="team team--home">
                    <TeamBadge
                        team={typeof homeTeam === 'string'
                            ? { name: homeTeam, badge_url: null }
                            : homeTeam
                        }
                    />
                    <div className="team-info">
                        <span className="team-name">{homeTeamName}</span>
                    </div>
                </div>

                {/* VS */}
                <div className="vs-badge">VS</div>

                {/* Away Team */}
                <div className="team team--away">
                    <TeamBadge
                        team={typeof awayTeam === 'string'
                            ? { name: awayTeam, badge_url: null }
                            : awayTeam
                        }
                    />
                    <div className="team-info">
                        <span className="team-name">{awayTeamName}</span>
                    </div>
                </div>
            </div>

            {/* Prediction */}
            {prediction && (
                <PredictionBar
                    prediction={prediction}
                    homeTeam={homeTeamName}
                    awayTeam={awayTeamName}
                />
            )}
        </div>
    );
}
