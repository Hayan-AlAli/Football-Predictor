export interface Team {
  name: string;
  short_name?: string;
  badge_url?: string | null;
}

export interface Prediction {
  prob_home: number;
  prob_draw: number;
  prob_away: number;
  score?: string;
  winner?: string;
  home_goals?: number;
  away_goals?: number;
  home_elo?: number;
  away_elo?: number;
}

export interface Match {
  id: string;
  date: string;
  time?: string;
  gameweek?: number;
  home_team: string | Team;
  away_team: string | Team;
  home_team_info?: Team;
  away_team_info?: Team;
  prediction?: Prediction;
  status?: string;
  score?: string;
}

/** One entry of a recorded results file (written by the evening job). */
export interface ResultEntry {
  match: Match;
  actual?: {
    home_goals: number;
    away_goals: number;
    score?: string;
  } | null;
  status: 'CORRECT' | 'INCORRECT' | 'PENDING';
}
