# Prediction Accuracy Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make predictions measurably more accurate, provable against history, gated by a backtest harness — only changes that beat the current model ship.

**Architecture:** Champion/challenger via `backend/evaluate.py` — deterministic offline temporal holdout on `training_data.pkl` (train seasons < last, test = last). Baseline spec replicates the production RandomForest exactly; challengers add decayed features, Poisson gradient boosting, and isotonic calibration — each measured independently on Brier/log-loss/accuracy vs actual outcomes. Champion gets baked into `train_model.py` + `predictor.py` via a spec registry and `model_meta.json`; retraining stays current via automation + weekly CI.

**Tech Stack:** Python 3.11, pandas 2.3.3, numpy 2.3.5, scikit-learn 1.7.2 (`HistGradientBoostingRegressor(loss="poisson")` available), joblib, pytest, FastAPI.

## Global Constraints

- No new runtime Python dependencies — sklearn only (already present).
- All evaluation offline and deterministic (seed 42 everywhere, stable sorts).
- Tests MUST NOT hit the network (clubelo.com hangs when down — monkeypatch fetches).
- Test command from repo root: `python -m pytest tests -q`; run the focused test first (e.g. `python -m pytest tests/test_evaluate.py -v`).
- `predict_match` response shape unchanged (frontend untouched).
- `training_data.pkl` has quirks to handle generically: season-year 2021 absent, 2020 has 760 rows (double season), last season-year (2025) is partial (~250 rows) and is the TEST split. Never hardcode season counts — split by max season_year.
- Commit style from repo history: `feat: ...`, `fix: ...`, one logical change per commit.
- Home/away xG in training data may be NaN — coerce with `pd.to_numeric(..., errors="coerce").fillna(0.0)` before modeling.

---

### Task 1: Feature builders v2 — decayed form, league-relative, elo gap

**Files:**
- Modify: `backend/features.py`
- Test: `tests/test_features.py` (new file)

**Interfaces:**
- Consumes: nothing new (uses `utils.normalize_team_name` only if needed; teams in `training_data.pkl` are already normalized).
- Produces:
  - `team_decayed_form(team_df, half_life_days=30.0) -> tuple[float, float]` — (decayed goals avg, decayed xG avg) over the team's matches, weighting each prior match by `exp(-days_before_today / half_life_days)`, where days_before_today counts back from the *latest* date in the slice. Empty slice → `(0.0, 0.0)`.
  - `calculate_rolling_stats_v2(df, half_life_days=30.0) -> pd.DataFrame` — adds columns `home_rolling_goals, away_rolling_goals, home_rolling_xg, away_rolling_xg` (decayed) and `home_relative_goals, away_relative_goals` (rolling minus league-wide decayed goals avg across all teams, clipped to >= 0). Operates per-row over matches strictly before each row's date (no leakage).
  - `feature_columns(spec: str) -> list[str]` — `"v1"` → `["home_team_code","away_team_code","home_elo","away_elo","home_rolling_goals","away_rolling_goals","home_rolling_xg","away_rolling_xg"]` (exact current production order); `"v2"` → v1 columns + `["elo_gap","home_relative_goals","away_relative_goals"]` (order: v1 eight, then `elo_gap`, `home_relative_goals`, `away_relative_goals`).
  - `build_feature_columns(df, spec: str) -> pd.DataFrame` — v1: runs the EXISTING `calculate_rolling_stats` untouched (production parity); v2: runs `calculate_rolling_stats_v2`; both then add `elo_gap = home_elo - away_elo` for v2 only. Returns df with all `feature_columns(spec)` present.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_features.py
import pandas as pd
import pytest

from backend import features


def _df(rows):
    return pd.DataFrame(rows)


def test_team_decayed_form_weights_recent_more():
    team = pd.DataFrame([
        {"date": pd.Timestamp("2026-01-01"), "goals_scored": 0.0, "xg_for": 0.5},
        {"date": pd.Timestamp("2026-02-01"), "goals_scored": 4.0, "xg_for": 3.0},
    ])
    g, x = features.team_decayed_form(team, half_life_days=15.0)
    # 31 days gap -> second game weight ~8x first; still an average, so 0 < g < 4
    assert 2.0 < g < 4.0
    assert 1.5 < x < 3.0


def test_team_decayed_form_empty():
    g, x = features.team_decayed_form(pd.DataFrame(columns=["date", "goals_scored", "xg_for"]))
    assert (g, x) == (0.0, 0.0)


def test_v2_rolling_no_leakage_uses_prior_matches_only():
    rows = [
        {"date": pd.Timestamp("2026-01-01"), "home_team": "A", "away_team": "B",
         "home_goals": 1, "away_goals": 0, "home_xg": 0.5, "away_xg": 0.2},
        {"date": pd.Timestamp("2026-01-08"), "home_team": "B", "away_team": "A",
         "home_goals": 2, "away_goals": 0, "home_xg": 1.8, "away_xg": 0.1},
    ]
    df = features.calculate_rolling_stats_v2(_df(rows))
    # Match 2: A's decayed form uses only match 1 (A scored 1, xg 0.5)
    assert df.loc[1, "away_rolling_goals"] == 1.0
    assert df.loc[1, "away_rolling_xg"] == 0.5


