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
  index?: number;
}

export default function MatchCard({ match, index = 0 }: MatchCardProps) {
    const homeTeam = match.home_team_info || match.home_team || {};
    const awayTeam = match.away_team_info || match.away_team || {};

    const homeTeamName = typeof homeTeam === 'string' ? homeTeam : homeTeam.name;
    const awayTeamName = typeof awayTeam === 'string' ? awayTeam : awayTeam.name;

    const formatDate = (dateStr?: string) => {
        if (!dateStr) return 'TBD';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-GB', {
            weekday: 'short',
            day: 'numeric',
            month: 'short'
        });
    };

    const formatTime = (timeStr?: string) => {
        if (!timeStr || timeStr === 'Unknown' || timeStr === 'TBD') return 'TBD';
        return timeStr;
    };

    const prediction = match.prediction;
    const glowColor = getGlowColor(homeTeamName);

    return (
        <GlowCard
          glowColor={glowColor}
          customSize
          className="!aspect-auto !grid-rows-none"
        >
        <div
            className={`glass-card match-card fade-in stagger-${(index % 5) + 1} w-full h-full`}
            id={`match-${match.id}`}
        >
            <div className="match-header">
                <div className="match-meta">
                    <span className="match-date">{formatDate(match.date)}</span>
                    <span className="match-time">{formatTime(match.time)}</span>
                </div>
                {match.gameweek && (
                    <span className="match-gameweek">GW{match.gameweek}</span>
                )}
            </div>

            <div className="teams-container">
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

                <div className="vs-badge">VS</div>

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
