/** A club as the API describes it (backend/teams.py + data/teams.json). */
export interface Team {
  name: string;
  slug?: string;
  full_name?: string;
  short_name?: string;
  badge_url?: string | null;
  /** Second source tried when badge_url fails to load. */
  badge_fallback_url?: string | null;
  /** Club colour as #RRGGBB. */
  color?: string | null;
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
  features?: PredictionFeatures | null;
  model_version?: string | null;
  created_at?: string | null;
}

export type MatchStatus = 'scheduled' | 'in_progress' | 'finished' | 'postponed';
export type Verdict = 'CORRECT' | 'INCORRECT' | 'PENDING';

export interface ActualResult {
  home_goals: number;
  away_goals: number;
  score?: string;
  winner?: string;
}

/** One fixture of a season: schedule, the model's call, and the result. */
export interface Match {
  id: string;
  season?: number;
  date: string;
  time?: string | null;
  /** ISO kickoff in UTC; null while the slot is unconfirmed. */
  kickoff?: string | null;
  gameweek?: number | null;
  home_team: string | Team;
  away_team: string | Team;
  home_team_info?: Team;
  away_team_info?: Team;
  status?: MatchStatus;
  home_goals?: number | null;
  away_goals?: number | null;
  prediction?: Prediction | null;
  actual?: ActualResult | null;
  /** Judgement of the prediction; null when the match was never predicted. */
  verdict?: Verdict | null;
}

/** A predicted match as the records print it. */
export interface ResultEntry {
  match: Match;
  actual?: ActualResult | null;
  status: Verdict;
}

export interface PredictionFeatures {
  home_elo: number;
  away_elo: number;
  elo_gap: number;
  home_rolling_goals: number;
  away_rolling_goals: number;
  home_rolling_xg: number;
  away_rolling_xg: number;
  league_avg_goals: number;
  league_avg_xg: number;
}

export interface StandingsRow {
  team: string;
  team_info?: Team;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  gf: number;
  ga: number;
  gd: number;
  points: number;
}

export interface ProjectedRow {
  team: string;
  team_info?: Team;
  median_position: number;
  points_p10: number;
  points_p50: number;
  points_p90: number;
  title_odds: number;
  top4_odds: number;
  top6_odds: number;
  relegation_odds: number;
  position_odds: Record<string, number>;
}

export interface ForecastData {
  generated: string;
  season_year: number;
  n_sims: number;
  season_complete: boolean;
  stale?: string;
  standings: StandingsRow[];
  projected: ProjectedRow[];
  fixtures_remaining: number;
}

export interface CalibrationBin {
  label: string;
  count: number;
  predicted: number;
  actual: number;
}

export interface GameweekAccuracy {
  gameweek: number;
  decided: number;
  correct: number;
  accuracy: number | null;
}

export interface CalibrationData {
  entries: number;
  brier: number | null;
  accuracy: number | null;
  bins: CalibrationBin[];
  rolling: GameweekAccuracy[];
}

export interface SeasonRow {
  season_year: number;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  gf: number;
  ga: number;
  points: number;
}

export interface FormEntry {
  date: string;
  result: 'W' | 'D' | 'L';
  home_team: string;
  away_team: string;
  home_goals: number;
  away_goals: number;
}

export interface EloPoint {
  date: string;
  elo: number;
}

export interface TeamProfileData {
  team: string;
  team_info: Team;
  seasons: SeasonRow[];
  form: FormEntry[];
  elo_history: EloPoint[];
  upcoming: Match[];
}

export interface Meeting {
  date: string;
  home_team: string;
  away_team: string;
  home_goals: number;
  away_goals: number;
  winner: string;
}

export interface H2HSummary {
  meetings: number;
  team_a_wins: number;
  draws: number;
  team_b_wins: number;
  team_a_for: number;
  team_a_against: number;
}

export interface H2HData {
  team_a: string;
  team_b: string;
  team_a_info: Team;
  team_b_info: Team;
  summary: H2HSummary;
  meetings: Meeting[];
}