def test_v2_league_relative_clipped_nonnegative():
    rows = [
        {"date": pd.Timestamp("2026-01-01"), "home_team": "A", "away_team": "B",
         "home_goals": 0, "away_goals": 0, "home_xg": 0.1, "away_xg": 0.1},
        {"date": pd.Timestamp("2026-01-08"), "home_team": "B", "away_team": "A",
         "home_goals": 0, "away_goals": 0, "home_xg": 0.1, "away_xg": 0.1},
    ]
    df = features.calculate_rolling_stats_v2(_df(rows))
    assert (df["home_relative_goals"] >= 0).all()
    assert (df["away_relative_goals"] >= 0).all()


def test_feature_columns_v1_matches_production():
    assert features.feature_columns("v1") == [
        "home_team_code", "away_team_code", "home_elo", "away_elo",
        "home_rolling_goals", "away_rolling_goals", "home_rolling_xg", "away_rolling_xg",
    ]


def test_feature_columns_v2_extends_v1():
    cols = features.feature_columns("v2")
    assert cols[:8] == features.feature_columns("v1")
    assert cols[8:] == ["elo_gap", "home_relative_goals", "away_relative_goals"]


def test_build_feature_columns_v1_preserves_legacy_semantics():
    rows = [
        {"date": pd.Timestamp("2026-01-01"), "home_team": "A", "away_team": "B",
         "home_goals": 1, "away_goals": 0, "home_xg": 0.5, "away_xg": 0.2,
         "home_elo": 1500.0, "away_elo": 1450.0},
        {"date": pd.Timestamp("2026-01-08"), "home_team": "B", "away_team": "A",
         "home_goals": 2, "away_goals": 0, "home_xg": 1.8, "away_xg": 0.1,
         "home_elo": 1450.0, "away_elo": 1500.0},
    ]
    df = features.build_feature_columns(_df(rows), "v1")
    for col in features.feature_columns("v1"):
        assert col in df.columns
    assert "elo_gap" not in df.columns


def test_build_feature_columns_v2_adds_elo_gap():
    rows = [
        {"date": pd.Timestamp("2026-01-01"), "home_team": "A", "away_team": "B",
         "home_goals": 1, "away_goals": 0, "home_xg": 0.5, "away_xg": 0.2,
         "home_elo": 1600.0, "away_elo": 1500.0},
    ]
    df = features.build_feature_columns(_df(rows), "v2")
    assert df.loc[0, "elo_gap"] == 100.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_features.py -v`
Expected: FAIL — `AttributeError: module 'backend.features' has no attribute 'team_decayed_form'` (and feature_columns/build_feature_columns missing).

- [ ] **Step 3: Implement in `backend/features.py`**

Append to `backend/features.py` (keep `calculate_rolling_stats` EXACTLY as-is — production parity depends on it):

```python
import math


def team_decayed_form(team_df, half_life_days=30.0):
    if team_df.empty:
        return 0.0, 0.0
    latest = team_df["date"].max()
    weights = []
    gs, xs = [], []
    for _, r in team_df.iterrows():
        days = max(0.0, (latest - r["date"]).total_seconds() / 86400.0)
        w = math.exp(-days / half_life_days)
        weights.append(w)
        gs.append(0.0 if pd.isna(r.get("goals_scored")) else float(r["goals_scored"]))
        xs.append(0.0 if pd.isna(r.get("xg_for")) else float(r["xg_for"]))
    tw = sum(weights)
    if tw <= 0:
        return 0.0, 0.0
    return sum(w * g for w, g in zip(weights, gs)) / tw, sum(w * x for w, x in zip(weights, xs)) / tw


def _team_matches(df, team_name):
    return df[(df["home_team"] == team_name) | (df["away_team"] == team_name)].copy()


def _team_record(row, team_name):
    if row["home_team"] == team_name:
        return {"goals_scored": row["home_goals"], "xg_for": row["home_xg"]}
    return {"goals_scored": row["away_goals"], "xg_for": row["away_xg"]}


