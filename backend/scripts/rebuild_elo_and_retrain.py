"""Recompute training-data Elo with backend/elo.py and retrain the models.

Rewrites home_elo / away_elo / elo_difference in training_data.pkl from a
full football-data.co.uk replay (no ClubElo), reports held-out accuracy
before and after, then refits model_home / model_away on all rows.

    python -m backend.scripts.rebuild_elo_and_retrain [--save]

Without --save it only reports the comparison.
"""
import sys

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor

from backend import data_manager, evaluate, features, insights

PKL = 'training_data.pkl'


def _fit(X, y):
    return RandomForestRegressor(n_estimators=100, random_state=42).fit(X, y)


def holdout_scores(df):
    """Train on every season but the latest, score the latest."""
    cols = features.PRODUCTION_FEATURE_COLUMNS
    season = df['date'].apply(insights.season_year_of)
    train, test = df[season < season.max()], df[season == season.max()]
    mh = _fit(train[cols], train['home_goals'])
    ma = _fit(train[cols], train['away_goals'])
    ph, pa = mh.predict(test[cols]), ma.predict(test[cols])
    brier = logloss = correct = 0.0
    for i, r in enumerate(test.itertuples()):
        p_home, p_draw, p_away = evaluate._outcome_probs(float(ph[i]), float(pa[i]))
        probs = np.array([p_home, p_away, p_draw])
        actual = evaluate._actual_outcome(int(r.home_goals), int(r.away_goals))
        onehot = np.eye(3)[actual]
        brier += float(np.sum((probs - onehot) ** 2))
        logloss += -np.log(max(probs[actual], 1e-9))
        correct += int(np.argmax(probs) == actual)
    n = len(test)
    return {'brier': round(brier / n, 4), 'log_loss': round(logloss / n, 4),
            'accuracy': round(correct / n, 4), 'n_matches': n}


def main(save=False):
    df = joblib.load(PKL)
    print('old Elo  ', holdout_scores(df))

    history = data_manager.fetch_historical_results()
    rebuilt = data_manager.merge_data_with_elo(df.copy(), history=history)
    rebuilt = features.add_elo_difference(rebuilt)
    print('new Elo  ', holdout_scores(rebuilt))

    if not save:
        print('Dry run: pass --save to write training_data.pkl and the models.')
        return
    cols = features.PRODUCTION_FEATURE_COLUMNS
    joblib.dump(_fit(rebuilt[cols], rebuilt['home_goals']), 'model_home.pkl')
    joblib.dump(_fit(rebuilt[cols], rebuilt['away_goals']), 'model_away.pkl')
    joblib.dump(rebuilt, PKL)
    print(f'Saved models and {PKL} ({len(rebuilt)} rows).')


if __name__ == '__main__':
    main(save='--save' in sys.argv)
