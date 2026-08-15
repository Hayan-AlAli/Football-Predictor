import type { CalibrationData, ForecastData, H2HData, Match, ResultEntry, TeamProfileData } from '../types';

const API_BASE = import.meta.env.PROD ? '' : 'http://localhost:8000';

interface FetchOptions {
  method?: string;
}

async function fetchAPI<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: options.method || 'GET',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return await response.json() as T;
  } catch (error) {
    console.error(`API Error for ${endpoint}:`, error);
    throw error;
  }
}

interface TeamsResponse {
  teams: { name: string; badge_url: string }[];
}

export async function getTeams(): Promise<{ name: string; badge_url: string }[]> {
  const data = await fetchAPI<TeamsResponse>('/api/teams');
  return data.teams;
}

interface MatchesResponse {
  matches: Match[];
}

export async function getUpcomingMatches(): Promise<Match[]> {
  const data = await fetchAPI<MatchesResponse>('/api/matches/upcoming');
  return data.matches || [];
}

interface PredictionsResponse {
  predictions: Match[];
}

export async function getPredictions(date: string | null = null): Promise<Match[]> {
  const endpoint = date
    ? `/api/matches/predictions?date=${date}`
    : '/api/matches/predictions';

  const data = await fetchAPI<PredictionsResponse>(endpoint);
  return data.predictions || [];
}

interface AllMatchesResponse {
  matches: Match[];
  gameweeks: number[];
}

export async function getAllMatches(): Promise<{ matches: Match[]; gameweeks: number[] }> {
  const data = await fetchAPI<AllMatchesResponse>('/api/matches/all');
  return { matches: data.matches || [], gameweeks: data.gameweeks || [] };
}

interface ResultsResponse {
  results: Match[];
}

export async function getResults(date: string | null = null): Promise<Match[]> {
  const endpoint = date
    ? `/api/matches/results?date=${date}`
    : '/api/matches/results';

  const data = await fetchAPI<ResultsResponse>(endpoint);
  return data.results || [];
}

interface ResultEntriesResponse {
  results: ResultEntry[];
}

/** The evening press's recorded verdicts for a date (status CORRECT / INCORRECT / PENDING). */
export async function getResultEntries(date: string): Promise<ResultEntry[]> {
  const data = await fetchAPI<ResultEntriesResponse>(`/api/matches/results?date=${date}`);
  return data.results || [];
}

interface DatesResponse {
  dates: string[];
}

export async function getAvailableDates(): Promise<string[]> {
  const data = await fetchAPI<DatesResponse>('/api/dates/available');
  return data.dates || [];
}

interface PredictResponse {
  prob_home: number;
  prob_draw: number;
  prob_away: number;
}

export async function predictMatch(homeTeam: string, awayTeam: string): Promise<PredictResponse> {
  return await fetchAPI<PredictResponse>(
    `/api/predict?home_team=${encodeURIComponent(homeTeam)}&away_team=${encodeURIComponent(awayTeam)}`
  );
}

export async function generatePredictions(): Promise<PredictionsResponse> {
  return await fetchAPI<PredictionsResponse>('/api/matches/predictions/generate', {
    method: 'POST',
  });
}

interface HealthResponse {
  status: string;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const data = await fetchAPI<HealthResponse>('/api/health');
    return data && data.status === 'online';
  } catch {
    try {
      const data = await fetchAPI<HealthResponse>('/');
      return data && data.status === 'online';
    } catch {
      return false;
    }
  }
}

export async function getForecast(): Promise<ForecastData> {
  return await fetchAPI<ForecastData>('/api/season/forecast');
}

export async function getCalibration(): Promise<CalibrationData> {
  return await fetchAPI<CalibrationData>('/api/calibration');
}

export async function getTeamProfile(name: string): Promise<TeamProfileData> {
  return await fetchAPI<TeamProfileData>(`/api/teams/${encodeURIComponent(name)}`);
}

export async function getHeadToHead(team: string, vs: string): Promise<H2HData> {
  return await fetchAPI<H2HData>(
    `/api/teams/${encodeURIComponent(team)}/h2h?vs=${encodeURIComponent(vs)}`
  );
}
