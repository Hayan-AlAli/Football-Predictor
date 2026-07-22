import type { Match } from '../types';
import TeamBadge from './TeamBadge';
import PredictionBar from './PredictionBar';

const teamHues: Record<string, number> = {
  'Manchester United': 0,
  'Liverpool': 0,
  'Arsenal': 0,
  'Brentford': 0,
  'Southampton': 0,
  'Bournemouth': 0,
  'Manchester City': 220,
  'Chelsea': 220,
  'Brighton': 220,
  'West Ham': 220,
  'Everton': 220,
  'Crystal Palace': 220,
  'Leicester': 220,
  'Ipswich': 220,
  'Tottenham': 280,
  'Newcastle United': 280,
  'Newcastle': 280,
  'Aston Villa': 280,
  'Wolves': 30,
  'Nottingham Forest': 120,
  'Fulham': 120,
};

function getHue(teamName: string): number {
  for (const [key, h] of Object.entries(teamHues)) {
    if (teamName.toLowerCase().includes(key.toLowerCase())) return h;
  }
  return 270;
}

interface MatchCardProps {
  match: Match;
}

export default function MatchCard({ match }: MatchCardProps) {
    const homeTeam = match.home_team_info || match.home_team || {};
    const awayTeam = match.away_team_info || match.away_team || {};

    const homeTeamName = typeof homeTeam === 'string' ? homeTeam : homeTeam.name;
    const awayTeamName = typeof awayTeam === 'string' ? awayTeam : awayTeam.name;
    const homeShort = typeof homeTeam === 'string' ? homeTeam.substring(0, 3).toUpperCase() : (homeTeam.short_name || homeTeam.name.substring(0, 3).toUpperCase());
    const awayShort = typeof awayTeam === 'string' ? awayTeam.substring(0, 3).toUpperCase() : (awayTeam.short_name || awayTeam.name.substring(0, 3).toUpperCase());

    const formatTime = (timeStr?: string) => {
        if (!timeStr || timeStr === 'Unknown' || timeStr === 'TBD') return '';
        return timeStr;
    };

    const prediction = match.prediction;
    const hue = getHue(homeTeamName);

    return (
        <div className="pl-match-card" id={`match-${match.id}`} style={{ '--team-hue': hue } as React.CSSProperties}>
            <div className="pl-match-teams">
                <div className="pl-team pl-team--home">
                    <TeamBadge team={typeof homeTeam === 'string' ? { name: homeTeam, badge_url: null } : homeTeam} size="large" />
                    <span className="pl-team-name">{homeShort}</span>
                </div>

                <div className="pl-match-center">
                    {prediction?.score ? (
                        <>
                            <div className="pl-score">{prediction.score}</div>
                            <div className="pl-time">{formatTime(match.time)}</div>
                        </>
                    ) : (
                        <div className="pl-time pl-time--kickoff">{formatTime(match.time) || 'Kick Off'}</div>
                    )}
                </div>

                <div className="pl-team pl-team--away">
                    <TeamBadge team={typeof awayTeam === 'string' ? { name: awayTeam, badge_url: null } : awayTeam} size="large" />
                    <span className="pl-team-name">{awayShort}</span>
                </div>
            </div>

            <div className="pl-match-full-names">
                <span>{homeTeamName}</span>
                <span>vs</span>
                <span>{awayTeamName}</span>
            </div>

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