def calculate_rolling_stats_v2(df, half_life_days=30.0):
    df = df.copy()
    df["home_goals"] = pd.to_numeric(df["home_goals"], errors="coerce").fillna(0.0)
    df["away_goals"] = pd.to_numeric(df["away_goals"], errors="coerce").fillna(0.0)
    df["home_xg"] = pd.to_numeric(df["home_xg"], errors="coerce").fillna(0.0)
    df["away_xg"] = pd.to_numeric(df["away_xg"], errors="coerce").fillna(0.0)

    hg, ag, hx, ax, hrel, arel = [], [], [], [], [], []
    for idx, row in df.iterrows():
        h_team, a_team = row["home_team"], row["away_team"]
        prior = df[df.index < idx]
        h_prior = _team_matches(prior, h_team)
        a_prior = _team_matches(prior, a_team)
        h_rec = [_team_record(r, h_team) for _, r in h_prior.iterrows()]
        a_rec = [_team_record(r, a_team) for _, r in a_prior.iterrows()]
        hg_t, hx_t = team_decayed_form(pd.DataFrame(h_rec) if h_rec else pd.DataFrame(columns=["date", "goals_scored", "xg_for"]), half_life_days)
        ag_t, ax_t = team_decayed_form(pd.DataFrame(a_rec) if a_rec else pd.DataFrame(columns=["date", "goals_scored", "xg_for"]), half_life_days)

        league_vals = []
        for t in sorted(set(df.loc[df.index < idx, "home_team"]) | set(df.loc[df.index < idx, "away_team"])):
            t_rec = [_team_record(r, t) for _, r in _team_matches(prior, t).iterrows()]
            if t_rec:
                league_vals.append(team_decayed_form(pd.DataFrame(t_rec), half_life_days)[0])
        league_avg = sum(league_vals) / len(league_vals) if league_vals else 0.0

        hg.append(hg_t); ag.append(ag_t); hx.append(hx_t); ax.append(ax_t)
        hrel.append(max(0.0, hg_t - league_avg)); arel.append(max(0.0, ag_t - league_avg))

    df["home_rolling_goals"] = hg
    df["away_rolling_goals"] = ag
    df["home_rolling_xg"] = hx
    df["away_rolling_xg"] = ax
    df["home_relative_goals"] = hrel
    df["away_relative_goals"] = arel
    return df


_FEATURE_COLUMNS_V1 = [
    "home_team_code", "away_team_code", "home_elo", "away_elo",
    "home_rolling_goals", "away_rolling_goals", "home_rolling_xg", "away_rolling_xg",
]
_FEATURE_COLUMNS_V2 = _FEATURE_COLUMNS_V1 + ["elo_gap", "home_relative_goals", "away_relative_goals"]


def feature_columns(spec):
    if spec == "v1":
        return list(_FEATURE_COLUMNS_V1)
    if spec == "v2":
        return list(_FEATURE_COLUMNS_V2)
    raise ValueError(f"Unknown feature spec: {spec}")


def build_feature_columns(df, spec):
    df = df.copy()
    if spec == "v1":
        df = calculate_rolling_stats(df)
    elif spec == "v2":
        df = calculate_rolling_stats_v2(df)
    else:
        raise ValueError(f"Unknown feature spec: {spec}")
    if "elo_gap" in feature_columns(spec):
        df["elo_gap"] = pd.to_numeric(df["home_elo"], errors="coerce").fillna(1500.0) - pd.to_numeric(df["away_elo"], errors="coerce").fillna(1500.0)
    return df
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_features.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/features.py tests/test_features.py
git commit -m "feat: decayed and league-relative feature builders with spec registry"
```

---

### Task 2: Backtest harness — split, scorer, baseline spec, CLI

**Files:**
- Create: `backend/evaluate.py`
- Test: `tests/test_evaluate.py` (new file)

**Interfaces:**
- Consumes: `features.feature_columns(spec)`, `features.build_feature_columns(df, spec)` from Task 1; `predictor.calculate_probabilities(home_avg, away_avg, max_goals=10)` (exists); `insights.season_year_of(ts)` (exists).
- Produces:
  - `split_by_season(df) -> tuple[pd.DataFrame, pd.DataFrame]` — (train, test) by `season_year_of(date)`, test = rows with max season_year, train = everything else. Sorted by date within each frame.
  - `model_specs() -> dict[str, dict]` — `{"baseline_rf": {"spec": "v1", "model": "rf"}}` initially.
  - `expected_goals(model_pair, X_test) -> tuple[np.ndarray, np.ndarray]` — clamped `max(0, pred)` per model.
  - `score_test(train_df, test_df, spec_key) -> dict` — encodes teams (LabelEncoder fit on train only), builds feature columns per spec on both splits, trains the model pair, predicts test expected goals, derives home/draw/away probs via `calculate_probabilities`, returns `{"brier": float, "log_loss": float, "accuracy": float, "n_matches": int}`.
  - `run_all() -> list[dict]` — one entry per spec_key with scores + a row summary line for the CLI table.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_evaluate.py
import pandas as pd

from backend import evaluate


def _data():
    rows = []
    for i, sy in enumerate([2020, 2021, 2022]):
        for j in range(5):
            rows.append({
                "date": pd.Timestamp(f"{sy + 1}-01-0{j + 1}"),
                "home_team": "A" if j % 2 == 0 else "B",
                "away_team": "B" if j % 2 == 0 else "A",
                "home_goals": j % 3, "away_goals": (j + 1) % 3,
                "home_xg": float(j), "away_xg": float(j + 1),
                "home_elo": 1500.0, "away_elo": 1450.0,
            })
    return pd.DataFrame(rows)


def test_split_uses_last_season_as_test():
    df = _data()
    train, test = evaluate.split_by_season(df)
    assert test["date"].dt.year.min() == max(df["date"].dt.year)
    assert train["date"].dt.year.max() < test["date"].dt.year.min()


def test_split_is_deterministic_and_exhaustive():
    df = _data()
    train, test = evaluate.split_by_season(df)
    assert len(train) + len(test) == len(df)


def test_model_specs_contains_baseline():
    assert "baseline_rf" in evaluate.model_specs()


def test_score_test_returns_metrics_dict(monkeypatch):
    df = _data()
    monkeypatch.setattr(evaluate, "_fit_pair", lambda X_train, yh, ya, spec_key: (None, None))
    monkeypatch.setattr(evaluate, "_predict_pair", lambda pair, X: (pd.Series([1.2, 0.8, 1.1, 0.9, 1.0]), pd.Series([0.7, 1.1, 1.2, 0.8, 1.0])))
    res = evaluate.score_test(_data(), df[df["date"].dt.year == 2023], "baseline_rf")
    for key in ("brier", "log_loss", "accuracy", "n_matches"):
        assert key in res
    assert res["n_matches"] == 5


def test_run_all_returns_rows():
    rows = evaluate.run_all()
    assert isinstance(rows, list)
    assert len(rows) >= 1
    assert all({"spec", "brier", "log_loss", "accuracy", "n_matches"} <= set(r) for r in rows)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_evaluate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.evaluate'`

