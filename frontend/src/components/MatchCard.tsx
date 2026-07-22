import type { Match } from '../types';
import TeamBadge from './TeamBadge';
import PredictionBar from './PredictionBar';
import { GlowCard } from './ui/spotlight-card';

const teamGlowMap: Record<string, 'blue' | 'purple' | 'green' | 'red' | 'orange'> = {
  'Manchester United': 'red',
  'Manchester City': 'blue',
  'Liverpool': 'red',
  'Arsenal': 'red',
  'Chelsea': 'blue',
  'Tottenham': 'purple',
  'Newcastle United': 'purple',
  'Newcastle': 'purple',
  'Aston Villa': 'purple',
  'Brighton': 'blue',
  'West Ham': 'blue',
  'Everton': 'blue',
  'Wolves': 'orange',
  'Crystal Palace': 'blue',
  'Nottingham Forest': 'green',
  'Fulham': 'green',
  'Brentford': 'red',
  'Leicester': 'blue',
  'Southampton': 'red',
  'Bournemouth': 'red',
  'Ipswich': 'blue',
};

function getGlowColor(teamName: string): 'blue' | 'purple' | 'green' | 'red' | 'orange' {
  for (const [key, color] of Object.entries(teamGlowMap)) {
    if (teamName.toLowerCase().includes(key.toLowerCase())) return color;
  }
  return 'purple';
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
    const glowColor = getGlowColor(homeTeamName);

    return (
        <GlowCard glowColor={glowColor} customSize className="!aspect-auto !grid-rows-none">
        <div className="pl-match-card" id={`match-${match.id}`}>
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
        </GlowCard>
    );
}
