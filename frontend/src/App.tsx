import { useState, useEffect } from 'react';
import './App.css';
import Header from './components/Header';
import MatchList from './components/MatchList';
import Loader from './components/Loader';
import { getAllMatches, checkHealth } from './api/matches';

function App() {
  const [matches, setMatches] = useState<any[]>([]);
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

  const currentIndex = gameweeks.indexOf(selectedGameweek!);
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < gameweeks.length - 1;

  const goPrev = () => {
    if (hasPrev) setSelectedGameweek(gameweeks[currentIndex - 1]);
  };
  const goNext = () => {
    if (hasNext) setSelectedGameweek(gameweeks[currentIndex + 1]);
  };

  const filteredMatches = selectedGameweek
    ? matches.filter(m => m.gameweek === selectedGameweek)
    : [];

  return (
    <div className="app">
      <Header />

      <main className="main">
        <div className="container">
          <div className="pl-hero">
            <h1 className="pl-title">Premier League</h1>
            <p className="pl-subtitle">Match Predictions 2026/27</p>
          </div>

          {gameweeks.length > 0 && (
            <div className="pl-gw-nav">
              <button
                className="pl-gw-arrow"
                onClick={goPrev}
                disabled={!hasPrev}
                aria-label="Previous gameweek"
              >
                ←
              </button>
              <div className="pl-gw-label">
                <span className="pl-gw-number">Matchweek {selectedGameweek}</span>
                <span className="pl-gw-count">{filteredMatches.length} matches</span>
              </div>
              <button
                className="pl-gw-arrow"
                onClick={goNext}
                disabled={!hasNext}
                aria-label="Next gameweek"
              >
                →
              </button>
            </div>
          )}

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
            <MatchList matches={filteredMatches} />
          )}
        </div>
      </main>

      <footer className="footer">
        <div className="container">
          <p className="footer-text">
            Football Predictor • Premier League 2026/27
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
