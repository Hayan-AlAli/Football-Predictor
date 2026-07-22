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


