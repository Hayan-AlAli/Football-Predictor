import { useState } from 'react';
import PredictionBar from './PredictionBar';
import TeamBadge from './TeamBadge';

// Map team names to flag emojis for authentic premium look
const FLAG_MAP = {
  "Argentina": "🇦🇷", "Spain": "🇪🇸", "France": "🇫🇷", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Portugal": "🇵🇹",
  "Brazil": "🇧🇷", "Morocco": "🇲🇦", "Netherlands": "🇳🇱", "Belgium": "🇧🇪", "Germany": "🇩🇪",
  "Croatia": "🇭🇷", "Colombia": "🇨🇴", "Mexico": "🇲🇽", "Senegal": "🇸🇳", "Uruguay": "🇺🇾",
  "United States": "🇺🇸", "Japan": "🇯🇵", "Switzerland": "🇨🇭", "Iran": "🇮🇷", "Ecuador": "🇪🇨",
  "Turkiye": "🇹🇷", "Australia": "🇦🇺", "South Korea": "🇰🇷", "Egypt": "🇪🇬", "Algeria": "🇩🇿",
  "Norway": "🇳🇴", "Austria": "🇦🇹", "Paraguay": "🇵🇾", "Ivory Coast": "🇨🇮", "Sweden": "🇸🇪",
  "Czechia": "🇨🇿", "Tunisia": "🇹🇳", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Uzbekistan": "🇺🇿", "Qatar": "🇶🇦",
  "Saudi Arabia": "🇸🇦", "Ghana": "🇬🇭", "Bosnia and Herzegovina": "🇧🇦", "Iraq": "🇮🇶",
  "Jordan": "🇯🇴", "Panama": "🇵🇦", "South Africa": "🇿🇦", "DR Congo": "🇨🇩", "Cape Verde": "🇨🇻",
  "Bolivia": "🇧🇴", "Curacao": "🇨🇼", "Haiti": "🇭🇹", "New Zealand": "🇳🇿", "Canada": "🇨🇦"
};

const getFlag = (team) => FLAG_MAP[team] || "🏳️";

