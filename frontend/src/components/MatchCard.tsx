import type { Match } from '../types';
import TeamBadge from './TeamBadge';
import PredictionBar from './PredictionBar';
import { GlowCard } from './ui/spotlight-card';

const teamColors: Record<string, string> = {
  'Manchester United': '#DA291C',
  'Manchester City': '#6CABDD',
  'Liverpool': '#C8102E',
  'Arsenal': '#EF0107',
  'Chelsea': '#034694',
  'Tottenham': '#132257',
  'Newcastle United': '#241F20',
  'Newcastle': '#241F20',
  'Aston Villa': '#670E36',
  'Brighton': '#0057B8',
  'West Ham': '#7A263A',
  'Everton': '#003399',
  'Wolves': '#FDB913',
  'Crystal Palace': '#1B458F',
  'Nottingham Forest': '#DD0000',
  'Fulham': '#333333',
  'Brentford': '#D30000',
  'Leicester': '#003090',
  'Southampton': '#D71920',
  'Bournemouth': '#DA291C',
  'Ipswich': '#003399',
  'Coventry City': '#339ACC',
  'Hull City': '#FF6600',
  'Hull': '#FF6600',
  'Leeds United': '#1D4491',
  'Leeds': '#1D4491',
  'Sunderland': '#EB172B',
};

function getTeamColor(teamName: string): string {
  for (const [key, color] of Object.entries(teamColors)) {
    if (teamName.toLowerCase().includes(key.toLowerCase())) return color;
  }
  return '#7C3AED';
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
    const homeColor = getTeamColor(homeTeamName);
    const awayColor = getTeamColor(awayTeamName);

    return (
        <GlowCard leftColor={homeColor} rightColor={awayColor} customSize className="!aspect-auto !grid-rows-none">
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