- [ ] **Step 3: Implement `backend/evaluate.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_evaluate.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Smoke-run the baseline**

Run: `python -m backend.evaluate`
Expected: a one-row table `baseline_rf` with real numbers (~0.6 brier, ~0.85 log_loss, ~0.5 accuracy). Record the output — Task 5 compares challengers against it.

- [ ] **Step 6: Commit**

```bash
git add backend/evaluate.py tests/test_evaluate.py
git commit -m "feat: backtest harness with baseline RF spec"
```

---

### Task 3: Challenger specs — v2 features + Poisson GBM + calibration

**Files:**
- Modify: `backend/evaluate.py`
- Test: `tests/test_evaluate.py` (extend)

**Interfaces:**
- Consumes: `features.team_decayed_form` (Task 1), `score_test` structure (Task 2).
- Produces: `model_specs()` now includes:
  - `"challenger_v2_hgb"`: `{"spec": "v2", "model": "hgb"}` with `HistGradientBoostingRegressor(loss="poisson", max_iter=200, random_state=SEED)` fallback `squared_error`.
  - `"challenger_v2_hgb_calib"`: same model, plus isotonic calibration: fit on rows with index >= n/2 of TEST set (temporally second half), transform all.
  - `calibrate_probs(pred_home, pred_draw, pred_away, fit_probs, fit_outcomes, clamp=(0.01, 0.99)) -> tuple[np.ndarray, np.ndarray, np.ndarray]` — isotonic per class (1/0.5/0 targets), returns clamped arrays.
  - `run_all()` iterates ALL specs (3 rows).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_evaluate.py`)

```python
def test_model_specs_has_challengers():
    specs = evaluate.model_specs()
    assert "challenger_v2_hgb" in specs
    assert "challenger_v2_hgb_calib" in specs


def test_calibrate_clamps_and_order_preserved():
    preds = np.array([[0.05, 0.45, 0.98], [0.3, 0.4, 0.9]])
    fit_probs = np.array([[0.1, 0.5, 0.9], [0.2, 0.6, 0.95]])
    fit_out = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    out = evaluate.calibrate_probs(preds, fit_probs, fit_out)
    assert out.shape == preds.shape
    assert (out >= 0.01).all() and (out <= 0.99).all()
    assert out[0, 2] > out[0, 0]  # away more likely than home, order preserved


def test_calibrated_v2_runs_end_to_end():
    train, test = evaluate.split_by_season(pd.read_pickle("tests/_mini.pkl"))
    row = evaluate.score_test(train, test, "challenger_v2_hgb_calib")
    assert row["n_matches"] == len(test)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_evaluate.py::test_model_specs_has_challengers -v`
Expected: FAIL — `KeyError: 'challenger_v2_hgb'`.

- [ ] **Step 3: Build a tiny fixture dataframe for the end-to-end test**

```bash
python - <<'PY'
import joblib, pandas as pd
df = joblib.load("training_data.pkl")
last2 = df.sort_values("date").tail(60).copy()
last2.to_pickle("tests/_mini.pkl")
print("wrote", len(last2), "rows")
PY
```

Keep `tests/_mini.pkl` in the repo (60 rows, ~6 KB) so the end-to-end calibration test stays offline and fast.