export default function WorldCupView({ data }) {
  const [activeSubTab, setActiveSubTab] = useState('overview'); // 'overview', 'groups', 'knockout', 'rankings'
  const [selectedGroup, setSelectedGroup] = useState('A');

  if (!data) return null;

  const { favorites, group_stage, knockout_stage, summary, generated_at } = data;
  const groups = Object.keys(group_stage?.standings || {}).sort();

  return (
    <div className="world-cup-view fade-in">
      {/* Sub Tabs */}
      <div className="sub-tabs glass-card">
        <button
          className={`sub-tab ${activeSubTab === 'overview' ? 'sub-tab--active' : ''}`}
          onClick={() => setActiveSubTab('overview')}
        >
          🏆 Overview
        </button>
        <button
          className={`sub-tab ${activeSubTab === 'groups' ? 'sub-tab--active' : ''}`}
          onClick={() => setActiveSubTab('groups')}
        >
          📋 Group Stage
        </button>
        <button
          className={`sub-tab ${activeSubTab === 'knockout' ? 'sub-tab--active' : ''}`}
          onClick={() => setActiveSubTab('knockout')}
        >
          🏟️ Knockout Stage
        </button>
        <button
          className={`sub-tab ${activeSubTab === 'rankings' ? 'sub-tab--active' : ''}`}
          onClick={() => setActiveSubTab('rankings')}
        >
          📊 Power Rankings
        </button>
      </div>

      {/* OVERVIEW SUB-TAB */}
      {activeSubTab === 'overview' && (
        <div className="wc-overview fade-in">
          {/* Podium */}
          <div className="podium-container glass-card">
            <h3 className="podium-title">🏆 Predicted World Cup Podium</h3>
            <div className="podium">
              {/* Runner Up */}
              <div className="podium-step step-2">
                <div className="podium-flag">{getFlag(summary?.runner_up)}</div>
                <div className="podium-team">{summary?.runner_up}</div>
                <div className="podium-rank rank-2">2nd</div>
              </div>
              {/* Winner */}
              <div className="podium-step step-1">
                <div className="podium-crown">👑</div>
                <div className="podium-flag">{getFlag(summary?.champion)}</div>
                <div className="podium-team">{summary?.champion}</div>
                <div className="podium-rank rank-1">1st</div>
              </div>
              {/* Third Place */}
              <div className="podium-step step-3">
                <div className="podium-flag">{getFlag(summary?.third_place)}</div>
                <div className="podium-team">{summary?.third_place}</div>
                <div className="podium-rank rank-3">3rd</div>
              </div>
            </div>
          </div>

          {/* Favorites Snippet */}
          <div className="overview-grid">
            <div className="overview-box glass-card">
              <h4>🔥 Top Title Contenders</h4>
              <div className="contenders-list">
                {favorites?.slice(0, 5).map((fav, i) => (
                  <div key={fav.team} className="contender-item">
                    <span className="contender-rank">#{i + 1}</span>
                    <span className="contender-flag">{getFlag(fav.team)}</span>
                    <span className="contender-name">{fav.team}</span>
                    <span className="contender-rating">{fav.rating}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="overview-box glass-card stats-summary-box">
              <h4>📊 Simulation Insights</h4>
              <div className="insight-stats">
                <div className="insight-item">
                  <div className="insight-val">{favorites?.length}</div>
                  <div className="insight-lbl">Total Teams</div>
                </div>
                <div className="insight-item">
                  <div className="insight-val">104</div>
                  <div className="insight-lbl">Total Matches</div>
                </div>
                <div className="insight-item">
                  <div className="insight-val">
                    {group_stage?.matches?.filter(m => m.status === 'COMPLETED').length}
                  </div>
                  <div className="insight-lbl">Completed Matches</div>
                </div>
              </div>
              <div className="insight-meta">
                <p><strong>Prediction Model:</strong> Composite (FIFA ELO + Squad Strength + Manager + Form + Pedigree + Poisson model)</p>
                <p className="generated-date">Generated: {generated_at}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* GROUP STAGE SUB-TAB */}
      {activeSubTab === 'groups' && (
        <div className="wc-groups fade-in">
          {/* Group Letters Selector */}
          <div className="group-selector">
            {groups.map(g => (
              <button
                key={g}
                className={`group-btn ${selectedGroup === g ? 'group-btn--active' : ''}`}
                onClick={() => setSelectedGroup(g)}
              >
                Group {g}
              </button>
            ))}
          </div>

          {/* Group Content */}
          <div className="group-detail-grid">
            {/* Standings Table */}
            <div className="group-standings glass-card">
              <h3 className="section-title">📊 Group {selectedGroup} Standings</h3>
              <div className="table-responsive">
                <table className="standings-table">
                  <thead>
                    <tr>
                      <th style={{ width: '40px' }}>Pos</th>
                      <th>Team</th>
                      <th>P</th>
                      <th>W</th>
                      <th>D</th>
                      <th>L</th>
                      <th>GD</th>
                      <th>Pts</th>
                    </tr>
                  </thead>
                  <tbody>
                    {group_stage?.standings[selectedGroup]?.map((row, idx) => {
                      const qualified = idx < 2;
                      return (
                        <tr key={row.team} className={qualified ? 'row-qualified' : ''}>
                          <td>{idx + 1}</td>
                          <td className="table-team-cell">
                            <span className="table-flag">{getFlag(row.team)}</span>
                            <span className="table-team-name">{row.team}</span>
                            {qualified && <span className="qualify-dot" title="Qualified"></span>}
                          </td>
                          <td>{row.played}</td>
                          <td>{row.w}</td>
                          <td>{row.d}</td>
                          <td>{row.l}</td>
                          <td className={row.gd > 0 ? 'text-green' : row.gd < 0 ? 'text-red' : ''}>
                            {row.gd > 0 ? `+${row.gd}` : row.gd}
                          </td>
                          <td className="text-pts">{row.pts}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Group Matches */}
            <div className="group-matches-container">
              <h3 className="section-title">⚽ Group {selectedGroup} Matches</h3>
              <div className="group-matches-list">
                {group_stage?.matches
                  ?.filter(m => m.group === selectedGroup)
                  .map((match, i) => {
                    const isCompleted = match.status === 'COMPLETED';
                    const score = match.score || 'vs';

                    return (
                      <div key={i} className="wc-match-card glass-card">
                        <div className="wc-match-header">
                          <span className="wc-match-date">📅 {match.date}</span>
                          <span className={`wc-match-status ${isCompleted ? 'status-comp' : 'status-pred'}`}>
                            {isCompleted ? 'RESULT' : 'PREDICTED'}
                          </span>
                        </div>
                        <div className="wc-match-body">
                          <div className="wc-match-team team-home">
                            <span className="wc-flag">{getFlag(match.home)}</span>
                            <span className="wc-name">{match.home}</span>
                          </div>
                          <div className="wc-match-score">{score}</div>
                          <div className="wc-match-team team-away">
                            <span className="wc-flag">{getFlag(match.away)}</span>
                            <span className="wc-name">{match.away}</span>
                          </div>
                        </div>
                        {!isCompleted && match.prob_home && (
                          <div className="wc-match-probs">
                            <div className="wc-prob-item">
                              <span className="wc-prob-lbl">{match.home}</span>
                              <span className="wc-prob-val">{match.prob_home}</span>
                            </div>
                            <div className="wc-prob-item">
                              <span className="wc-prob-lbl">Draw</span>
                              <span className="wc-prob-val">{match.prob_draw}</span>
                            </div>
                            <div className="wc-prob-item">
                              <span className="wc-prob-lbl">{match.away}</span>
                              <span className="wc-prob-val">{match.prob_away}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* KNOCKOUT STAGE SUB-TAB */}
      {activeSubTab === 'knockout' && (
        <div className="wc-knockout fade-in">
          {/* R32, R16, QF, SF, Finals Grid columns */}
          <div className="knockout-rounds">
            {/* Round of 32 */}
            <div className="knockout-round">
              <h4 className="round-title">🏟️ Round of 32</h4>
              <div className="round-matches">
                {knockout_stage?.R32?.map((match, i) => (
                  <KnockoutMatchCard key={i} match={match} />
                ))}
              </div>
            </div>

            {/* Round of 16 */}
            <div className="knockout-round">
              <h4 className="round-title">🏟️ Round of 16</h4>
              <div className="round-matches">
                {knockout_stage?.R16?.map((match, i) => (
                  <KnockoutMatchCard key={i} match={match} />
                ))}
              </div>
            </div>

            {/* Quarter Finals */}
            <div className="knockout-round">
              <h4 className="round-title">🏆 Quarter Finals</h4>
              <div className="round-matches">
                {knockout_stage?.QF?.map((match, i) => (
                  <KnockoutMatchCard key={i} match={match} />
                ))}
              </div>
            </div>

            {/* Semi Finals */}
            <div className="knockout-round">
              <h4 className="round-title">⭐ Semi Finals</h4>
              <div className="round-matches">
                {knockout_stage?.SF?.map((match, i) => (
                  <KnockoutMatchCard key={i} match={match} />
                ))}
              </div>
            </div>

            {/* Finals */}
            <div className="knockout-round round-finals">
              <h4 className="round-title">🏆 Finals</h4>
              <div className="round-matches">
                {/* 3rd Place */}
                {knockout_stage?.["3rd"] && (
                  <div className="finals-container">
                    <span className="finals-label">🥉 Third Place Playoff</span>
                    <KnockoutMatchCard match={knockout_stage["3rd"]} isFinals={true} />
                  </div>
                )}
                {/* Final */}
                {knockout_stage?.Final && (
                  <div className="finals-container">
                    <span className="finals-label">👑 World Cup Final</span>
                    <KnockoutMatchCard match={knockout_stage.Final} isFinals={true} />
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* POWER RANKINGS SUB-TAB */}
      {activeSubTab === 'rankings' && (
        <div className="wc-rankings fade-in">
          <div className="rankings-container glass-card">
            <h3 className="section-title">📊 Pre-Tournament Power Rankings</h3>
            <div className="table-responsive">
              <table className="rankings-table">
                <thead>
                  <tr>
                    <th style={{ width: '60px' }}>Rank</th>
                    <th>Team</th>
                    <th>Rating</th>
                    <th>FIFA Rank</th>
                    <th>Squad Strength</th>
                    <th>Manager</th>
                    <th>Manager Rating</th>
                    <th>Recent Form</th>
                    <th>WC Pedigree</th>
                  </tr>
                </thead>
                <tbody>
                  {favorites?.map((fav, i) => (
                    <tr key={fav.team}>
                      <td className="rank-num">#{i + 1}</td>
                      <td className="table-team-cell">
                        <span className="table-flag">{getFlag(fav.team)}</span>
                        <span className="table-team-name">{fav.team}</span>
                      </td>
                      <td>
                        <div className="rating-cell">
                          <span className="rating-val">{fav.rating}</span>
                          <div className="rating-bar-bg">
                            <div
                              className="rating-bar-fill"
                              style={{ width: `${Math.min(100, Math.max(0, (fav.rating - 1000) / 10))}%` }}
                            ></div>
                          </div>
                        </div>
                      </td>
                      <td>#{fav.fifa_rank}</td>
                      <td>
                        <span className="stat-strength-badge" style={{ opacity: fav.squad_strength / 100 }}>
                          {fav.squad_strength}/100
                        </span>
                      </td>
                      <td>{fav.manager}</td>
                      <td>{fav.manager_score}</td>
                      <td>{fav.form}</td>
                      <td>{fav.pedigree}/100</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Sub-component for Knockout Matches
function KnockoutMatchCard({ match, isFinals = false }) {
  if (!match) return null;
  const homeWinner = match.winner === match.home;
  const awayWinner = match.winner === match.away;
  const extraTime = match.extra_time;

  return (
    <div className={`ko-match-card glass-card ${isFinals ? 'finals-card' : ''}`}>
      <div className="ko-match-header">
        {extraTime && <span className="ko-et-badge">ET/Penalties</span>}
      </div>
      <div className="ko-match-body">
        <div className={`ko-team ${homeWinner ? 'ko-winner' : 'ko-loser'}`}>
          <span className="ko-flag">{getFlag(match.home)}</span>
          <span className="ko-name">{match.home}</span>
          <span className="ko-goals">{match.score.split('-')[0]}</span>
        </div>
        <div className={`ko-team ${awayWinner ? 'ko-winner' : 'ko-loser'}`}>
          <span className="ko-flag">{getFlag(match.away)}</span>
          <span className="ko-name">{match.away}</span>
          <span className="ko-goals">{match.score.split('-')[1]}</span>
        </div>
      </div>
      {match.prob_home && (
        <div className="ko-match-probs">
          <div className="ko-prob-item text-green" style={{ opacity: homeWinner ? 1 : 0.6 }}>
            <span>{(match.prob_home * 100).toFixed(0)}%</span>
          </div>
          <div className="ko-prob-item text-draw" style={{ opacity: 0.6 }}>
            <span>{(match.prob_draw * 100).toFixed(0)}%</span>
          </div>
          <div className="ko-prob-item text-red" style={{ opacity: awayWinner ? 1 : 0.6 }}>
            <span>{(match.prob_away * 100).toFixed(0)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}
