import type { Prediction } from '../types';

interface PredictionBarProps {
  prediction: Prediction;
  homeTeam: string;
  awayTeam: string;
}

export default function PredictionBar({ prediction, homeTeam, awayTeam }: PredictionBarProps) {
    if (!prediction) return null;

    const probHome = (prediction.prob_home * 100).toFixed(1);
    const probDraw = (prediction.prob_draw * 100).toFixed(1);
    const probAway = (prediction.prob_away * 100).toFixed(1);

    const maxProb = Math.max(prediction.prob_home, prediction.prob_draw, prediction.prob_away);

    const isHomeHighest = prediction.prob_home === maxProb;
    const isDrawHighest = prediction.prob_draw === maxProb;
    const isAwayHighest = prediction.prob_away === maxProb;

    return (
        <div className="prediction-section">
            <div className="prediction-title">Prediction</div>

            <div className="probability-bars">
                <div className="prob-row">
                    <span className="prob-label" title={homeTeam}>
                        {homeTeam?.length > 10 ? homeTeam.substring(0, 10) + '...' : homeTeam}
                    </span>
                    <div className="prob-bar-container">
                        <div
                            className="prob-bar prob-bar--home"
                            style={{ width: `${probHome}%` }}
                        />
                    </div>
                    <span className={`prob-value ${isHomeHighest ? 'prob-value--highest' : ''}`}>
                        {probHome}%
                    </span>
                </div>

                <div className="prob-row">
                    <span className="prob-label">Draw</span>
                    <div className="prob-bar-container">
                        <div
                            className="prob-bar prob-bar--draw"
                            style={{ width: `${probDraw}%` }}
                        />
                    </div>
                    <span className={`prob-value ${isDrawHighest ? 'prob-value--highest' : ''}`}>
                        {probDraw}%
                    </span>
                </div>

                <div className="prob-row">
                    <span className="prob-label" title={awayTeam}>
                        {awayTeam?.length > 10 ? awayTeam.substring(0, 10) + '...' : awayTeam}
                    </span>
                    <div className="prob-bar-container">
                        <div
                            className="prob-bar prob-bar--away"
                            style={{ width: `${probAway}%` }}
                        />
                    </div>
                    <span className={`prob-value ${isAwayHighest ? 'prob-value--highest' : ''}`}>
                        {probAway}%
                    </span>
                </div>
            </div>

            {prediction.score && (
                <div className="predicted-score">
                    <span className="predicted-score-label">Expected Score:</span>
                    <span className="predicted-score-value">{prediction.score}</span>

                    {prediction.winner && (
                        <div className="predicted-winner">
                            <span className="predicted-winner-label">→</span>
                            <span className="predicted-winner-name">
                                {prediction.winner === 'Draw' ? 'Draw' : `${prediction.winner} Win`}
                            </span>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
