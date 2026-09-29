import type { CalibrationData, ForecastData, H2HData, Match, Team, TeamProfileData } from '../types';

const API_BASE = import.meta.env.PROD ? '' : 'http://localhost:8000';

async function fetchAPI<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    throw new Error(`API Error for ${endpoint}: ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export interface SeasonMatches {
  season: number;
  matches: Match[];
  gameweeks: number[];
}

/** Every match of a season - fixtures, predictions, results and verdicts in one call. */
export async function getMatches(season?: number): Promise<SeasonMatches> {
  const data = await fetchAPI<Partial<SeasonMatches>>(season ? `/api/matches?season=${season}` : '/api/matches');
  return { season: data.season ?? 0, matches: data.matches ?? [], gameweeks: data.gameweeks ?? [] };
}

export async function getTeams(): Promise<Team[]> {
  const data = await fetchAPI<{ teams?: Team[] }>('/api/teams');
  return data.teams ?? [];
}

export async function getForecast(): Promise<ForecastData> {
  return fetchAPI<ForecastData>('/api/forecast');
}

export async function getCalibration(): Promise<CalibrationData> {
  return fetchAPI<CalibrationData>('/api/calibration');
}

/** team: slug or name - the API accepts either. */
export async function getTeamProfile(team: string): Promise<TeamProfileData> {
  return fetchAPI<TeamProfileData>(`/api/teams/${encodeURIComponent(team)}`);
}

export async function getHeadToHead(team: string, vs: string): Promise<H2HData> {
  return fetchAPI<H2HData>(`/api/teams/${encodeURIComponent(team)}/h2h?vs=${encodeURIComponent(vs)}`);
}