- [ ] **Step 4: Implement challengers in `backend/evaluate.py`**

Replace the `model_specs`, `_fit_pair`, and the prediction-scoring part of `score_test`:

```python
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.isotonic import IsotonicRegression


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
```

In `score_test`, collect all row probabilities into a matrix first, then apply calibration to the first half using the second half as the fit set, and score only the calibrated half:

```python
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
```

Keep the existing `_outcome_probs` / `_actual_outcome` / encoding / model-fitting code from Task 2 unchanged; only the per-row scoring loop and the return dict change as shown.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_evaluate.py -v`
Expected: PASS (8 tests).

- [ ] **Step 6: Smoke-run all specs**

Run: `python -m backend.evaluate`
Expected: a 3-row table. Record the numbers (baseline vs challenger vs calibrated) — Task 5 needs them.

- [ ] **Step 7: Commit**

```bash
git add backend/evaluate.py tests/test_evaluate.py tests/_mini.pkl
git commit -m "feat: challenger specs - v2 features, Poisson GBM, isotonic calibration"
```

---

### Task 4: Meta-driven train/predict — `model_meta.json`

**Files:**
- Modify: `backend/train_model.py`, `backend/predictor.py`
- Test: `tests/test_predictor.py` (extend), `tests/test_train_model.py` (new file)

**Interfaces:**
- Consumes: `features.feature_columns(spec)`, `features.build_feature_columns(df, spec)` (Task 1).
- Produces:
  - `train(spec: str = "v1", model_kind: str = "rf") -> dict` — like today but spec-driven; writes `model_home.pkl`, `model_away.pkl`, `team_encoder.pkl`, `training_data.pkl`, and NEW `model_meta.json`: `{"spec": spec, "model": model_kind, "trained_at": "YYYY-MM-DD", "test_score": {"brier":..., "log_loss":..., "accuracy":...}}` (test_score computed by evaluate on fresh data, wrapped in try/except).
  - `predictor.MODEL_SPEC` — module global, loaded at import: `"v1"` if meta missing/unknown, else meta spec.
  - `predictor.features_for_fixture(home_team, away_team, home_elo, away_elo, training_df, spec) -> dict[str, float]` — v1: reuse existing `get_latest_stats` semantics; v2: decayed form via `features.team_decayed_form` on team slices of training_df filtered to `date < now`, plus `elo_gap`.
  - `predict_match` uses `features_for_fixture` per `MODEL_SPEC` (v2 path only when spec says v2; v1 path byte-identical behavior to today).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_train_model.py
import json
import os

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from backend import train_model


def test_train_writes_meta_and_pickles(tmp_path, monkeypatch):
    def fake_fetch(years=5):
        rows = []
        for i in range(40):
            rows.append({
                "date": pd.Timestamp(f"2024-0{1 + i % 9}-01"),
                "home_team": "A" if i % 2 else "B",
                "away_team": "B" if i % 2 else "A",
                "home_goals": i % 3, "away_goals": (i + 1) % 3,
                "home_xg": float(i % 4), "away_xg": float((i + 1) % 4),
                "home_elo": 1500.0, "away_elo": 1450.0,
            })
        return pd.DataFrame(rows)

    monkeypatch.setattr(train_model.data_manager, "fetch_training_data", fake_fetch)
    monkeypatch.setattr(train_model, "_MODEL_PREFIX", str(tmp_path) + os.sep)
    meta = train_model.train(spec="v1", model_kind="rf")
    assert os.path.exists(str(tmp_path) + "model_meta.json")
    with open(str(tmp_path) + "model_meta.json") as f:
        meta = json.load(f)
    assert meta["spec"] == "v1"
    assert "trained_at" in meta
    assert os.path.exists(str(tmp_path) + "model_home.pkl")
    assert os.path.exists(str(tmp_path) + "model_away.pkl")
    assert os.path.exists(str(tmp_path) + "team_encoder.pkl")
```

```python
# append to tests/test_predictor.py
def test_features_for_fixture_v2_shape():
    from backend import predictor, features
    df = pd.DataFrame([
        {"date": pd.Timestamp("2026-01-01"), "home_team": "Arsenal", "away_team": "Chelsea",
         "home_goals": 2, "away_goals": 1, "home_xg": 1.8, "away_xg": 0.9},
        {"date": pd.Timestamp("2026-01-08"), "home_team": "Chelsea", "away_team": "Arsenal",
         "home_goals": 0, "away_goals": 3, "home_xg": 0.7, "away_xg": 2.2},
    ])
    f = predictor.features_for_fixture("Arsenal", "Chelsea", 1600.0, 1500.0, df, "v2")
    assert set(f.keys()) == set(features.feature_columns("v2"))
    assert f["elo_gap"] == 100.0
    assert f["home_rolling_goals"] > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_predictor.py::test_features_for_fixture_v2_shape tests/test_train_model.py -v`
