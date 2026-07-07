import { useState, useEffect } from 'react';
import './App.css';
import Header from './components/Header';
import MatchList from './components/MatchList';
import Loader from './components/Loader';
import WorldCupView from './components/WorldCupView';
import { getPredictions, getAvailableDates, getUpcomingMatches, checkHealth, getWorldCupPredictions, generatePredictions } from './api/matches';


function App() {
  const [predictions, setPredictions] = useState([]);
  const [upcomingMatches, setUpcomingMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingUpcoming, setLoadingUpcoming] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null);
  const [availableDates, setAvailableDates] = useState([]);
  const [activeTab, setActiveTab] = useState('predictions');
  const [activeTournament, setActiveTournament] = useState('pl');
  const [wcData, setWcData] = useState(null);
  const [loadingWc, setLoadingWc] = useState(false);


  // Check API health and load initial data
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

  // Load upcoming matches
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

  // Generate predictions for upcoming matches
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

  // Load predictions when date changes
  const handleDateChange = async (date) => {
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

  // Load World Cup predictions
  const loadWorldCupData = async () => {
    setLoadingWc(true);
    try {
      const data = await getWorldCupPredictions();
      setWcData(data);
      setError(null);
    } catch (err) {
      console.error('Error loading World Cup predictions:', err);
      setError('Failed to load World Cup predictions. Showing demo data.');
      setWcData(getMockWorldCupData());
    } finally {
      setLoadingWc(false);
    }
  };

  const handleTournamentChange = (tournament) => {
    setActiveTournament(tournament);
    if (tournament === 'wc' && !wcData) {
      loadWorldCupData();
    }
  };

  const totalMatches = activeTournament === 'wc' 
    ? 104 
    : (activeTab === 'predictions' ? predictions.length : upcomingMatches.length);

  return (
    <div className="app">
      <Header matchCount={totalMatches} />


      <main className="main">
        <div className="container">
          {/* Tournament Selector */}
          <div className="tournament-selector glass-card">
            <button
              className={`tournament-btn ${activeTournament === 'pl' ? 'tournament-btn--active' : ''}`}
              onClick={() => handleTournamentChange('pl')}
            >
              🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League
            </button>
            <button
              className={`tournament-btn ${activeTournament === 'wc' ? 'tournament-btn--active' : ''}`}
              onClick={() => handleTournamentChange('wc')}
            >
              🏆 World Cup 2026
            </button>
          </div>

          {activeTournament === 'wc' ? (
            loadingWc ? (
              <Loader message="Simulating World Cup 2026..." />
            ) : error && !wcData ? (
              <div className="error-state fade-in">
                <span className="error-icon">⚠️</span>
                <span className="error-message">{error}</span>
              </div>
            ) : (
              <WorldCupView data={wcData} />
            )
          ) : (
            <>
              {/* Tab Navigation */}
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

              {/* Predictions Tab */}
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

              {/* Upcoming Matches Tab */}
              {activeTab === 'upcoming' && (
                <>
                  {/* Section Header */}
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

                  {/* Content */}
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

/**
 * Format date for display
 */
function formatDateDisplay(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });
}

/**
 * Mock World Cup data when API is offline
 */
function getMockWorldCupData() {
  return {
    "generated_at": "2026-06-19 04:00 (DEMO)",
    "summary": {
      "champion": "Argentina",
      "runner_up": "Germany",
      "third_place": "Spain"
    },
    "favorites": [],
    "group_stage": {
      "matches": [],
      "standings": {}
    },
    "knockout_stage": {
      "R32": [],
      "R16": [],
      "QF": [],
      "SF": [],
      "3rd": {},
      "Final": {}
    }
  };
}

export default App;

