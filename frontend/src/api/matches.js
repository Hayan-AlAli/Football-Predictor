/**
 * API client for Football Predictor backend
 */

const API_BASE = import.meta.env.PROD ? '' : 'http://localhost:8000';

/**
 * Fetch wrapper with error handling
 */
async function fetchAPI(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: options.method || 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error(`API Error for ${endpoint}:`, error);
    throw error;
  }
}

/**
 * Get all Premier League teams with badge URLs
 */
export async function getTeams() {
  const data = await fetchAPI('/api/teams');
  return data.teams;
}

/**
 * Get upcoming matches from FBRef
 */
export async function getUpcomingMatches() {
  const data = await fetchAPI('/api/matches/upcoming');
  return data.matches || [];
}

/**
 * Get predictions for a specific date
 * @param {string} date - Date in YYYY-MM-DD format (optional, defaults to today)
 */
export async function getPredictions(date = null) {
  const endpoint = date 
    ? `/api/matches/predictions?date=${date}`
    : '/api/matches/predictions';
  
  const data = await fetchAPI(endpoint);
  return data.predictions || [];
}

/**
 * Get results comparison for a specific date
 * @param {string} date - Date in YYYY-MM-DD format (optional, defaults to today)
 */
export async function getResults(date = null) {
  const endpoint = date 
    ? `/api/matches/results?date=${date}`
    : '/api/matches/results';
  
  const data = await fetchAPI(endpoint);
  return data.results || [];
}

/**
 * Get list of available prediction dates
 */
export async function getAvailableDates() {
  const data = await fetchAPI('/api/dates/available');
  return data.dates || [];
}

/**
 * Generate prediction for a single match on-demand
 * @param {string} homeTeam - Home team name
 * @param {string} awayTeam - Away team name
 */
export async function predictMatch(homeTeam, awayTeam) {
  const data = await fetchAPI(
    `/api/predict?home_team=${encodeURIComponent(homeTeam)}&away_team=${encodeURIComponent(awayTeam)}`
  );
  return data;
}

/**
 * Get World Cup 2026 predictions and simulation results
 */
export async function getWorldCupPredictions() {
  const data = await fetchAPI('/api/worldcup/predictions');
  return data;
}

/**
 * Generate predictions for all upcoming matches
 */
export async function generatePredictions() {
  return await fetchAPI('/api/matches/predictions/generate', {
    method: 'POST',
  });
}

/**
 * API health check
 */
export async function checkHealth() {
  try {
    const data = await fetchAPI('/api/health');
    return data && data.status === 'online';
  } catch {
    return false;
  }
}

