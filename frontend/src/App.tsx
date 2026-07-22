import { useState, useEffect } from 'react';
import './App.css';
import Header from './components/Header';
import MatchList from './components/MatchList';
import Loader from './components/Loader';
import { getAllMatches, checkHealth } from './api/matches';
import type { Match } from './types';

function App() {
  const [matches, setMatches] = useState<Match[]>([]);
  const [gameweeks, setGameweeks] = useState<number[]>([]);
  const [selectedGameweek, setSelectedGameweek] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const isOnline = await checkHealth();
        if (!isOnline) {
          setError('API is offline. Cannot fetch predictions.');
          setLoading(false);
          return;
        }
        const data = await getAllMatches();
        setMatches(data.matches);
        setGameweeks(data.gameweeks);
        if (data.gameweeks.length > 0) {
          setSelectedGameweek(data.gameweeks[0]);
        }
      } catch (err) {
        console.error('Error loading data:', err);
        setError('Failed to load predictions.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filteredMatches = selectedGameweek
    ? matches.filter(m => m.gameweek === selectedGameweek)
    : [];

  return (
    <div className="app">
      <Header matchCount={filteredMatches.length} />

      <main className="main">
        <div className="container">
          <div className="section-header">
            <div className="section-title">
              <h2>Match Predictions</h2>
              {selectedGameweek && (
                <span className="section-subtitle">
                  Gameweek {selectedGameweek}
                </span>
              )}
            </div>

            {gameweeks.length > 1 && (
              <div className="gameweek-nav">
                {gameweeks.map(gw => (
                  <button
                    key={gw}
                    className={`gameweek-btn ${selectedGameweek === gw ? 'gameweek-btn--active' : ''}`}
                    onClick={() => setSelectedGameweek(gw)}
                  >
                    GW{gw}
                  </button>
                ))}
              </div>
            )}
          </div>

          {error && (
            <div className="error-state fade-in">
              <span className="error-message">{error}</span>
            </div>
          )}

          {loading ? (
            <Loader message="Loading predictions..." />
          ) : filteredMatches.length === 0 ? (
            <div className="empty-state glass-card">
              <h3 className="empty-title">No Predictions Yet</h3>
              <p className="empty-description">
                No matches found for this gameweek.
              </p>
            </div>
          ) : (
            <MatchList matches={filteredMatches} groupByDate={true} />
          )}
        </div>
      </main>

      <footer className="footer">
        <div className="container">
          <p className="footer-text">
            Football Predictor • Match Predictions • Premier League 2025/26
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
