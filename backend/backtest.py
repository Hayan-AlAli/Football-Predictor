"""Walk-forward backtest: how well do the model's calls hold up?

Replays the bundled history from a start date. Each week, every candidate is
fitted only on the matches played before that week, predicts that week's
matches, and is scored when they finish:

- RPS (ranked probability score, lower is better): the standard for
  home/draw/away forecasts, since it rewards being close on the ordered
  outcome, not just right on the most likely one;
- log loss and accuracy of the most likely outcome.

    python -m backend.backtest                    # from Aug 2023
    python -m backend.backtest --start 2024-08-01 --xi 0.0019 0.003

This is how the production model was chosen (see backend/dixon_coles.py).
"""
import argparse

import numpy as np
import pandas as pd

from backend import dixon_coles, predictor


def _outcome_probs(grid):
    return np.tril(grid, -1).sum(), np.trace(grid), np.triu(grid, 1).sum()


def rps(p, y):
    cp, cy = np.cumsum(p, 1)[:, :2], np.cumsum(y, 1)[:, :2]
    return ((cp - cy) ** 2).sum(1) / 2


def dixon_coles_candidate(xi, xg_weight):
    def predict(history, week, as_of):
        model = dixon_coles.fit(history, as_of, xi=xi, xg_weight=xg_weight)
        return [_outcome_probs(model.score_matrix(*model.expected_goals(r.home_team, r.away_team)))
                for r in week.itertuples()]
    return predict


def elo_candidate(history, week, as_of):
    out = []
    for r in week.itertuples():
        hg, ag = predictor.elo_goal_expectations(r.home_elo, r.away_elo)
        ph, pd_, pa, *_ = predictor.calculate_probabilities(hg, ag)
        out.append((ph, pd_, pa))
    return out


def base_rate_candidate(history, week, as_of):
    y = np.sign(history['home_goals'] - history['away_goals'])
    freq = [(y > 0).mean(), (y == 0).mean(), (y < 0).mean()]
    return [freq] * len(week)


def run(history, start, candidates):
    history = history.sort_values('date').reset_index(drop=True)
    history['date'] = pd.to_datetime(history['date'])
    test = history[history['date'] >= start]
    outcome = np.sign(test['home_goals'] - test['away_goals']).to_numpy()
    y = np.stack([outcome > 0, outcome == 0, outcome < 0], 1).astype(float)
    weeks = test['date'].dt.to_period('W').dt.start_time
    scores = {}
    for name, predict in candidates.items():
        probs = []
        for week_start, week in test.groupby(weeks, sort=True):
            past = history[history['date'] < week_start]
            probs.extend(predict(past, week, week_start))
        p = np.clip(np.array(probs, float), 1e-12, 1)
        scores[name] = {
            'rps': rps(p, y).mean(),
            'log_loss': -np.log((p * y).sum(1)).mean(),
            'accuracy': (p.argmax(1) == y.argmax(1)).mean(),
        }
    return len(test), scores


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--start', default='2023-08-01')
    parser.add_argument('--xi', type=float, nargs='*', default=[dixon_coles.XI],
                        help='time-decay values to try for the production model')
    args = parser.parse_args()

    # Every candidate is scored on the same matches: those with a pre-match
    # Elo in the bundled history.
    history = predictor.form_frame().dropna(subset=['home_elo', 'away_elo'])
    candidates = {}
    for xi in args.xi:
        candidates[f'Dixon-Coles, {dixon_coles.XG_WEIGHT:.0%} xG (xi={xi})'] = \
            dixon_coles_candidate(xi, dixon_coles.XG_WEIGHT)
    candidates['Dixon-Coles, goals only'] = dixon_coles_candidate(dixon_coles.XI, 0.0)
    candidates['Elo only'] = elo_candidate
    candidates['Base rates'] = base_rate_candidate

    n, scores = run(history, pd.Timestamp(args.start), candidates)
    print(f'{n} matches from {args.start}, refitted weekly on earlier matches only\n')
    print(f"{'model':<40} {'RPS':>7} {'log loss':>9} {'accuracy':>9}")
    for name, s in sorted(scores.items(), key=lambda kv: kv[1]['rps']):
        print(f"{name:<40} {s['rps']:7.4f} {s['log_loss']:9.4f} {s['accuracy']:9.1%}")


if __name__ == '__main__':
    main()