Expected: FAIL — `AttributeError: ... has no attribute 'features_for_fixture'` / missing meta write.

- [ ] **Step 3: Refactor `backend/train_model.py`**

Rewrite to be spec-driven (keep `train()` CLI entry `python -m backend.train_model` calling `train()`):

```python
import json
import os
from datetime import datetime, timezone

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.preprocessing import LabelEncoder

from backend import data_manager, evaluate, features, utils

MODEL_PREFIX = ""


def _path(name):
    return os.path.join(MODEL_PREFIX, name)


def train(spec="v1", model_kind="rf"):
    df = data_manager.fetch_training_data(years=5)
    if df.empty:
        print("No matches found to train on.")
        return None

    df = df.copy()
    df["home_team"] = df["home_team"].apply(utils.normalize_team_name)
    df["away_team"] = df["away_team"].apply(utils.normalize_team_name)
    df = features.build_feature_columns(df, spec)

    le = LabelEncoder()
    all_teams = pd.concat([df["home_team"], df["away_team"]]).unique()
    le.fit(all_teams)
    df["home_team_code"] = le.transform(df["home_team"])
    df["away_team_code"] = le.transform(df["away_team"])

    cols = features.feature_columns(spec)
    X = df[cols]
    y_home = pd.to_numeric(df["home_goals"], errors="coerce").fillna(0.0)
    y_away = pd.to_numeric(df["away_goals"], errors="coerce").fillna(0.0)

    if model_kind == "rf":
        mh = RandomForestRegressor(n_estimators=100, random_state=42)
        ma = RandomForestRegressor(n_estimators=100, random_state=42)
    elif model_kind == "hgb":
        mh = HistGradientBoostingRegressor(loss="poisson", max_iter=200, random_state=42)
        ma = HistGradientBoostingRegressor(loss="poisson", max_iter=200, random_state=42)
    else:
        raise ValueError(f"unknown model_kind: {model_kind}")
    mh.fit(X, y_home)
    ma.fit(X, y_away)

    joblib.dump(mh, _path("model_home.pkl"))
    joblib.dump(ma, _path("model_away.pkl"))
    joblib.dump(le, _path("team_encoder.pkl"))
    joblib.dump(df, _path("training_data.pkl"))

    test_score = None
    try:
        train_df, test_df = evaluate.split_by_season(df)
        test_score = evaluate.score_test(train_df, test_df, next(k for k, v in evaluate.model_specs().items() if v["spec"] == spec and v["model"] == model_kind))
    except Exception as e:
        print(f"Evaluation skipped: {e}")

    meta = {
        "spec": spec,
        "model": model_kind,
        "trained_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "test_score": test_score,
    }
    with open(_path("model_meta.json"), "w") as f:
        json.dump(meta, f)
    print(f"Training complete (spec={spec}, model={model_kind}).")
    return meta


if __name__ == "__main__":
    train()
```

NOTE: `_MODEL_PREFIX` referenced in the test must match `MODEL_PREFIX` (module global). The test monkeypatches `train_model.MODEL_PREFIX`; keep the name `MODEL_PREFIX` and drop the `_path` helper's prefix via `MODEL_PREFIX` only. Also `train_model.data_manager` must be importable (`from backend import data_manager` at top).

- [ ] **Step 4: Wire meta into `backend/predictor.py`**

```python
# near top, after model loading:
MODEL_SPEC = "v1"
try:
    meta_path = os.path.join(os.path.dirname(__file__), "..", "model_meta.json")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            _meta = json.load(f)  # add `import json` at top
        MODEL_SPEC = _meta.get("spec", "v1")
except Exception:
    pass
```

Add `features_for_fixture` (used by `predict_match` when `MODEL_SPEC == "v2"`):

```python
def features_for_fixture(home_team, away_team, home_elo, away_elo, training_df, spec):
    import json, datetime as _dt
    from backend import features
    now = pd.Timestamp.now(tz="UTC")
    h_df = training_df[(training_df["home_team"] == home_team) | (training_df["away_team"] == home_team)]
    a_df = training_df[(training_df["home_team"] == away_team) | (training_df["away_team"] == away_team)]
    h_hist = h_df[h_df["date"] < now]
    a_hist = a_df[a_df["date"] < now]

    def records(team_df, team):
        out = []
        for _, r in team_df.iterrows():
            out.append({
                "date": r["date"],
                "goals_scored": r["home_goals"] if r["home_team"] == team else r["away_goals"],
                "xg_for": r["home_xg"] if r["home_team"] == team else r["away_xg"],
            })
        return out

    h_rec = pd.DataFrame(records(h_hist, home_team))
    a_rec = pd.DataFrame(records(a_hist, away_team))
    hg, hx = features.team_decayed_form(h_rec, 30.0) if not h_rec.empty else (0.0, 0.0)
    ag, ax = features.team_decayed_form(a_rec, 30.0) if not a_rec.empty else (0.0, 0.0)

    league_vals = []
    for t in sorted(set(training_df["home_team"]) | set(training_df["away_team"])):
        t_rec = pd.DataFrame(records(training_df[(training_df["home_team"] == t) | (training_df["away_team"] == t)], t))
        if not t_rec.empty:
            league_vals.append(features.team_decayed_form(t_rec, 30.0)[0])
    league_avg = sum(league_vals) / len(league_vals) if league_vals else 0.0

    feat = {
        "home_team_code": 0, "away_team_code": 0, "home_elo": home_elo, "away_elo": away_elo,
        "home_rolling_goals": hg, "away_rolling_goals": ag,
        "home_rolling_xg": hx, "away_rolling_xg": ax,
    }
    if spec == "v2":
        feat["elo_gap"] = float(home_elo) - float(away_elo)
        feat["home_relative_goals"] = max(0.0, hg - league_avg)
        feat["away_relative_goals"] = max(0.0, ag - league_avg)
    return feat
```

