import random

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
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
    }


def _fit_pair(X_train, y_home, y_away, spec_key):
    cfg = model_specs()[spec_key]
    if cfg["model"] == "rf":
        mh = RandomForestRegressor(n_estimators=100, random_state=SEED)
        ma = RandomForestRegressor(n_estimators=100, random_state=SEED)
        mh.fit(X_train, y_home)
        ma.fit(X_train, y_away)
        return mh, ma
    raise ValueError(f"unknown model: {cfg['model']}")


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

    brier, logloss, correct, n = 0.0, 0.0, 0, len(test)
    for i in range(n):
        ph, pd_, pa = _outcome_probs(float(pred_home[i]), float(pred_away[i]))
        actual = _actual_outcome(int(test.iloc[i]["home_goals"]), int(test.iloc[i]["away_goals"]))
        probs = [ph, pa, pd_]
        brier += sum((probs[k] - (1.0 if k == actual else 0.0)) ** 2 for k in range(3))
        logloss += -np.log(max(1e-9, probs[actual]))
        if max(range(3), key=lambda k: probs[k]) == actual:
            correct += 1
    return {
        "brier": round(brier / n, 4),
        "log_loss": round(logloss / n, 4),
        "accuracy": round(correct / n, 4),
        "n_matches": n,
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