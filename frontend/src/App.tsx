import { useState, useEffect } from 'react';
import './App.css';
import Header from './components/Header';
import MatchList from './components/MatchList';
import Loader from './components/Loader';
import { getPredictions, getAvailableDates, getUpcomingMatches, checkHealth, generatePredictions } from './api/matches';
import type { Match } from './types';

function App() {
  const [predictions, setPredictions] = useState<Match[]>([]);
  const [upcomingMatches, setUpcomingMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingUpcoming, setLoadingUpcoming] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [availableDates, setAvailableDates] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState('predictions');


  useEffect(() => {
    async function initializeApp() {
      setLoading(true);
      setError(null);

      try {
        const isOnline = await checkHealth();

        if (!isOnline) {
          setError('API is offline. Cannot fetch predictions.');
          setPredictions([]);
          setLoading(false);
          return;
        }

        const dates = await getAvailableDates();
        setAvailableDates(dates);

        const targetDate = dates.length > 0 ? dates[0] : null;
        setSelectedDate(targetDate);

        if (targetDate) {
          const preds = await getPredictions(targetDate);
          setPredictions(preds);
        } else {
          setPredictions([]);
        }

        loadUpcomingMatches();
      } catch (err) {
        console.error('Error loading data:', err);
        setError('Failed to load predictions. Please try again.');
        setPredictions([]);
      } finally {
        setLoading(false);
      }
    }

    initializeApp();
  }, []);

  const loadUpcomingMatches = async () => {
    setLoadingUpcoming(true);
    try {
      const matches = await getUpcomingMatches();
      setUpcomingMatches(matches);
    } catch (err) {
      console.error('Error loading upcoming matches:', err);
    } finally {
      setLoadingUpcoming(false);
    }
  };

  const handleGeneratePredictions = async () => {
    setGenerating(true);
    setError(null);
    try {
      const result = await generatePredictions();
      setPredictions(result.predictions || []);
      if (result.predictions && result.predictions.length > 0) {
        const today = new Date().toISOString().split('T')[0];
        setAvailableDates(prev => {
          if (!prev.includes(today)) return [today, ...prev];
          return prev;
        });
        setSelectedDate(today);
      }
    } catch (err) {
      console.error('Error generating predictions:', err);
      setError('Failed to generate predictions.');
    } finally {
      setGenerating(false);
    }
  };

  const handleDateChange = async (date: string) => {
    setSelectedDate(date);
    setLoading(true);

    try {
      const preds = await getPredictions(date);
      setPredictions(preds);
      setError(null);
    } catch (err) {
      console.error('Error loading predictions:', err);
      setError('Failed to load predictions for this date.');
    } finally {
      setLoading(false);
    }
  };

  const totalMatches = activeTab === 'predictions' ? predictions.length : upcomingMatches.length;

  return (
    <div className="app">
      <Header matchCount={totalMatches} />

      <main className="main">
        <div className="container">
          <div className="tabs">
                <button
                  className={`tab ${activeTab === 'predictions' ? 'tab--active' : ''}`}
                  onClick={() => setActiveTab('predictions')}
                >
                  🤖 Predictions
                </button>
                <button
                  className={`tab ${activeTab === 'upcoming' ? 'tab--active' : ''}`}
                  onClick={() => setActiveTab('upcoming')}
                >
                  📅 Upcoming Matches
                </button>
              </div>

              {activeTab === 'predictions' && (
                <>
                  <div className="section-header">
                    <div className="section-title">
                      <h2>Match Predictions</h2>
                      {selectedDate && (
                        <span className="section-subtitle">
                          {formatDateDisplay(selectedDate)}
                        </span>
                      )}
                    </div>

                    <div className="section-actions">
                      {availableDates.length > 1 && (
                        <select
                          className="btn btn-ghost"
                          value={selectedDate || ''}
                          onChange={(e) => handleDateChange(e.target.value)}
                        >
                          {availableDates.map(date => (
                            <option key={date} value={date}>
                              {formatDateDisplay(date)}
                            </option>
                          ))}
                        </select>
                      )}
                      <button
                        className="btn btn-primary"
                        onClick={handleGeneratePredictions}
                        disabled={generating}
                      >
                        {generating ? 'Generating...' : 'Generate Predictions'}
                      </button>
                    </div>
                  </div>

                  {error && (
                    <div className="error-state fade-in">
                      <span className="error-icon">⚠️</span>
                      <span className="error-message">{error}</span>
                    </div>
                  )}

                  {loading ? (
                    <Loader message="Loading predictions..." />
                  ) : predictions.length === 0 ? (
                    <div className="empty-state glass-card">
                      <div className="empty-icon">📅</div>
                      <h3 className="empty-title">No Predictions Yet</h3>
                      <p className="empty-description">
                        Click "Generate Predictions" to get AI-powered predictions for upcoming matches.
                      </p>
                    </div>
                  ) : (
                    <MatchList
                      matches={predictions}
                      groupByDate={false}
                    />
                  )}
                </>
              )}

              {activeTab === 'upcoming' && (
                <>
                  <div className="section-header">
                    <div className="section-title">
                      <h2>Upcoming Fixtures</h2>
                      <span className="section-subtitle">
                        Future Premier League matches
                      </span>
                    </div>
                    <button
                      className="btn btn-ghost"
                      onClick={loadUpcomingMatches}
                      disabled={loadingUpcoming}
                    >
                      🔄 Refresh
                    </button>
                  </div>

                  {loadingUpcoming ? (
                    <Loader message="Loading upcoming matches..." />
                  ) : (
                    <MatchList
                      matches={upcomingMatches}
                      groupByDate={true}
                    />
                  )}
                </>
              )}
          </div>
      </main>

      <footer className="footer">
        <div className="container">
          <p className="footer-text">
            Football Predictor • AI-Powered Match Predictions • Premier League 2025/26
          </p>
        </div>
      </footer>
    </div>
  );
}

function formatDateDisplay(dateStr: string) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });
}

export default App;