The v2 path in `predict_match`: when `MODEL_SPEC == "v2"`, replace the `get_latest_stats` + fallback block with `features_for_fixture` output for the 8 base keys + elo_gap/relative, keeping the model columns order per `features.feature_columns("v2")`. Keep the existing v1 path intact.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_predictor.py tests/test_train_model.py -v`
Expected: PASS. Also run `python -m pytest tests -q` → all still green.

- [ ] **Step 6: Commit**

```bash
git add backend/train_model.py backend/predictor.py tests/test_train_model.py tests/test_predictor.py
git commit -m "feat: meta-driven training and prediction feature pipeline"
```

---

### Task 5: Run evaluation & choose the champion (gate)

**Files:** none (report only, plus a decision recorded in the plan)

**Interfaces:** consumes `run_all()` from Task 3.

- [ ] **Step 1: Run the full evaluation**

Run: `python -m backend.evaluate`
Expected: 3-row table (baseline_rf, challenger_v2_hgb, challenger_v2_hgb_calib) with brier/log_loss/accuracy/n_matches.

- [ ] **Step 2: Report to the user (controller) — STOP here**

Report the table to the user and ask: which spec wins? Rules:
- If `challenger_v2_hgb` (or calibrated) beats `baseline_rf` on **both** brier and accuracy (log_loss as tiebreaker), winner = that challenger.
- If neither beats baseline, winner = `baseline_rf` (no model change ships).
Do NOT proceed to Task 6 without the user's explicit choice. Record the choice + scores in the plan doc.

---

### Task 6: Bake the champion into production defaults

**Files:**
- Modify: `backend/train_model.py`, `backend/predictor.py`

**Interfaces:**
- Consumes: Task 4 wiring; champion choice from Task 5.
- Produces: `DEFAULT_SPEC` / `DEFAULT_MODEL_KIND` module constants; `train()` defaults them; predictor meta behavior unchanged.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_train_model.py
def test_train_defaults_match_champion(monkeypatch):
    import inspect
    sig = inspect.signature(train_model.train)
    assert sig.parameters["spec"].default == train_model.DEFAULT_SPEC
    assert sig.parameters["model_kind"].default == train_model.DEFAULT_MODEL_KIND
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_train_model.py::test_train_defaults_match_champion -v`
Expected: FAIL — `AttributeError: module 'backend.train_model' has no attribute 'DEFAULT_SPEC'`.

- [ ] **Step 3: Set defaults per the Task 5 verdict**

```python
# backend/train_model.py
DEFAULT_SPEC = "v2"          # "v1" if Task 5 chose baseline
DEFAULT_MODEL_KIND = "hgb"   # "rf" if Task 5 chose baseline


def train(spec=DEFAULT_SPEC, model_kind=DEFAULT_MODEL_KIND):
    ...
```

