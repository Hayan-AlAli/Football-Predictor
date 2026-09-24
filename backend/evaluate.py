import random

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.isotonic import IsotonicRegression
from sklearn.preprocessing import LabelEncoder

from backend import features, insights, predictor, utils

SEED = 42
_BEST_ORDER = (("1-0", "2-0", "2-1", "3-0", "3-1", "3-2", "4-0", "4-1", "4-2", "0-0"),
               ("0-1", "0-2", "1-2", "0-3", "1-3", "2-3", "0-4", "1-4", "2-4", "0-0"),
               ("1-1", "2-2", "3-3", "0-0"))


def split_by_season(df):
    work = df.copy()
    work["_sy"] = work["date"].apply(insights.season_year_of)
    max_sy = work["_sy"].max()
    test = work[work["_sy"] == max_sy].drop(columns="_sy").sort_values("date")
    train = work[work["_sy"] < max_sy].drop(columns="_sy").sort_values("date")
    return train, test


def model_specs():
    return {
        "baseline_rf": {"spec": "v1", "model": "rf"},
        "challenger_v2_hgb": {"spec": "v2", "model": "hgb"},
        "challenger_v2_hgb_calib": {"spec": "v2", "model": "hgb", "calibrate": True},
    }


def _fit_pair(X_train, y_home, y_away, spec_key):
    cfg = model_specs()[spec_key]
    if cfg["model"] == "rf":
        mh = RandomForestRegressor(n_estimators=100, random_state=SEED)
        ma = RandomForestRegressor(n_estimators=100, random_state=SEED)
        mh.fit(X_train, y_home)
        ma.fit(X_train, y_away)
        return mh, ma
    if cfg["model"] == "hgb":
        try:
            mh = HistGradientBoostingRegressor(loss="poisson", max_iter=200, random_state=SEED)
            ma = HistGradientBoostingRegressor(loss="poisson", max_iter=200, random_state=SEED)
        except TypeError:
            mh = HistGradientBoostingRegressor(max_iter=200, random_state=SEED)
            ma = HistGradientBoostingRegressor(max_iter=200, random_state=SEED)
        mh.fit(X_train, y_home)
        ma.fit(X_train, y_away)
        return mh, ma
    raise ValueError(f"unknown model: {cfg['model']}")


def calibrate_probs(pred_matrix, fit_matrix, fit_targets, clamp=(0.01, 0.99)):
    """Isotonic calibration per outcome column.
    pred_matrix: (n, 3) home/away/draw probabilities to transform.
    fit_matrix: (m, 3) probabilities used to fit the maps.
    fit_targets: (m, 3) one-hot actual outcomes.
    Returns a (n, 3) array, columns order preserved, clamped to [clamp].
    """
    out = np.empty_like(np.asarray(pred_matrix, dtype=float))
    for col in range(3):
        iso = IsotonicRegression(out_of_bounds="clip", y_min=clamp[0], y_max=clamp[1])
        iso.fit(np.asarray(fit_matrix)[:, col], np.asarray(fit_targets)[:, col])
        out[:, col] = np.clip(iso.predict(np.asarray(pred_matrix)[:, col]), clamp[0], clamp[1])
    return out


def _predict_pair(pair, X_test):
    mh, ma = pair
    return mh.predict(X_test), ma.predict(X_test)


def _outcome_probs(hg, ag):
    ph, pd_, pa, *_ = predictor.calculate_probabilities(hg, ag)
    return ph, pd_, pa


def _actual_outcome(home_goals, away_goals):
    if home_goals > away_goals:
        return 0  # home
    if away_goals > home_goals:
        return 1  # away
    return 2  # draw


def score_test(train_df, test_df, spec_key):
    cfg = model_specs()[spec_key]
    spec = cfg["spec"]
    train, test = train_df.copy(), test_df.copy()
    train = train.reset_index(drop=True)
    test = test.reset_index(drop=True)

    train = features.build_feature_columns(train, spec)
    test = features.build_feature_columns(test, spec)
    train["home_team"] = train["home_team"].apply(utils.normalize_team_name)
    train["away_team"] = train["away_team"].apply(utils.normalize_team_name)
    test["home_team"] = test["home_team"].apply(utils.normalize_team_name)
    test["away_team"] = test["away_team"].apply(utils.normalize_team_name)

    le = LabelEncoder()
    all_teams = pd.concat([train["home_team"], train["away_team"]]).unique()
    le.fit(all_teams)
    train["home_team_code"] = le.transform(train["home_team"])
    train["away_team_code"] = le.transform(train["away_team"])
    test["home_team_code"] = le.transform(test["home_team"].map(lambda t: t if t in le.classes_ else le.classes_[0]))
    test["away_team_code"] = le.transform(test["away_team"].map(lambda t: t if t in le.classes_ else le.classes_[0]))

    cols = features.feature_columns(spec)
    X_train = train[cols]
    y_home = train["home_goals"]
    y_away = train["away_goals"]
    pair = _fit_pair(X_train, y_home, y_away, spec_key)
    X_test = test[cols]
    pred_home, pred_away = _predict_pair(pair, X_test)

    n = len(test)
    probs_matrix = np.zeros((n, 3))
    outcomes = np.zeros((n, 3))
    for i in range(n):
        ph, pd_, pa = _outcome_probs(float(pred_home[i]), float(pred_away[i]))
        probs_matrix[i] = [ph, pa, pd_]          # home, away, draw
        a = _actual_outcome(int(test.iloc[i]["home_goals"]), int(test.iloc[i]["away_goals"]))
        outcomes[i, a] = 1.0

    scored_probs = probs_matrix
    scored_outcomes = outcomes
    if cfg.get("calibrate"):
        half = n // 2
        scored_probs = calibrate_probs(probs_matrix[:half], probs_matrix[half:], outcomes[half:])
        scored_outcomes = outcomes[:half]

    brier = float(np.mean(np.sum((scored_probs - scored_outcomes) ** 2, axis=1)))
    logloss = -np.mean(np.log(np.clip(np.sum(scored_probs * scored_outcomes, axis=1), 1e-9, 1.0)))
    correct = int(np.sum(np.argmax(scored_probs, axis=1) == np.argmax(scored_outcomes, axis=1)))
    n_scored = len(scored_probs)
    return {
        "brier": round(brier, 4),
        "log_loss": round(logloss, 4),
        "accuracy": round(correct / n_scored, 4),
        "n_matches": n_scored,
    }


def run_all():
    import joblib
    df = joblib.load("training_data.pkl")
    train, test = split_by_season(df)
    out = []
    for spec_key in model_specs():
        row = {"spec": spec_key}
        row.update(score_test(train, test, spec_key))
        out.append(row)
    return out


if __name__ == "__main__":
    print(f"{'spec':<16}{'brier':>8}{'log_loss':>10}{'accuracy':>10}{'n':>6}")
    for r in run_all():
        print(f"{r['spec']:<16}{r['brier']:>8}{r['log_loss']:>10.4f}{r['accuracy']:>10.1%}{r['n_matches']:>6}")