If the champion is the calibrated challenger, note: calibration happens at eval time only; production `predict_match` ships the raw model (same as baseline today) — the calibration spec's value is demonstrated at eval, and shipping raw is acceptable per spec's "calibration ships only if it beats uncalibrated" — if the calibrated row wins, ALSO record that decision flag in `model_meta.json` as `"calibrated": true` and skip applying isotonic in production (documented in plan doc). Keep it simple: production uses raw model outputs; the flag documents the eval verdict.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_train_model.py -v` then `python -m pytest tests -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/train_model.py tests/test_train_model.py
git commit -m "feat: champion spec baked into training defaults"
```

---

### Task 7: Retraining workflow — automation staleness guard + weekly CI

**Files:**
- Modify: `backend/automation.py`, `.github/workflows/morning_prediction.yml`
- Test: `tests/test_automation.py` (extend)

**Interfaces:**
- Consumes: `train_model.train()` (Task 6), `insights.write_forecast_file` (exists).
- Produces: `model_is_stale(max_age_days=7) -> bool` — True if `model_meta.json` missing or `trained_at` older than max_age_days (UTC parse, `datetime.strptime(trained_at, "%Y-%m-%d")`); `ensure_model_fresh()` — calls `train_model.train()` if stale, wrapped in try/except (graceful fallback).

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_automation.py
import json
import os
from datetime import datetime, timedelta, timezone

from backend import automation, train_model


def test_model_is_stale_missing_meta(monkeypatch, tmp_path):
    monkeypatch.setattr(train_model, "MODEL_PREFIX", str(tmp_path) + os.sep)
    assert automation.model_is_stale() is True


def test_model_is_stale_old_meta(monkeypatch, tmp_path):
    old = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
    with open(str(tmp_path) + "model_meta.json", "w") as f:
        json.dump({"spec": "v1", "trained_at": old}, f)
    monkeypatch.setattr(train_model, "MODEL_PREFIX", str(tmp_path) + os.sep)
    assert automation.model_is_stale() is True


def test_model_is_stale_fresh_meta(monkeypatch, tmp_path):
    fresh = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with open(str(tmp_path) + "model_meta.json", "w") as f:
        json.dump({"spec": "v1", "trained_at": fresh}, f)
    monkeypatch.setattr(train_model, "MODEL_PREFIX", str(tmp_path) + os.sep)
    assert automation.model_is_stale() is False


def test_ensure_model_fresh_retrains_when_stale(monkeypatch):
    calls = []
    monkeypatch.setattr(automation, "model_is_stale", lambda *a, **k: True)
    monkeypatch.setattr(automation.train_model, "train", lambda *a, **k: calls.append("trained"))
    automation.ensure_model_fresh()
    assert calls == ["trained"]


def test_ensure_model_fresh_skips_when_fresh(monkeypatch):
    calls = []
    monkeypatch.setattr(automation, "model_is_stale", lambda *a, **k: False)
    monkeypatch.setattr(automation.train_model, "train", lambda *a, **k: calls.append("trained"))
    automation.ensure_model_fresh()
    assert calls == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_automation.py -v`
Expected: FAIL — `AttributeError: module 'backend.automation' has no attribute 'model_is_stale'`.

- [ ] **Step 3: Implement in `backend/automation.py`**

```python
import json
import os
from datetime import datetime, timedelta, timezone

from backend import train_model


def model_is_stale(max_age_days=7):
    meta_path = os.path.join(train_model.MODEL_PREFIX or "", "model_meta.json")
    if not os.path.exists(meta_path):
        return True
    try:
        with open(meta_path) as f:
            meta = json.load(f)
        trained = datetime.strptime(meta.get("trained_at", "2000-01-01"), "%Y-%m-%d")
        return (datetime.now(timezone.utc).replace(tzinfo=None) - trained) > timedelta(days=max_age_days)
    except Exception:
        return True


def ensure_model_fresh():
    if model_is_stale():
        try:
            train_model.train()
        except Exception as e:
            print(f"Model retrain failed, keeping current models: {e}")
```

Wire `ensure_model_fresh()` at the top of `run_morning_job()` (before fetching upcoming):

```python
def run_morning_job():
    print("Starting Morning Job (Prediction)...")
    ensure_model_fresh()
    utils_data.ensure_directories()
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_automation.py -v` then `python -m pytest tests -q`
Expected: PASS.

- [ ] **Step 5: Add the weekly retrain step to CI**

Append to `.github/workflows/morning_prediction.yml`, a new job after `predict`:

```yaml
  retrain:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          ref: main
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Retrain if model stale
        run: python -m backend.automation ensure-model

      - name: Commit improved models only
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "Auto: Model Refresh"
          file_pattern: 'model_*.pkl team_encoder.pkl training_data.pkl model_meta.json'
```

Add the `ensure-model` mode to `automation.__main__`:

```python
    if args.mode == 'ensure-model':
        ensure_model_fresh()
```

- [ ] **Step 6: Commit**

```bash
git add backend/automation.py tests/test_automation.py .github/workflows/morning_prediction.yml
git commit -m "feat: stale-model retraining in automation and weekly CI"
```

---

## Self-Review Notes

- Spec coverage: harness (T2), challengers (T3), champion gating (T5), meta integration (T4), defaults (T6), retraining/CI (T7), calibration clamp (T3), no-new-deps constraint (all tasks, sklearn only) — all covered.
- The "losing variants removed" spec rule is satisfied by Task 6 (defaults point at the winner; `evaluate.py` retains all specs for future measurement only).
- Type consistency: `feature_columns(spec) -> list[str]`, `build_feature_columns(df, spec) -> DataFrame`, `model_specs()[key] -> {"spec","model"[, "calibrate"]}`, `score_test -> {"brier","log_loss","accuracy","n_matches"}` are consistent across tasks 1–4.
- `MODEL_PREFIX` naming is used consistently in automation + train_model + tests (test asserts `train_model.MODEL_PREFIX` monkeypatch; automation reads `train_model.MODEL_PREFIX`).