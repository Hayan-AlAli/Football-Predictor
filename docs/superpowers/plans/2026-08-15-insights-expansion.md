# Insights Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add five insights features to the Football Predictor: season Monte-Carlo forecast, calibration dashboard, team detail pages, head-to-head, and per-fixture feature reveal.

**Architecture:** A new pure-function backend module `backend/insights.py` serves standings/simulation/calibration/profile/H2H math; `predict_match()` exposes its feature values; four new FastAPI endpoints wire them up. Frontend gains two new pages + a team detail page + a `FeatureReveal` component, using hand-rolled SVG charts and the existing almanack design language.

**Tech Stack:** Python 3.10+ (FastAPI, pandas, numpy via pandas, joblib), React 19 + Vite + Tailwind + motion (no new npm deps), pytest + httpx (new, test-only).

## Global Constraints

- Backend imports follow existing convention: `from backend import utils`, `from backend import utils_data` etc. — never relative imports.
- No new runtime Python deps. Only dev/test additions: `pytest`, `httpx` (required by FastAPI TestClient).
- No new npm dependencies. Charts are hand-rolled SVG in `frontend/src/lib/charts.tsx`.
- Vercel serverless: no long-lived processes; the forecast cache must be written by the morning automation job, never by the prod request path except as fallback.
- All new data is computed from real on-disk data (`training_data.pkl`, `data/predictions/*.json`, `data/results/*.json`). No fabricated numbers; empty result archives render as honest empty states.
- Existing endpoints (`/api/teams`, `/api/matches/predictions`, etc.) and their payload shapes must not change.
- Team names normalized with `utils.normalize_team_name` everywhere before matching.
- Frontend pages follow existing patterns: `Press` loading state, `OfflineSlate` with `onRetry`, `EmptyState`, motion variants from `lib/motion`, Tailwind tokens `ink/rubric/paper/ledger`.
- Existing tests: none in repo. New tests live in `tests/test_*.py` and run with `python -m pytest tests -q` from repo root.
- Commit per task; message style matches `git log`: `feat: ...`, `fix: ...`, `test: ...`.
- Dev verification: `python -m backend.server` (FastAPI :8000), `npm run dev` (Vite :5173, proxies /api to 8000).

---

### Task 1: Insights module — standings engine

**Files:**
- Create: `backend/insights.py`
- Create: `tests/test_insights.py`

**Interfaces:**
- Consumes: `backend.utils` (`normalize_team_name`), `backend.utils_data` (`DATA_DIR`, `save_json`, `load_json`), pandas.
- Produces: `season_year_of(ts: pd.Timestamp) -> int`, `build_standings(training_df: pd.DataFrame, season_year: int) -> list[dict]` where each row is `{team, played, wins, draws, losses, gf, ga, gd, points}` sorted by points desc, GD desc, name asc.

- [ ] **Step 1: Add test dependencies**

Modify `requirements.txt` — append:
```
pytest
httpx
```

- [ ] **Step 2: Write the failing tests**

`tests/test_insights.py`:
```python
import pandas as pd
from backend.insights import build_standings, season_year_of


def _df():
    return pd.DataFrame([
        # season 2024-25 (year 2024): dates Aug 2024 – May 2025
        {"date": pd.Timestamp("2024-08-17"), "home_team": "Arsenal", "away_team": "Chelsea",
         "home_goals": 2, "away_goals": 1},
        {"date": pd.Timestamp("2024-08-24"), "home_team": "Arsenal", "away_team": "Liverpool",
         "home_goals": 1, "away_goals": 1},
        {"date": pd.Timestamp("2024-08-31"), "home_team": "Chelsea", "away_team": "Liverpool",
         "home_goals": 0, "away_goals": 3},
        # season 2025-26 (year 2025)
        {"date": pd.Timestamp("2025-08-16"), "home_team": "Arsenal", "away_team": "Chelsea",
         "home_goals": 3, "away_goals": 0},
    ])


def test_season_year_of_august_date():
    assert season_year_of(pd.Timestamp("2024-08-17")) == 2024


def test_season_year_of_may_date():
    assert season_year_of(pd.Timestamp("2025-05-25")) == 2024


def test_build_standings_points_and_goals():
    rows = build_standings(_df(), 2024)
    by_name = {r["team"]: r for r in rows}
    assert by_name["Arsenal"]["points"] == 4          # W + D
    assert by_name["Arsenal"]["played"] == 2
    assert by_name["Arsenal"]["wins"] == 1
    assert by_name["Arsenal"]["draws"] == 1
    assert by_name["Arsenal"]["losses"] == 0
    assert by_name["Arsenal"]["gf"] == 3              # 2 + 1
    assert by_name["Arsenal"]["ga"] == 2              # 1 + 1
    assert by_name["Liverpool"]["points"] == 4
    assert by_name["Liverpool"]["draws"] == 1
    assert by_name["Liverpool"]["wins"] == 1
    assert by_name["Liverpool"]["losses"] == 0
    assert by_name["Chelsea"]["points"] == 0
    assert rows[0]["team"] in ("Arsenal", "Liverpool")  # 4 pts, tied — GD breaks


def test_build_standings_filters_season():
    rows = build_standings(_df(), 2025)
    assert len(rows) == 2
    by_name = {r["team"]: r for r in rows}
    assert by_name["Arsenal"]["played"] == 1
    assert by_name["Arsenal"]["points"] == 3
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_insights.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.insights'`

- [ ] **Step 4: Write minimal implementation**

`backend/insights.py`:
```python
import os
from datetime import datetime, timezone

import pandas as pd

from backend import utils_data
from backend import utils

FORECAST_DIR = os.path.join(utils_data.DATA_DIR, "forecast")


def season_year_of(ts):
    return ts.year if ts.month >= 8 else ts.year - 1


def _season_col(df):
    return df["date"].dt.year - (df["date"].dt.month < 8).astype(int)


def build_standings(training_df, season_year):
    df = training_df[_season_col(training_df) == season_year]
    if df.empty:
        return []
    teams = sorted(set(df["home_team"]) | set(df["away_team"]))
    rows = []
    for t in teams:
        home = df[df["home_team"] == t]
        away = df[df["away_team"] == t]
        wins = ((home["home_goals"] > home["away_goals"]).sum()
                + (away["away_goals"] > away["home_goals"]).sum())
        draws = ((home["home_goals"] == home["away_goals"]).sum()
                 + (away["away_goals"] == away["home_goals"]).sum())
        gf = int(home["home_goals"].sum() + away["away_goals"].sum())
        ga = int(home["away_goals"].sum() + away["home_goals"].sum())
        rows.append({
            "team": t,
            "played": int(len(home) + len(away)),
            "wins": int(wins),
            "draws": int(draws),
            "losses": int(len(home) + len(away) - wins - draws),
            "gf": gf,
            "ga": ga,
            "gd": gf - ga,
            "points": int(wins * 3 + draws),
        })
    rows.sort(key=lambda r: (-r["points"], -r["gd"], r["team"]))
    return rows
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_insights.py -q`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add requirements.txt backend/insights.py tests/test_insights.py
git commit -m "feat: standings engine for insights module"
```

---

### Task 2: Insights module — Monte Carlo season simulation

**Files:**
- Modify: `backend/insights.py`
- Modify: `tests/test_insights.py`

**Interfaces:**
- Consumes: `predictor.predict_match(match_input)` (returns dict with `home_goals`, `away_goals` floats), `data_manager.fetch_upcoming_matches()` (DataFrame with columns `home_team`, `away_team`, `date`, `home_elo`, `away_elo`), `build_standings` from Task 1, `utils.normalize_team_name`.
- Produces:
  - `simulate_season(standings: list[dict], fixture_rows: list[dict], n_sims=10_000, seed=42) -> dict` → `{"projected": [...], "n_sims": n, "fixtures_remaining": len(fixture_rows)}`. Each projected row: `{team, median_position, points_p10, points_p50, points_p90, title_odds, top4_odds, top6_odds, relegation_odds, position_odds}` where `position_odds` keys are `"1"`, `"2-4"`, `"5-6"`, `"7-17"`, `"18-20"` summing to 1.
  - `generate_forecast(n_sims=10_000, seed=42) -> dict | None` → full payload `{generated, season_year, n_sims, season_complete, stale?, standings, projected, fixtures_remaining}`; `None` only on total failure (no fixtures, no stale cache, no training data).
  - `write_forecast_file(forecast=None, out_dir=None) -> str | None`
- `fixture_rows` (as passed to `simulate_season`): `{"home": str, "away": str, "home_elo": num, "away_elo": num}`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_insights.py`:
```python
from backend.insights import generate_forecast, simulate_season, write_forecast_file
from backend import utils_data

STANDINGS = [
    {"team": "Arsenal", "played": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0, "gd": 0, "points": 0},
    {"team": "Chelsea", "played": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0, "gd": 0, "points": 0},
]


def test_simulate_season_is_deterministic():
    fixtures = [
        {"home": "Arsenal", "away": "Chelsea", "home_elo": 1950, "away_elo": 1800},
    ]
    a = simulate_season(STANDINGS, fixtures, n_sims=2000, seed=42)
    b = simulate_season(STANDINGS, fixtures, n_sims=2000, seed=42)
    assert a["projected"] == b["projected"]
    assert a["n_sims"] == 2000
    assert a["fixtures_remaining"] == 1


def test_simulate_season_favorite_wins_title_often():
    fixtures = [
        {"home": "Arsenal", "away": "Chelsea", "home_elo": 2050, "away_elo": 1500},
    ]
    res = simulate_season(STANDINGS, fixtures, n_sims=2000, seed=7)["projected"]
    by = {r["team"]: r for r in res}
    assert by["Arsenal"]["title_odds"] > 0.9
    assert by["Chelsea"]["title_odds"] < 0.1
    assert abs(by["Arsenal"]["title_odds"] + by["Chelsea"]["title_odds"] - 1.0) < 0.01


def test_simulate_season_odds_and_percentiles_sane():
    fixtures = [
        {"home": "Arsenal", "away": "Chelsea", "home_elo": 2000, "away_elo": 1600},
        {"home": "Chelsea", "away": "Arsenal", "home_elo": 1600, "away_elo": 2000},
    ]
    res = simulate_season(STANDINGS, fixtures, n_sims=2000, seed=11)["projected"]
    for r in res:
        assert r["points_p10"] <= r["points_p50"] <= r["points_p90"]
        assert sum(r["position_odds"].values()) == 1.0
        assert 0.0 <= r["relegation_odds"] <= 1.0
    by = {r["team"]: r for r in res}
    assert by["Arsenal"]["relegation_odds"] < 0.05
    assert by["Arsenal"]["points_p50"] > by["Chelsea"]["points_p50"]


def test_generate_forecast_returns_payload():
    res = generate_forecast()
    assert res is not None
    assert isinstance(res["standings"], list)
    assert isinstance(res["projected"], list)
    assert res["n_sims"] > 0


def test_write_forecast_file_roundtrip(tmp_path):
    payload = {"generated": "2026-08-15", "season_year": 2026, "n_sims": 10,
               "season_complete": False, "standings": [], "projected": [],
               "fixtures_remaining": 0}
    path = write_forecast_file(forecast=payload, out_dir=str(tmp_path))
    assert path is not None
    loaded = utils_data.load_json(path)
    assert loaded == payload
```

Note: `test_generate_forecast_returns_payload` exercises the real data path — it may hit the network (ESPN fixtures). If the network is unavailable, the implementation must still return a payload (standings from training data + empty projected list). Do not mock it away; this is the integration guarantee.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_insights.py -q`
Expected: FAIL — `simulate_season` / `generate_forecast` / `write_forecast_file` not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `backend/insights.py`:
```python
import numpy as np

from backend import data_manager
from backend import predictor


def _poisson_sims(home_lambda, away_lambda, n_sims, seed):
    rng = np.random.default_rng(seed)
    return rng.poisson(home_lambda, size=n_sims), rng.poisson(away_lambda, size=n_sims)


def simulate_season(standings, fixture_rows, n_sims=10000, seed=42):
    rows = []
    for f in fixture_rows:
        pred = predictor.predict_match({
            "home_team": utils.normalize_team_name(f["home"]),
            "away_team": utils.normalize_team_name(f["away"]),
            "home_elo": f["home_elo"],
            "away_elo": f["away_elo"],
        })
        rows.append((
            utils.normalize_team_name(f["home"]),
            utils.normalize_team_name(f["away"]),
            max(float(pred.get("home_goals") or 0.0), 0.0),
            max(float(pred.get("away_goals") or 0.0), 0.0),
        ))

    team_names = sorted({r["team"] for r in standings}
                        | {h for h, _, _, _ in rows}
                        | {a for _, a, _, _ in rows})
    points = {t: np.zeros(n_sims) for t in team_names}

    for idx, (home, away, hl, al) in enumerate(rows):
        if hl <= 0 and al <= 0:
            continue
        hg, ag = _poisson_sims(hl, al, n_sims, seed + 7919 * (idx + 1))
        pts_h = np.where(hg > ag, 3.0, np.where(hg == ag, 1.0, 0.0))
        pts_a = np.where(ag > hg, 3.0, np.where(hg == ag, 1.0, 0.0))
        points[home] += pts_h
        points[away] += pts_a

    mat = np.vstack([points[t] for t in team_names])          # (n_teams, n_sims)
    order = np.lexsort((np.array(team_names), -mat))          # rank: points desc, name asc
    positions = np.empty_like(order, dtype=int)
    for i in range(n_sims):
        positions[order[:, i], i] = np.arange(len(team_names))

    projected = []
    for i, t in enumerate(team_names):
        pos = positions[i] + 1
        pts = mat[i]
        title_odds = float(np.mean(pos == 1))
        top4_part = float(np.mean((pos >= 2) & (pos <= 4)))
        top6_part = float(np.mean((pos >= 5) & (pos <= 6)))
        position_odds = {
            "1": title_odds,
            "2-4": top4_part,
            "5-6": top6_part,
            "7-17": float(np.mean((pos >= 7) & (pos <= 17))),
            "18-20": float(np.mean(pos >= 18)),
        }
        projected.append({
            "team": t,
            "median_position": int(np.median(pos)),
            "points_p10": round(float(np.percentile(pts, 10)), 1),
            "points_p50": round(float(np.percentile(pts, 50)), 1),
            "points_p90": round(float(np.percentile(pts, 90)), 1),
            "title_odds": round(title_odds, 4),
            "top4_odds": round(title_odds + top4_part, 4),
            "top6_odds": round(title_odds + top4_part + top6_part, 4),
            "relegation_odds": round(position_odds["18-20"], 4),
            "position_odds": {k: round(v, 4) for k, v in position_odds.items()},
        })
    projected.sort(key=lambda r: (r["median_position"], -r["points_p50"]))
    return {"projected": projected, "n_sims": n_sims, "fixtures_remaining": len(rows)}


def generate_forecast(n_sims=10000, seed=42):
    today = datetime.now(timezone.utc)
    today_str = today.strftime("%Y-%m-%d")
    season_year = None
    fixtures = []

    upcoming = data_manager.fetch_upcoming_matches()
    if upcoming is not None and not upcoming.empty:
        season_year = season_year_of(upcoming.iloc[0]["date"])
        for _, row in upcoming.iterrows():
            date_str = row["date"].strftime("%Y-%m-%d")
            if date_str >= today_str:
                fixtures.append({
                    "home": row["home_team"],
                    "away": row["away_team"],
                    "home_elo": float(row.get("home_elo") or 1500),
                    "away_elo": float(row.get("away_elo") or 1500),
                })

    df = predictor.training_df
    standings = []
    if df is not None:
        standings = build_standings(df, season_year) if season_year is not None else []

    if season_year is None and df is not None and not df.empty:
        season_year = int(df["date"].dt.year.max())

    if not fixtures:
        if standings:
            return {
                "generated": today_str,
                "season_year": season_year,
                "n_sims": n_sims,
                "season_complete": True,
                "standings": standings,
                "projected": [],
                "fixtures_remaining": 0,
            }
        stale = _latest_forecast()
        if stale:
            stale["stale"] = stale.get("generated", "unknown")
            return stale
        return None

    sim = simulate_season(standings, fixtures, n_sims=n_sims, seed=seed)
    return {
        "generated": today_str,
        "season_year": season_year,
        "n_sims": sim["n_sims"],
        "season_complete": False,
        "standings": standings,
        "projected": sim["projected"],
        "fixtures_remaining": sim["fixtures_remaining"],
    }


def _latest_forecast():
    if not os.path.isdir(FORECAST_DIR):
        return None
    files = sorted(f for f in os.listdir(FORECAST_DIR) if f.endswith(".json"))
    if not files:
        return None
    return utils_data.load_json(os.path.join(FORECAST_DIR, files[-1]))


def write_forecast_file(forecast=None, out_dir=None):
    forecast = forecast or generate_forecast()
    if not forecast:
        return None
    dir_path = out_dir or FORECAST_DIR
    os.makedirs(dir_path, exist_ok=True)
    path = os.path.join(dir_path, f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json")
    utils_data.save_json(forecast, path)
    return path
```

`_poisson_sims` re-seeds per fixture (seed offset by fixture index) so fixture ordering cannot change outcomes; overall determinism comes from `seed`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_insights.py -q`
Expected: PASS (10 passed). `test_generate_forecast_returns_payload` passes with network up or down.

- [ ] **Step 5: Commit**

```bash
git add backend/insights.py tests/test_insights.py
git commit -m "feat: Monte Carlo season simulation with odds and points ranges"
```

---

### Task 3: Insights module — calibration math

**Files:**
- Modify: `backend/insights.py`
- Modify: `tests/test_insights.py`

**Interfaces:**
- Consumes: `utils_data.load_json`, prediction files `data/predictions/<date>.json` (shape: `[{id, date, home_team, away_team, prediction: {prob_home, prob_draw, prob_away, winner, ...}}]`), result files `data/results/<date>.json` (shape: `[{match: {...}, actual: {home_goals, away_goals, winner}, status: "CORRECT"|"INCORRECT"|"PENDING"}]`).
- Produces: `compute_calibration(predictions_dir=None, results_dir=None) -> dict` → `{entries, brier, accuracy, bins, rolling}`:
  - `entries`: count of decided (CORRECT/INCORRECT with actual) entries
  - `brier`: `None` if 0 entries; else mean of `(1 - p)^2` when correct, `p^2` when wrong, where `p` is the probability the model assigned to the outcome it called
  - `accuracy`: `None` if 0 entries; else `correct / entries`
  - `bins`: list of `{label, count, predicted, actual}` for buckets `0-0.35`, `0.35-0.45`, `0.45-0.55`, `0.55-0.65`, `0.65-0.75`, `0.75-1` (only buckets with count > 0)
  - `rolling`: list of `{gameweek, decided, correct, accuracy}` chunking entries by date order in groups of 10 (same `(idx // 10) + 1` convention as `server.py` `/api/matches/all`)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_insights.py`:
```python
import json
from backend.insights import compute_calibration


def _write_cal_fixture(tmp_path, pred_dates, results_dates):
    pred_dir = tmp_path / "predictions"
    res_dir = tmp_path / "results"
    pred_dir.mkdir()
    res_dir.mkdir()
    for d in pred_dates:
        (pred_dir / f"{d}.json").write_text(json.dumps(pred_dates[d]))
    for d in results_dates:
        (res_dir / f"{d}.json").write_text(json.dumps(results_dates[d]))
    return str(pred_dir), str(res_dir)


def test_calibration_hand_computed_brier():
    pred_dates = {
        "2026-01-03": [{"date": "2026-01-03", "home_team": "Arsenal", "away_team": "Chelsea",
                        "prediction": {"prob_home": 0.8, "prob_draw": 0.1, "prob_away": 0.1, "winner": "Arsenal"}}],
        "2026-01-17": [{"date": "2026-01-17", "home_team": "Liverpool", "away_team": "Everton",
                        "prediction": {"prob_home": 0.6, "prob_draw": 0.2, "prob_away": 0.2, "winner": "Liverpool"}}],
    }
    results_dates = {
        "2026-01-03": [{"match": pred_dates["2026-01-03"][0],
                        "actual": {"home_goals": 2, "away_goals": 1, "winner": "Arsenal"},
                        "status": "CORRECT"}],
        "2026-01-17": [{"match": pred_dates["2026-01-17"][0],
                        "actual": {"home_goals": 1, "away_goals": 1, "winner": "Draw"},
                        "status": "INCORRECT"}],
    }
    pred_dir, res_dir = _write_cal_fixture(tmp_path, pred_dates, results_dates)
    res = compute_calibration(pred_dir, res_dir)
    assert res["entries"] == 2
    assert res["accuracy"] == 0.5
    assert abs(res["brier"] - (0.04 + 0.36) / 2) < 1e-9      # (1-0.8)^2 and 0.6^2
    assert len(res["bins"]) == 2
    bin_80 = next(b for b in res["bins"] if b["label"] == "0.75-1")
    assert bin_80["count"] == 1 and bin_80["predicted"] == 0.8 and bin_80["actual"] == 1.0
    assert len(res["rolling"]) == 1
    assert res["rolling"][0] == {"gameweek": 1, "decided": 2, "correct": 1, "accuracy": 0.5}


def test_calibration_empty():
    pred_dir, res_dir = _write_cal_fixture(tmp_path, {}, {})
    res = compute_calibration(pred_dir, res_dir)
    assert res["entries"] == 0 and res["brier"] is None and res["accuracy"] is None
    assert res["bins"] == [] and res["rolling"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_insights.py -q`
Expected: FAIL — `compute_calibration` not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `backend/insights.py`:
```python
BIN_EDGES = [(0.0, 0.35), (0.35, 0.45), (0.45, 0.55), (0.55, 0.65), (0.65, 0.75), (0.75, 1.01)]


def _called_probability(pred, home_team, away_team):
    winner = (pred.get("winner") or "").strip()
    if winner.lower() == "draw":
        return float(pred.get("prob_draw") or 0.0)
    if winner and winner.lower() == home_team.lower():
        return float(pred.get("prob_home") or 0.0)
    if winner and winner.lower() == away_team.lower():
        return float(pred.get("prob_away") or 0.0)
    probs = [pred.get("prob_home", 0.0), pred.get("prob_draw", 0.0), pred.get("prob_away", 0.0)]
    return float(max(probs))


def compute_calibration(predictions_dir=None, results_dir=None):
    res_dir = results_dir or utils_data.RESULTS_DIR

    entries = []
    if os.path.isdir(res_dir):
        for fname in sorted(os.listdir(res_dir)):
            if not fname.endswith(".json"):
                continue
            payload = utils_data.load_json(os.path.join(res_dir, fname)) or []
            for entry in payload:
                if entry.get("status") not in ("CORRECT", "INCORRECT"):
                    continue
                if not entry.get("actual"):
                    continue
                match = entry.get("match") or {}
                pred = match.get("prediction") or {}
                if not pred.get("prob_home"):
                    continue
                p = _called_probability(pred, match.get("home_team", ""), match.get("away_team", ""))
                entries.append({
                    "date": match.get("date") or fname.replace(".json", ""),
                    "p": p,
                    "correct": entry["status"] == "CORRECT",
                })

    n = len(entries)
    if n == 0:
        return {"entries": 0, "brier": None, "accuracy": None, "bins": [], "rolling": []}

    brier = sum((1 - e["p"]) ** 2 if e["correct"] else e["p"] ** 2 for e in entries) / n
    correct = sum(1 for e in entries if e["correct"])

    bins = []
    for lo, hi in BIN_EDGES:
        group = [e for e in entries if lo <= e["p"] < hi]
        if not group:
            continue
        label = "0-0.35" if lo == 0.0 else ("0.75-1" if hi >= 1.01 else f"{lo:.2f}-{hi:.2f}")
        bins.append({
            "label": label,
            "count": len(group),
            "predicted": round(sum(e["p"] for e in group) / len(group), 3),
            "actual": round(sum(1 for e in group if e["correct"]) / len(group), 3),
        })

    ordered = sorted(entries, key=lambda e: e["date"])
    rolling = []
    for i in range(0, n, 10):
        chunk = ordered[i:i + 10]
        decided = len(chunk)
        c = sum(1 for e in chunk if e["correct"])
        rolling.append({
            "gameweek": (i // 10) + 1,
            "decided": decided,
            "correct": c,
            "accuracy": round(c / decided, 3),
        })

    return {
        "entries": n,
        "brier": round(brier, 4),
        "accuracy": round(correct / n, 4),
        "bins": bins,
        "rolling": rolling,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_insights.py -q`
Expected: PASS (12 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/insights.py tests/test_insights.py
git commit -m "feat: calibration math — Brier score, bins, rolling accuracy"
```

---

### Task 4: Insights module — team profile and head-to-head

**Files:**
- Modify: `backend/insights.py`
- Modify: `tests/test_insights.py`

**Interfaces:**
- Consumes: `utils.normalize_team_name`, `season_year_of`.
- Produces:
  - `team_profile(training_df, team_name) -> dict | None` → `{team, seasons, form, elo_history}`:
    - `team`: canonical name (from df)
    - `seasons`: list of `{season_year, played, wins, draws, losses, gf, ga, points}` per season, newest first; only seasons where the team has matches
    - `form`: last 6 played matches, oldest→newest: `{date, result: "W"|"D"|"L", home_team, away_team, home_goals, away_goals}` where `result` is from the team's perspective
    - `elo_history`: ascending by date, `{date, elo}` — the team's Elo on each of its match dates (home Elo when at home, away Elo when away), deduplicated (first per date)
  - `head_to_head(training_df, team_a, team_b) -> dict | None` → `{team_a, team_b, summary, meetings}`:
    - `summary`: `{meetings, team_a_wins, draws, team_b_wins, team_a_for, team_a_against}`
    - `meetings`: newest first, `{date, home_team, away_team, home_goals, away_goals, winner}`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_insights.py`:
```python
from backend.insights import head_to_head, team_profile

H2H_DF = pd.DataFrame([
    {"date": pd.Timestamp("2024-08-17"), "home_team": "Arsenal", "away_team": "Chelsea",
     "home_goals": 2, "away_goals": 1, "home_elo": 1900, "away_elo": 1800},
    {"date": "2025-01-04", "home_team": "Chelsea", "away_team": "Arsenal",
     "home_goals": 0, "away_goals": 0, "home_elo": 1810, "away_elo": 1910},
    {"date": "2025-05-03", "home_team": "Chelsea", "away_team": "Arsenal",
     "home_goals": 2, "away_goals": 3, "home_elo": 1850, "away_elo": 1930},
    # May 2025 still belongs to season year 2024 (2024-25)
    {"date": "2025-08-16", "home_team": "Arsenal", "away_team": "Chelsea",
     "home_goals": 1, "away_goals": 1, "home_elo": 1950, "away_elo": 1860},
    {"date": "2025-09-13", "home_team": "Arsenal", "away_team": "Everton",
     "home_goals": 4, "away_goals": 0, "home_elo": 1960, "away_elo": 1700},
])


def test_team_profile_seasons_and_form():
    p = team_profile(H2H_DF, "Arsenal")
    assert p is not None
    assert p["team"] == "Arsenal"
    seasons = {s["season_year"]: s for s in p["seasons"]}
    assert seasons[2024]["points"] == 7              # W, D, W
    assert seasons[2024]["played"] == 3
    assert seasons[2025]["points"] == 4              # D, W
    assert seasons[2025]["gf"] == 5
    assert p["seasons"][0]["season_year"] == 2025    # newest first
    form = p["form"]
    assert [f["result"] for f in form] == ["W", "D", "W", "D", "W"]
    assert form[0]["date"] < form[-1]["date"]        # oldest → newest
    assert len(form) == 5
    elo = p["elo_history"]
    assert elo[0] == {"date": "2024-08-17", "elo": 1900}
    assert elo[-1]["elo"] == 1960


def test_team_profile_unknown_team():
    assert team_profile(H2H_DF, "Norwich City") is None


def test_head_to_head_summary_and_meetings():
    h = head_to_head(H2H_DF, "Arsenal", "Chelsea")
    assert h is not None
    assert h["summary"]["meetings"] == 4
    assert h["summary"]["team_a_wins"] == 2
    assert h["summary"]["draws"] == 2
    assert h["summary"]["team_b_wins"] == 0
    assert h["summary"]["team_a_for"] == 6
    assert h["summary"]["team_a_against"] == 4
    assert h["meetings"][0]["date"] >= h["meetings"][-1]["date"]   # newest first
    assert h["meetings"][0]["winner"] == "Draw"


def test_head_to_head_unknown_pair():
    assert head_to_head(H2H_DF, "Arsenal", "Norwich City") is None
```

Note: `H2H_DF` mixes `pd.Timestamp` and `str` dates — normalize all with `pd.to_datetime` inside the implementation.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_insights.py -q`
Expected: FAIL — `team_profile` / `head_to_head` not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `backend/insights.py`:
```python
def _norm_df(df):
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out["home_team"] = out["home_team"].apply(utils.normalize_team_name)
    out["away_team"] = out["away_team"].apply(utils.normalize_team_name)
    out["season_year"] = _season_col(out)
    return out


def _canonical_name(df, norm):
    for c in df["home_team"]:
        if c == norm:
            return c
    for c in df["away_team"]:
        if c == norm:
            return c
    return norm


def team_profile(training_df, team_name):
    df = _norm_df(training_df)
    norm = utils.normalize_team_name(team_name)
    involved = df[(df["home_team"] == norm) | (df["away_team"] == norm)]
    if involved.empty:
        return None
    name = _canonical_name(df, norm)

    seasons = []
    for sy in sorted(involved["season_year"].unique(), reverse=True):
        sdf = involved[involved["season_year"] == sy]
        wins = draws = losses = 0
        gf = ga = 0
        for _, r in sdf.iterrows():
            if r["home_team"] == norm:
                scored, conceded = r["home_goals"], r["away_goals"]
            else:
                scored, conceded = r["away_goals"], r["home_goals"]
            gf += int(scored)
            ga += int(conceded)
            if scored > conceded:
                wins += 1
            elif scored == conceded:
                draws += 1
            else:
                losses += 1
        seasons.append({
            "season_year": int(sy),
            "played": len(sdf),
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "gf": gf,
            "ga": ga,
            "points": wins * 3 + draws,
        })

    form = []
    for _, r in involved.sort_values("date").iterrows():
        if r["home_team"] == norm:
            scored, conceded = r["home_goals"], r["away_goals"]
        else:
            scored, conceded = r["away_goals"], r["home_goals"]
        result = "W" if scored > conceded else ("D" if scored == conceded else "L")
        form.append({
            "date": r["date"].strftime("%Y-%m-%d"),
            "result": result,
            "home_team": r["home_team"],
            "away_team": r["away_team"],
            "home_goals": int(r["home_goals"]),
            "away_goals": int(r["away_goals"]),
        })
    form = form[-6:]

    elo_history = []
    seen = set()
    for _, r in involved.sort_values("date").iterrows():
        d = r["date"].strftime("%Y-%m-%d")
        if d in seen:
            continue
        seen.add(d)
        elo = r["home_elo"] if r["home_team"] == norm else r["away_elo"]
        elo_history.append({"date": d, "elo": int(float(elo))})

    return {"team": name, "seasons": seasons, "form": form, "elo_history": elo_history}


def head_to_head(training_df, team_a, team_b):
    df = _norm_df(training_df)
    a = utils.normalize_team_name(team_a)
    b = utils.normalize_team_name(team_b)
    if a == b:
        return None
    meetings = df[
        ((df["home_team"] == a) & (df["away_team"] == b))
        | ((df["home_team"] == b) & (df["away_team"] == a))
    ]
    if meetings.empty:
        return None

    a_wins = draws = b_wins = 0
    a_for = a_against = 0
    rows = []
    for _, r in meetings.sort_values("date", ascending=False).iterrows():
        if r["home_team"] == a:
            a_score, b_score = r["home_goals"], r["away_goals"]
        else:
            b_score, a_score = r["home_goals"], r["away_goals"]
        a_for += int(a_score)
        a_against += int(b_score)
        if a_score > b_score:
            a_wins += 1
            winner = a
        elif a_score == b_score:
            draws += 1
            winner = "Draw"
        else:
            b_wins += 1
            winner = b
        rows.append({
            "date": r["date"].strftime("%Y-%m-%d"),
            "home_team": r["home_team"],
            "away_team": r["away_team"],
            "home_goals": int(r["home_goals"]),
            "away_goals": int(r["away_goals"]),
            "winner": winner,
        })

    return {
        "team_a": _canonical_name(df, a),
        "team_b": _canonical_name(df, b),
        "summary": {
            "meetings": len(rows),
            "team_a_wins": a_wins,
            "draws": draws,
            "team_b_wins": b_wins,
            "team_a_for": a_for,
            "team_a_against": a_against,
        },
        "meetings": rows,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_insights.py -q`
Expected: PASS (16 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/insights.py tests/test_insights.py
git commit -m "feat: team profiles and head-to-head records"
```

---

### Task 5: Expose model features in predict_match

**Files:**
- Modify: `backend/predictor.py` (the `features_dict` → response section, ~lines 216-257)
- Create: `tests/test_predictor.py`

**Interfaces:**
- Consumes: existing module state (`model_home`, `model_away`, `encoder`, `training_df`).
- Produces: `predict_match()` response gains `"features"` key: `{home_elo, away_elo, elo_gap, home_rolling_goals, away_rolling_goals, home_rolling_xg, away_rolling_xg, league_avg_goals, league_avg_xg}` — all numbers. The `features` key is absent only in the random-fallback path.

- [ ] **Step 1: Write the failing test**

`tests/test_predictor.py`:
```python
from backend import predictor


def test_predict_match_returns_features():
    pred = predictor.predict_match({
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "home_elo": 1900,
        "away_elo": 1800,
    })
    assert "features" in pred
    f = pred["features"]
    assert f["home_elo"] == 1900
    assert f["away_elo"] == 1800
    assert f["elo_gap"] == 100
    assert set(f) == {
        "home_elo", "away_elo", "elo_gap",
        "home_rolling_goals", "away_rolling_goals",
        "home_rolling_xg", "away_rolling_xg",
        "league_avg_goals", "league_avg_xg",
    }
    for v in f.values():
        assert isinstance(v, (int, float))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_predictor.py -q`
Expected: FAIL — no `features` key in response.

- [ ] **Step 3: Implement**

In `backend/predictor.py`, modify the success return block of `predict_match` (the one returning `winner`, `score`, etc.) to:

```python
            league_avg_goals = float(training_df['home_rolling_goals'].mean())
            league_avg_xg = float(training_df['home_rolling_xg'].mean())

            X_pred = pd.DataFrame([features_dict])

            pred_home_goals = model_home.predict(X_pred)[0]
            pred_away_goals = model_away.predict(X_pred)[0]

            pred_home_goals = max(0.0, pred_home_goals)
            pred_away_goals = max(0.0, pred_away_goals)

            prob_home, prob_draw, prob_away, best_home, best_draw, best_away, p_best_home, p_best_draw, p_best_away = calculate_probabilities(pred_home_goals, pred_away_goals)

            if p_best_home >= p_best_draw and p_best_home >= p_best_away:
                winner = home_team
                score_home, score_away = best_home
            elif p_best_away >= p_best_home and p_best_away >= p_best_draw:
                winner = away_team
                score_home, score_away = best_away
            else:
                winner = "Draw"
                score_home, score_away = best_draw

            return {
                'winner': winner,
                'score': f"{score_home}-{score_away}",
                'home_goals': pred_home_goals,
                'away_goals': pred_away_goals,
                'home_elo': int(home_elo),
                'away_elo': int(away_elo),
                'prob_home': prob_home,
                'prob_draw': prob_draw,
                'prob_away': prob_away,
                'features': {
                    'home_elo': int(home_elo),
                    'away_elo': int(away_elo),
                    'elo_gap': int(home_elo - away_elo),
                    'home_rolling_goals': round(h_g, 3),
                    'away_rolling_goals': round(a_g, 3),
                    'home_rolling_xg': round(h_xg, 3),
                    'away_rolling_xg': round(a_xg, 3),
                    'league_avg_goals': round(league_avg_goals, 3),
                    'league_avg_xg': round(league_avg_xg, 3),
                }
            }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_predictor.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/predictor.py tests/test_predictor.py
git commit -m "feat: expose model features with per-fixture predictions"
```

---

### Task 6: Backend endpoints

**Files:**
- Modify: `backend/server.py` (add 4 endpoints; import insights)
- Create: `tests/test_endpoints.py`

**Interfaces:**
- Consumes: `insights.generate_forecast()`, `insights.compute_calibration()`, `insights.team_profile(df, name)`, `insights.head_to_head(df, a, b)`, `predictor.training_df`, `server.get_team_info(team_name)` (existing).
- Produces (API contract):
  - `GET /api/season/forecast` → 200 with forecast payload from Task 2; 503 `{"detail": "Forecast unavailable"}` when `generate_forecast()` returns `None`.
  - `GET /api/calibration` → 200 with calibration payload from Task 3.
  - `GET /api/teams/{team_name}` → 200 `{**profile, "team_info": get_team_info(profile["team"])}`; 404 `{"detail": "Team not found"}` when profile is `None`.
  - `GET /api/teams/{team_name}/h2h?vs={other}` → 200 `{**h2h, "team_a_info": ..., "team_b_info": ...}`; 400 `{"detail": "Missing vs parameter"}` when `vs` absent; 404 when `head_to_head` returns `None`.

- [ ] **Step 1: Write the failing tests**

`tests/test_endpoints.py`:
```python
from fastapi.testclient import TestClient

from backend import server, insights


def _client():
    return TestClient(server.app)


def test_season_forecast_ok(monkeypatch):
    payload = {
        "generated": "2026-08-15", "season_year": 2026, "n_sims": 10000,
        "season_complete": False, "standings": [], "projected": [],
        "fixtures_remaining": 0,
    }
    monkeypatch.setattr(insights, "generate_forecast", lambda *a, **k: payload)
    r = _client().get("/api/season/forecast")
    assert r.status_code == 200
    assert r.json()["season_year"] == 2026


def test_season_forecast_unavailable(monkeypatch):
    monkeypatch.setattr(insights, "generate_forecast", lambda *a, **k: None)
    r = _client().get("/api/season/forecast")
    assert r.status_code == 503


def test_calibration_ok(monkeypatch):
    payload = {"entries": 0, "brier": None, "accuracy": None, "bins": [], "rolling": []}
    monkeypatch.setattr(insights, "compute_calibration", lambda *a, **k: payload)
    r = _client().get("/api/calibration")
    assert r.status_code == 200
    assert r.json()["entries"] == 0


def test_team_profile_ok(monkeypatch):
    def fake_profile(df, name):
        return {"team": "Arsenal", "seasons": [], "form": [], "elo_history": []}
    monkeypatch.setattr(insights, "team_profile", fake_profile)
    r = _client().get("/api/teams/Arsenal")
    assert r.status_code == 200
    body = r.json()
    assert body["team"] == "Arsenal"
    assert body["team_info"]["name"] == "Arsenal"


def test_team_profile_404(monkeypatch):
    monkeypatch.setattr(insights, "team_profile", lambda df, name: None)
    r = _client().get("/api/teams/Norwich%20City")
    assert r.status_code == 404


def test_h2h_ok(monkeypatch):
    def fake_h2h(df, a, b):
        return {"team_a": "Arsenal", "team_b": "Chelsea",
                "summary": {"meetings": 1}, "meetings": []}
    monkeypatch.setattr(insights, "head_to_head", fake_h2h)
    r = _client().get("/api/teams/Arsenal/h2h?vs=Chelsea")
    assert r.status_code == 200
    body = r.json()
    assert body["team_a"] == "Arsenal"
    assert body["summary"]["meetings"] == 1


def test_h2h_missing_vs():
    r = _client().get("/api/teams/Arsenal/h2h")
    assert r.status_code == 400


def test_h2h_404(monkeypatch):
    monkeypatch.setattr(insights, "head_to_head", lambda df, a, b: None)
    r = _client().get("/api/teams/Arsenal/h2h?vs=Norwich%20City")
    assert r.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_endpoints.py -q`
Expected: FAIL — endpoints return 404 (no routes).

- [ ] **Step 3: Implement**

In `backend/server.py`:
- add `from backend import insights` to the imports
- add the four routes before `if __name__ == "__main__":`:

```python
@app.get("/api/season/forecast")
async def get_season_forecast():
    forecast = insights.generate_forecast()
    if forecast is None:
        raise HTTPException(status_code=503, detail="Forecast unavailable")
    return forecast


@app.get("/api/calibration")
async def get_calibration():
    return insights.compute_calibration()


@app.get("/api/teams/{team_name}")
async def get_team_profile(team_name: str):
    profile = insights.team_profile(predictor_module_training_df(), team_name)
    if profile is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return {**profile, "team_info": get_team_info(profile["team"])}


@app.get("/api/teams/{team_name}/h2h")
async def get_head_to_head(team_name: str, vs: Optional[str] = None):
    if not vs:
        raise HTTPException(status_code=400, detail="Missing vs parameter")
    h2h = insights.head_to_head(predictor_module_training_df(), team_name, vs)
    if h2h is None:
        raise HTTPException(status_code=404, detail="Head-to-head not found")
    return {
        **h2h,
        "team_a_info": get_team_info(h2h["team_a"]),
        "team_b_info": get_team_info(h2h["team_b"]),
    }
```

Add the helper near the top of `server.py` (after `PREMIER_LEAGUE_TEAMS`):

```python
def predictor_module_training_df():
    try:
        from backend import predictor
        return predictor.training_df
    except Exception:
        return None
```

Note: the endpoint signatures keep `Optional[str] = None` for `vs` — FastAPI treats `vs` as a query parameter automatically.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_endpoints.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Manual smoke check (recommended)**

Run: `python -m backend.server`; then `curl http://localhost:8000/api/season/forecast` and `curl "http://localhost:8000/api/teams/Arsenal/h2h?vs=Chelsea"` — expect JSON, no 500s.

- [ ] **Step 6: Commit**

```bash
git add backend/server.py tests/test_endpoints.py
git commit -m "feat: forecast, calibration, team profile, and head-to-head endpoints"
```

---

### Task 7: Morning automation writes forecast cache; workflow commits it

**Files:**
- Modify: `backend/automation.py` (morning job, ~lines 28-31)
- Modify: `.github/workflows/morning_prediction.yml` (`file_pattern`, ~line 45)
- Create: `tests/test_automation.py`

**Interfaces:**
- Consumes: `insights.write_forecast_file(forecast=None, out_dir=None)` from Task 2.
- Produces: after every successful morning job, a `data/forecast/<date>.json` cache file that the API serves. The workflow commits `data/forecast/*.json`.

- [ ] **Step 1: Write the test**

`tests/test_automation.py`:
```python
import os

from backend import insights


def test_write_forecast_file_writes_cache(tmp_path):
    payload = {
        "generated": "2026-08-15", "season_year": 2026, "n_sims": 10000,
        "season_complete": False, "standings": [], "projected": [],
        "fixtures_remaining": 380,
    }
    out_dir = str(tmp_path / "forecast")
    path = insights.write_forecast_file(forecast=payload, out_dir=out_dir)
    assert path is not None
    assert os.path.exists(path)
```

- [ ] **Step 2: Run test**

Run: `python -m pytest tests/test_automation.py -q`
Expected: PASS

- [ ] **Step 3: Implement**

In `backend/automation.py`:
- add `from backend import insights` to the imports
- at the end of `run_morning_job()`, after `utils_data.save_json(predictions, output_path)`:

```python
    forecast_path = insights.write_forecast_file()
    if forecast_path:
        print(f"Forecast cache written to {forecast_path}")
    print("Morning job completed successfully.")
```

In `.github/workflows/morning_prediction.yml`, change the `Commit and Push` step's `file_pattern`:

```yaml
          file_pattern: 'data/predictions/*.json data/forecast/*.json'
```

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_automation.py -q` — PASS.
Run: `python -m backend.automation morning` locally (network permitting) — confirm the day's forecast file appears under `data/forecast/`.

- [ ] **Step 5: Commit**

```bash
git add backend/automation.py .github/workflows/morning_prediction.yml tests/test_automation.py
git commit -m "feat: cache season forecast in the morning job and CI workflow"
```

---

### Task 8: Frontend plumbing — types, API client, routes, nav

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/matches.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/RunningHead.tsx`

**Interfaces:**
- Consumes: existing `Match`, `Team` types; `fetchAPI<T>` helper (already in matches.ts — replicate its pattern).
- Produces (module constants other tasks import):
  - `types.ts`: `PredictionFeatures`, `StandingsRow`, `ProjectedRow`, `ForecastData`, `CalibrationBin`, `GameweekAccuracy`, `CalibrationData`, `SeasonRow`, `FormEntry`, `EloPoint`, `TeamProfileData`, `Meeting`, `H2HSummary`, `ModelCall`, `H2HData`; `Prediction` gains optional `features?: PredictionFeatures`.
  - `api/matches.ts`: `getForecast(): Promise<ForecastData>`, `getCalibration(): Promise<CalibrationData>`, `getTeamProfile(name: string): Promise<TeamProfileData>`, `getHeadToHead(team: string, vs: string): Promise<H2HData>`.
  - `App.tsx`: routes `/forecast`, `/calibration`, `/teams/:teamName` (lazy-loaded; `Suspense` already wraps all).
  - `RunningHead.tsx`: `SECTIONS` gains `{ to: '/forecast', label: 'FORECAST', folio: () => '5' }` and `{ to: '/calibration', label: 'CALIBRATION', folio: () => '6' }` at the end.

- [ ] **Step 1: Add types**

Append to `frontend/src/types.ts`:
```ts
export interface PredictionFeatures {
  home_elo: number;
  away_elo: number;
  elo_gap: number;
  home_rolling_goals: number;
  away_rolling_goals: number;
  home_rolling_xg: number;
  away_rolling_xg: number;
  league_avg_goals: number;
  league_avg_xg: number;
}

export interface StandingsRow {
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  gf: number;
  ga: number;
  gd: number;
  points: number;
}

export interface ProjectedRow {
  team: string;
  median_position: number;
  points_p10: number;
  points_p50: number;
  points_p90: number;
  title_odds: number;
  top4_odds: number;
  top6_odds: number;
  relegation_odds: number;
  position_odds: Record<string, number>;
}

export interface ForecastData {
  generated: string;
  season_year: number;
  n_sims: number;
  season_complete: boolean;
  stale?: string;
  standings: StandingsRow[];
  projected: ProjectedRow[];
  fixtures_remaining: number;
}

export interface CalibrationBin {
  label: string;
  count: number;
  predicted: number;
  actual: number;
}

export interface GameweekAccuracy {
  gameweek: number;
  decided: number;
  correct: number;
  accuracy: number | null;
}

export interface CalibrationData {
  entries: number;
  brier: number | null;
  accuracy: number | null;
  bins: CalibrationBin[];
  rolling: GameweekAccuracy[];
}

export interface SeasonRow {
  season_year: number;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  gf: number;
  ga: number;
  points: number;
}

export interface FormEntry {
  date: string;
  result: 'W' | 'D' | 'L';
  home_team: string;
  away_team: string;
  home_goals: number;
  away_goals: number;
}

export interface EloPoint {
  date: string;
  elo: number;
}

export interface TeamProfileData {
  team: string;
  team_info: Team;
  seasons: SeasonRow[];
  form: FormEntry[];
  elo_history: EloPoint[];
  upcoming: Match[];
}

export interface Meeting {
  date: string;
  home_team: string;
  away_team: string;
  home_goals: number;
  away_goals: number;
  winner: string;
}

export interface H2HSummary {
  meetings: number;
  team_a_wins: number;
  draws: number;
  team_b_wins: number;
  team_a_for: number;
  team_a_against: number;
}

export interface ModelCall {
  date: string;
  predicted: string;
  actual: string | null;
  status: 'CORRECT' | 'INCORRECT' | null;
}

export interface H2HData {
  team_a: string;
  team_b: string;
  team_a_info: Team;
  team_b_info: Team;
  summary: H2HSummary;
  meetings: Meeting[];
  model_calls: ModelCall[];
}
```

And in the existing `Prediction` interface, add:
```ts
  features?: PredictionFeatures;
```

- [ ] **Step 2: Add API client functions**

Update the imports in `frontend/src/api/matches.ts`:
```ts
import type { CalibrationData, ForecastData, H2HData, Match, ResultEntry, TeamProfileData } from '../types';
```

Append to `frontend/src/api/matches.ts`:
```ts
export async function getForecast(): Promise<ForecastData> {
  return await fetchAPI<ForecastData>('/api/season/forecast');
}

export async function getCalibration(): Promise<CalibrationData> {
  return await fetchAPI<CalibrationData>('/api/calibration');
}

export async function getTeamProfile(name: string): Promise<TeamProfileData> {
  return await fetchAPI<TeamProfileData>(`/api/teams/${encodeURIComponent(name)}`);
}

export async function getHeadToHead(team: string, vs: string): Promise<H2HData> {
  return await fetchAPI<H2HData>(
    `/api/teams/${encodeURIComponent(team)}/h2h?vs=${encodeURIComponent(vs)}`
  );
}
```

- [ ] **Step 3: Add routes**

In `frontend/src/App.tsx`, add lazy imports beside the existing ones:
```ts
const ForecastPage = lazy(() => import('./pages/ForecastPage'));
const CalibrationPage = lazy(() => import('./pages/CalibrationPage'));
const TeamDetailPage = lazy(() => import('./pages/TeamDetailPage'));
```
And inside `<Routes>`, after the `/teams` route:
```tsx
            <Route path="/forecast" element={<ForecastPage />} />
            <Route path="/calibration" element={<CalibrationPage />} />
            <Route path="/teams/:teamName" element={<TeamDetailPage />} />
```

- [ ] **Step 4: Update nav**

In `frontend/src/components/RunningHead.tsx`, replace the `SECTIONS` array:
```ts
const SECTIONS = [
  { to: '/', label: 'MATCHDAY', folio: (gw?: number) => (gw == null ? '1' : gameweekLabel(gw)) },
  { to: '/method', label: 'METHOD', folio: () => '2' },
  { to: '/records', label: 'RECORDS', folio: () => '3' },
  { to: '/teams', label: 'TEAMS INDEX', folio: () => '4' },
  { to: '/forecast', label: 'FORECAST', folio: () => '5' },
  { to: '/calibration', label: 'CALIBRATION', folio: () => '6' },
] as const;
```

- [ ] **Step 5: Verify**

Run: `npm run lint` in `frontend/`. Expected: PASS.
Run: `npm run build` in `frontend/`. Expected: FAILS on `Cannot find module './pages/ForecastPage'` etc. — that is expected until Tasks 11-13 create the pages. Do not block on it; the type/API/nav additions must be lint-clean.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/matches.ts frontend/src/App.tsx frontend/src/components/RunningHead.tsx
git commit -m "feat: frontend plumbing for insights pages"
```

---

### Task 9: SVG chart primitives

**Files:**
- Create: `frontend/src/lib/charts.tsx`

**Interfaces:**
- Consumes: nothing but React; classNames use existing Tailwind tokens.
- Produces (components used by Tasks 11-14):
  - `MeterBar({ value, tone })` — `value: number` 0..1, `tone?: 'ink' | 'rubric'` (default `ink`). A ruled track with a filled bar, like the outcome-odds bars in `LedgerRow`.
  - `SvgLineChart({ points, width = 520, height = 160, strokeClass = 'stroke-rubric' })` — `points: Array<{ x: string; y: number }>` (x is a date/ordinal string). Renders an SVG polyline scaled to min/max of `y` with 10% headroom, `vectorEffect="non-scaling-stroke"`, plus faint min/max reference lines and a rubber-tip dot on the last point.
  - `CalibrationCurve({ bins, width = 520, height = 160 })` — draws the diagonal (perfect calibration) in faint dashed ink and each bin as a point `(predicted, actual)` connected by a rubric polyline, with `0%/100%` axis captions.

- [ ] **Step 1: Create component**

`frontend/src/lib/charts.tsx`:
```tsx
export function MeterBar({ value, tone = 'ink' }: { value: number; tone?: 'ink' | 'rubric' }) {
  const pct = Math.min(100, Math.max(0, value * 100));
  return (
    <span className="inline-block h-2 flex-1 bg-paper-white border border-paper-line overflow-hidden" aria-hidden="true">
      <span
        className={`block h-full ${tone === 'rubric' ? 'bg-rubric' : 'bg-ink'}`}
        style={{ width: `${pct}%` }}
      />
    </span>
  );
}

export function SvgLineChart({
  points,
  width = 520,
  height = 160,
  strokeClass = 'stroke-rubric',
}: {
  points: Array<{ x: string; y: number }>;
  width?: number;
  height?: number;
  strokeClass?: string;
}) {
  if (points.length === 0) return null;
  const ys = points.map((p) => p.y);
  const min = Math.min(...ys);
  const max = Math.max(...ys);
  const span = Math.max(max - min, 1);
  const pad = span * 0.1;
  const lo = min - pad;
  const hi = max + pad;
  const stepX = points.length > 1 ? width / (points.length - 1) : 0;
  const coords = points.map((p, i) => ({
    x: i * stepX,
    y: height - ((p.y - lo) / (hi - lo)) * height,
  }));
  const line = coords.map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' ');
  const first = coords[0];
  const last = coords[coords.length - 1];
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full"
      role="img"
      aria-label="Trend chart"
    >
      <line x1={0} y1={first.y} x2={width} y2={first.y} className="stroke-paper-line" strokeWidth={1} />
      <line x1={0} y1={last.y} x2={width} y2={last.y} className="stroke-paper-line" strokeWidth={1} />
      <path d={line} fill="none" className={strokeClass} strokeWidth={2} vectorEffect="non-scaling-stroke" />
      <circle cx={last.x} cy={last.y} r={3} className="fill-rubric" />
    </svg>
  );
}

export function CalibrationCurve({
  bins,
  width = 520,
  height = 160,
}: {
  bins: Array<{ label: string; count: number; predicted: number; actual: number }>;
  width?: number;
  height?: number;
}) {
  if (bins.length === 0) return null;
  const padX = 24;
  const padY = 16;
  const x = (v: number) => padX + v * (width - padX * 2);
  const y = (v: number) => height - padY - v * (height - padY * 2);
  const diagonal = `M${x(0)},${y(0)} L${x(1)},${y(1)}`;
  const line = bins
    .map((b, i) => `${i === 0 ? 'M' : 'L'}${x(b.predicted).toFixed(1)},${y(b.actual).toFixed(1)}`)
    .join(' ');
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full"
      role="img"
      aria-label="Calibration curve: predicted probability versus actual win rate"
    >
      <path d={diagonal} fill="none" className="stroke-paper-line" strokeWidth={1} strokeDasharray="3 3" />
      <path d={line} fill="none" className="stroke-rubric" strokeWidth={2} vectorEffect="non-scaling-stroke" />
      {bins.map((b) => (
        <circle key={b.label} cx={x(b.predicted)} cy={y(b.actual)} r={3.5} className="fill-ink" />
      ))}
      <text x={padX} y={height - 4} className="fill-ink-faint font-mono text-[9px]">0%</text>
      <text x={x(1) - 10} y={height - 4} className="fill-ink-faint font-mono text-[9px]">100%</text>
      <text x={2} y={y(0) + 3} className="fill-ink-faint font-mono text-[9px]">100%</text>
      <text x={2} y={y(1) - 2} className="fill-ink-faint font-mono text-[9px]">0%</text>
    </svg>
  );
}
```

- [ ] **Step 2: Verify**

Run: `npm run lint` in `frontend/`. Expected: PASS. (Build still fails on missing page modules until Tasks 11-13 — expected.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/charts.tsx
git commit -m "feat: SVG chart primitives for forecast and calibration"
```

---

### Task 10: FeatureReveal component + ledger integration

**Files:**
- Create: `frontend/src/components/FeatureReveal.tsx`
- Modify: `frontend/src/components/LedgerRow.tsx`

**Interfaces:**
- Consumes: `Match` type, `pred.features: PredictionFeatures | undefined`, `teamShort` from `lib/teams`, Tailwind tokens.
- Produces: `FeatureReveal({ match }: { match: Match })` — renders `null` when `match.prediction?.features` is absent; otherwise a ruled table: rows for Elo (home / away / gap), rolling goals (home / away, each vs league average with ▲/▼), rolling xG (home / away, each vs league average with ▲/▼). All copy in the almanack voice.

- [ ] **Step 1: Create component**

`frontend/src/components/FeatureReveal.tsx`:
```tsx
import { teamShort } from '../lib/teams';
import type { Match } from '../types';

const LEAGUE_ROWS: Array<{
  label: string;
  key: 'home_rolling_goals' | 'away_rolling_goals' | 'home_rolling_xg' | 'away_rolling_xg';
  avgKey: 'league_avg_goals' | 'league_avg_xg';
}> = [
  { label: 'Rolling goals — home', key: 'home_rolling_goals', avgKey: 'league_avg_goals' },
  { label: 'Rolling goals — away', key: 'away_rolling_goals', avgKey: 'league_avg_goals' },
  { label: 'Rolling xG — home', key: 'home_rolling_xg', avgKey: 'league_avg_xg' },
  { label: 'Rolling xG — away', key: 'away_rolling_xg', avgKey: 'league_avg_xg' },
];

function Delta({ value, avg }: { value: number; avg: number }) {
  const diff = value - avg;
  const cls = Math.abs(diff) < 0.05 ? 'text-ink-faint' : diff > 0 ? 'text-ledger' : 'text-rubric';
  return (
    <span className={`font-mono text-[0.6875rem] tnum ${cls}`}>
      {Math.abs(diff) < 0.05 ? '≈' : diff > 0 ? '▲' : '▼'} {Math.abs(diff).toFixed(2)}
    </span>
  );
}

/** The model's inputs for one fixture: why it prints what it prints. */
export default function FeatureReveal({ match }: { match: Match }) {
  const f = match.prediction?.features;
  if (!f) return null;
  const home = typeof match.home_team === 'string' ? match.home_team : match.home_team?.name ?? '';
  const away = typeof match.away_team === 'string' ? match.away_team : match.away_team?.name ?? '';

  return (
    <section className="rule-double mt-5 pt-4" aria-label="Model inputs for this fixture">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
          Why the model says so · feature inputs
        </h4>
        <span className="font-serif text-[0.6875rem] italic text-ink-faint">
          live club rating and rolling form, against the league average
        </span>
      </div>

      <div className="mt-3 space-y-1.5">
        <div className="grid grid-cols-[1fr_auto] gap-x-3 sm:grid-cols-[8rem_1fr_1fr_1fr]">
          <span className="font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">Club rating</span>
          <span className="hidden sm:block text-right font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">{teamShort(home)}</span>
          <span className="hidden sm:block text-center font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">gap</span>
          <span className="hidden sm:block text-right font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">{teamShort(away)}</span>
        </div>
        <div className="grid grid-cols-[1fr_auto] items-center gap-x-3 border-t border-paper-line pt-1.5 sm:grid-cols-[8rem_1fr_1fr_1fr]">
          <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-soft">Elo</span>
          <span className="text-right font-mono text-sm text-ink tnum">{f.home_elo}</span>
          <span className="text-center font-mono text-[0.6875rem] text-ink-faint tnum">
            {f.elo_gap >= 0 ? `+${f.elo_gap}` : f.elo_gap}
          </span>
          <span className="text-right font-mono text-sm text-ink tnum">{f.away_elo}</span>
        </div>

        {LEAGUE_ROWS.map((row) => (
          <div
            key={row.key}
            className="grid grid-cols-[1fr_auto] items-center gap-x-3 border-t border-paper-line pt-1.5 sm:grid-cols-[8rem_1fr_1fr_1fr]"
          >
            <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-soft">
              {row.label}
            </span>
            <span className="text-right font-mono text-sm text-ink tnum">{f[row.key].toFixed(2)}</span>
            <span className="text-center font-mono text-[0.6875rem] text-ink-faint tnum">
              avg {f[row.avgKey].toFixed(2)}
            </span>
            <span className="text-right">
              <Delta value={f[row.key]} avg={f[row.avgKey]} />
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Integrate into LedgerRow**

In `frontend/src/components/LedgerRow.tsx`:
- add `import FeatureReveal from './FeatureReveal';`
- inside the `pred` truthy branch (after the `</div>` closing the `grid gap-5 pt-4 sm:grid-cols-3` block, before the `pred && (` footer), insert:

```tsx
                  <FeatureReveal match={match} />
```

- [ ] **Step 3: Verify**

Run: `npm run lint` in `frontend/`. Expected: PASS.
Run: with backend up (`python -m backend.server`) and `npm run dev`, expand a fold-out plate on a fresh fixture — the reveal renders; on a stale prediction (no `features`), no reveal shows and nothing breaks.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/FeatureReveal.tsx frontend/src/components/LedgerRow.tsx
git commit -m "feat: per-fixture feature reveal on matchday plates"
```

---

### Task 11: Forecast page

**Files:**
- Create: `frontend/src/pages/ForecastPage.tsx`

**Interfaces:**
- Consumes: `getForecast()`, `ForecastData`, `MeterBar` (Task 9), `TeamBadge`, `teamInk`/`teamShort` from `lib/teams`, `percent` from `lib/format`, `Press`/`OfflineSlate`/`EmptyState`, motion variants from `lib/motion`.
- Produces: `/forecast` page. Layout:
  - Title band: "The Season Forecast" + serif sub-line.
  - Status handling: `loading` → `Press`; `error` → `OfflineSlate` with `onRetry`; no projected rows but `season_complete` → "The season is complete" + final standings table; no data at all → `EmptyState`.
  - Table of 20 projected teams, one ruled row each: rank + badge + team name, current points chip (from `standings` when found), points `P10–P90` range bar with P50 tick, `median_position`, and three `MeterBar` odds (title / top-4 / relegation) labeled on desktop.
  - Footer note: "10,000 runs · generated <generated> · odds are the model's own probabilities, not betting advice"; when `stale` present: "served from the forecast of <stale>".

- [ ] **Step 1: Create page**

`frontend/src/pages/ForecastPage.tsx`:
```tsx
import { useEffect, useMemo, useState } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import Press from '../components/Press';
import OfflineSlate from '../components/OfflineSlate';
import EmptyState from '../components/EmptyState';
import TeamBadge from '../components/TeamBadge';
import { MeterBar } from '../lib/charts';
import { getForecast } from '../api/matches';
import { teamShort } from '../lib/teams';
import { percent } from '../lib/format';
import { getReducedMotionVariants, headVariants, ledgerVariants, staggerContainer } from '../lib/motion';
import type { ForecastData } from '../types';

type LoadState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; data: ForecastData };

export default function ForecastPage() {
  const [state, setState] = useState<LoadState>({ status: 'loading' });
  const [reloadKey, setReloadKey] = useState(0);
  const reduce = useReducedMotion();
  const headV = reduce ? getReducedMotionVariants(headVariants) : headVariants;
  const staggerV = reduce ? getReducedMotionVariants(staggerContainer) : staggerContainer;
  const rowV = reduce ? getReducedMotionVariants(ledgerVariants) : ledgerVariants;

  useEffect(() => {
    let cancelled = false;
    setState({ status: 'loading' });
    getForecast()
      .then((data) => { if (!cancelled) setState({ status: 'ready', data }); })
      .catch(() => { if (!cancelled) setState({ status: 'error' }); });
    return () => { cancelled = true; };
  }, [reloadKey]);

  const standingsByTeam = useMemo(() => {
    if (state.status !== 'ready') return new Map<string, (typeof state.data.standings)[number]>();
    return new Map(state.data.standings.map((s) => [s.team, s]));
  }, [state]);

  if (state.status === 'loading') return <div className="mx-auto max-w-5xl px-4 pb-4"><Press /></div>;
  if (state.status === 'error') {
    return (
      <div className="mx-auto max-w-5xl px-4 pb-4">
        <OfflineSlate
          message="The forecast could not be computed. Check that the press (FastAPI) is running."
          onRetry={() => setReloadKey((k) => k + 1)}
        />
      </div>
    );
  }

  const { data } = state;
  const rows = data.projected;

  return (
    <div className="mx-auto max-w-5xl px-4 pb-4">
      <motion.div variants={headV} initial="hidden" animate="show" className="pt-8">
        <h1 className="font-sans text-2xl sm:text-3xl font-extrabold uppercase tracking-caps text-ink">
          The Season Forecast
        </h1>
        <p className="mt-1.5 font-serif text-sm italic text-ink-soft sm:text-base">
          The model plays every remaining fixture ten thousand times, and prints the distribution.
        </p>
        {data.stale && (
          <p className="mt-1 font-mono text-[0.6875rem] uppercase tracking-wider-caps text-rubric">
            served from the forecast of {data.stale}
          </p>
        )}
      </motion.div>

      {data.season_complete && rows.length === 0 ? (
        <>
          <h2 className="rule-double mt-8 pt-3 font-mono text-xl font-semibold text-rubric">
            The season is complete
          </h2>
          <p className="mt-2 font-serif text-sm italic text-ink-soft">
            No fixtures remain — here is the final league table as the model saw it.
          </p>
          <div className="mt-6">
            {data.standings.map((s, i) => (
              <div key={s.team} className="grid grid-cols-[2rem_1fr_4rem] items-center gap-x-3 border-t border-paper-line py-3">
                <span className="font-mono text-sm text-ink-faint tnum">{i + 1}</span>
                <span className="flex min-w-0 items-center gap-2 truncate font-sans text-sm font-bold uppercase tracking-caps text-ink">
                  <TeamBadge team={s.team} size="sm" /> {teamShort(s.team)}
                </span>
                <span className="text-right font-mono text-sm text-ink tnum">{s.points}</span>
              </div>
            ))}
          </div>
        </>
      ) : rows.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            title="The forecast has not been printed"
            note="Once the press runs against a new season's fixtures, the season forecast appears here."
          />
        </div>
      ) : (
        <>
          <div className="rule-draw mt-6 flex flex-wrap items-center justify-between gap-2 py-3">
            <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
              Projected final table · {data.n_sims.toLocaleString()} runs
            </span>
            <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
              generated {data.generated}
            </span>
          </div>

          <div className="hidden sm:grid grid-cols-[2.5rem_1fr_10rem_4.5rem_12rem] gap-x-3 px-2 pb-1 pt-3">
            <span className="font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">#</span>
            <span className="font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">Club</span>
            <span className="text-center font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">Points P10–P90</span>
            <span className="text-center font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">Median pos</span>
            <span className="text-right font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">Title · Top-4 · Relegation</span>
          </div>

          <motion.div variants={staggerV} initial="hidden" animate="show" className="pb-8">
            {rows.map((r, i) => {
              const current = standingsByTeam.get(r.team);
              return (
                <motion.div
                  key={r.team}
                  variants={rowV}
                  initial="hidden"
                  animate="show"
                  className="grid grid-cols-[2rem_1fr_auto] items-center gap-x-3 border-t border-paper-line py-3.5 sm:grid-cols-[2.5rem_1fr_10rem_4.5rem_12rem] sm:px-2"
                >
                  <span className="font-mono text-sm text-ink-faint tnum">{i + 1}</span>
                  <span className="flex min-w-0 items-center gap-2">
                    <TeamBadge team={r.team} size="md" />
                    <span className="truncate font-sans text-sm font-bold uppercase tracking-caps text-ink">{teamShort(r.team)}</span>
                    {current && (
                      <span className="hidden sm:inline font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">
                        {current.points} pts · {current.played} played
                      </span>
                    )}
                  </span>
                  <span className="flex w-24 items-center gap-1.5 sm:w-auto sm:flex-1" aria-label={`Points range ${r.points_p10} to ${r.points_p90}`}>
                    <span className="font-mono text-[0.625rem] text-ink-faint tnum">{Math.round(r.points_p10)}</span>
                    <span className="relative h-2 flex-1 bg-paper-white border border-paper-line overflow-hidden">
                      <span className="absolute inset-y-0 left-0 bg-ink/25" style={{ width: `${(r.points_p50 / 90) * 100}%` }} aria-hidden="true" />
                      <span className="absolute top-1/2 h-full w-0.5 -translate-y-1/2 bg-rubric" style={{ left: `${(r.points_p50 / 90) * 100}%` }} aria-hidden="true" />
                    </span>
                    <span className="font-mono text-[0.625rem] text-ink-faint tnum">{Math.round(r.points_p90)}</span>
                  </span>
                  <span className="text-center font-mono text-sm text-ink tnum">{r.median_position}</span>
                  <span className="hidden sm:block">
                    <span className="flex items-center gap-1.5">
                      <span className="w-16 truncate font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">title</span>
                      <MeterBar value={r.title_odds} tone={r.title_odds > 0.2 ? 'rubric' : 'ink'} />
                      <span className="w-9 text-right font-mono text-[0.625rem] text-ink tnum">{percent(r.title_odds)}</span>
                    </span>
                    <span className="mt-1 flex items-center gap-1.5">
                      <span className="w-16 truncate font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">top-4</span>
                      <MeterBar value={r.top4_odds} />
                      <span className="w-9 text-right font-mono text-[0.625rem] text-ink tnum">{percent(r.top4_odds)}</span>
                    </span>
                    <span className="mt-1 flex items-center gap-1.5">
                      <span className="w-16 truncate font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">releg.</span>
                      <MeterBar value={r.relegation_odds} tone={r.relegation_odds > 0.2 ? 'rubric' : 'ink'} />
                      <span className="w-9 text-right font-mono text-[0.625rem] text-ink tnum">{percent(r.relegation_odds)}</span>
                    </span>
                  </span>
                </motion.div>
              );
            })}
          </motion.div>

          <p className="rule-double pt-3 pb-8 font-serif text-xs italic text-ink-faint">
            Odds are the model's own probabilities, not betting advice. The simulation samples scorelines from
            each fixture's expected goals and assumes independence between matches.
          </p>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify**

Run: `npm run lint` and `npm run build` in `frontend/`. Expected: both PASS now (all page modules exist after Task 13 — if Task 13 isn't done yet, build fails only on the missing modules, which is expected).
With backend up, visit `/forecast`: the projection renders; with the network down, the offline state shows.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ForecastPage.tsx
git commit -m "feat: season forecast page with Monte Carlo table"
```

---

### Task 12: Calibration page

**Files:**
- Create: `frontend/src/pages/CalibrationPage.tsx`

**Interfaces:**
- Consumes: `getCalibration()`, `CalibrationData`, `CalibrationCurve` (Task 9), `percent` from `lib/format`, `Press`/`OfflineSlate`/`EmptyState`, motion variants.
- Produces: `/calibration` page. Layout:
  - Title band: "Calibration & the record" + serif sub-line ("When the model says 60%, does it win six in ten?").
  - Stat cards: overall accuracy, Brier score (with a one-line honest gloss: lower is better; a perfect forecaster scores 0), decided entries count.
  - Calibration section: `CalibrationCurve` from `bins` + per-bin count captions.
  - "By matchweek" section: `SvgLineChart` of rolling accuracy (points `{x: "GW n", y: accuracy}`) + per-gameweek chip list.
  - Empty state when `entries === 0`: copy — "No decided verdicts recorded yet. The evening press compares predictions against results; once it has, the calibration ledger fills." No fabricated numbers.

- [ ] **Step 1: Create page**

`frontend/src/pages/CalibrationPage.tsx`:
```tsx
import { useEffect, useState } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import Press from '../components/Press';
import OfflineSlate from '../components/OfflineSlate';
import EmptyState from '../components/EmptyState';
import { CalibrationCurve, SvgLineChart } from '../lib/charts';
import { getCalibration } from '../api/matches';
import { percent } from '../lib/format';
import { getReducedMotionVariants, headVariants } from '../lib/motion';
import type { CalibrationData } from '../types';

type LoadState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; data: CalibrationData };

export default function CalibrationPage() {
  const [state, setState] = useState<LoadState>({ status: 'loading' });
  const [reloadKey, setReloadKey] = useState(0);
  const reduce = useReducedMotion();
  const headV = reduce ? getReducedMotionVariants(headVariants) : headVariants;

  useEffect(() => {
    let cancelled = false;
    setState({ status: 'loading' });
    getCalibration()
      .then((data) => { if (!cancelled) setState({ status: 'ready', data }); })
      .catch(() => { if (!cancelled) setState({ status: 'error' }); });
    return () => { cancelled = true; };
  }, [reloadKey]);

  if (state.status === 'loading') return <div className="mx-auto max-w-5xl px-4 pb-4"><Press /></div>;
  if (state.status === 'error') {
    return (
      <div className="mx-auto max-w-5xl px-4 pb-4">
        <OfflineSlate
          message="The calibration ledger could not be read. Check that the press (FastAPI) is running."
          onRetry={() => setReloadKey((k) => k + 1)}
        />
      </div>
    );
  }

  const { data } = state;

  return (
    <div className="mx-auto max-w-5xl px-4 pb-4">
      <motion.div variants={headV} initial="hidden" animate="show" className="pt-8">
        <h1 className="font-sans text-2xl sm:text-3xl font-extrabold uppercase tracking-caps text-ink">
          Calibration &amp; the record
        </h1>
        <p className="mt-1.5 font-serif text-sm italic text-ink-soft sm:text-base">
          When the model says 60%, does it win six in ten? The record, kept honestly — misses included.
        </p>
      </motion.div>

      {data.entries === 0 ? (
        <div className="mt-8">
          <EmptyState
            title="The calibration ledger is blank"
            note="No decided verdicts recorded yet. The evening press compares predictions against results; once it has, the calibration ledger fills."
          />
        </div>
      ) : (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <div className="plate p-4">
              <h3 className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">Overall accuracy</h3>
              <p className="mt-1 font-mono text-3xl font-semibold text-ink tnum">
                {data.accuracy != null ? percent(data.accuracy) : '—'}
              </p>
              <p className="mt-1 font-serif text-xs italic text-ink-faint">{data.entries} decided verdicts</p>
            </div>
            <div className="plate p-4">
              <h3 className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">Brier score</h3>
              <p className="mt-1 font-mono text-3xl font-semibold text-ink tnum">
                {data.brier != null ? data.brier.toFixed(3) : '—'}
              </p>
              <p className="mt-1 font-serif text-xs italic text-ink-faint">lower is better; a perfect forecaster scores 0</p>
            </div>
            <div className="plate p-4">
              <h3 className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">Honesty note</h3>
              <p className="mt-1 font-serif text-sm italic text-ink-soft">
                This ledger shows every miss. A prediction is only as credible as its record of being wrong.
              </p>
            </div>
          </div>

          {data.bins.length > 0 && (
            <section className="rule-double mt-10 pt-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="font-mono text-xl font-semibold text-rubric">Calibration curve</h2>
                <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
                  predicted probability vs actual win rate
                </span>
              </div>
              <div className="mt-4">
                <CalibrationCurve bins={data.bins} />
              </div>
              <p className="mt-2 font-serif text-xs italic text-ink-faint">
                The dashed line is perfect calibration — on it, 60% predicted wins exactly six in ten.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {data.bins.map((b) => (
                  <span key={b.label} className="font-mono text-[0.625rem] uppercase tracking-widest text-ink-soft">
                    {b.label} · n={b.count} · {percent(b.predicted)} → {percent(b.actual)}
                  </span>
                ))}
              </div>
            </section>
          )}

          {data.rolling.length > 0 && (
            <section className="rule-double mt-10 pt-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="font-mono text-xl font-semibold text-rubric">By matchweek</h2>
                <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
                  decided verdicts per matchweek, rolling
                </span>
              </div>
              <div className="mt-4">
                <SvgLineChart
                  points={data.rolling.map((r) => ({ x: `GW ${r.gameweek}`, y: r.accuracy ?? 0 }))}
                />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {data.rolling.map((r) => (
                  <span key={r.gameweek} className="chip">
                    GW {r.gameweek} · {r.correct}/{r.decided}
                    {r.accuracy != null ? ` · ${percent(r.accuracy)}` : ''}
                  </span>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify**

Run: `npm run lint` and `npm run build` in `frontend/`. Expected: PASS once all pages exist.
With backend up, visit `/calibration`: with no result files yet, the empty state reads honestly; once the evening job has written results, the curve and chart render.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/CalibrationPage.tsx
git commit -m "feat: calibration page with Brier score and curve"
```

---

### Task 13: Team detail page

**Files:**
- Create: `frontend/src/pages/TeamDetailPage.tsx`
- Modify: `frontend/src/pages/TeamsPage.tsx` (make roster rows link to detail pages)

**Interfaces:**
- Consumes: `useParams` from react-router-dom, `getTeamProfile(name)`, `TeamProfileData`, `TeamBadge`, `SvgLineChart`, `FeatureReveal`, `teamShort` from `lib/teams`, `percent`/`printDate` from `lib/format`, `Press`/`OfflineSlate`/`EmptyState`, motion variants.
- Produces: `/teams/:teamName` page:
  - Header: badge (team_info) + club name + current chips (points / position when `standings`-less — use a compact "P W D L" summary from the newest season's row).
  - "The ledger of the club" — season-by-season table: SeasonYear / P / W / D / L / GF / GA / Pts (ruled rows, no motion stagger — 5 rows).
  - "Form — last six" strip: six tiles colored `text-ledger` (W), `text-ink` (D), `text-rubric` (L), each with `teamShort` of the opponent.
  - "Club rating, five seasons" — `SvgLineChart` on `elo_history` points `{x: date, y: elo}` with the current Elo caption.
  - Upcoming fixtures (when `upcoming.length > 0`): rendered as `LedgerRow`-style rows — reuse existing row markup inline (not the component — it expects `Match` with gameweek; upcoming rows lack gameweeks). Simpler: a list of `{date, home, away, score, call}` one-liners with a `FeatureReveal` below each when features exist.
  - Back link: "← The Teams Index" linking to `/teams`.
- `TeamsPage.tsx`: wrap each roster row (the `motion.div` in the map) in a `Link to={`/teams/${encodeURIComponent(club.name)}`}` (import `Link` from `react-router-dom`); keep the letter-anchor behavior.

- [ ] **Step 1: Add links in TeamsPage**

In `frontend/src/pages/TeamsPage.tsx`:
- add `import { Link } from 'react-router-dom';`
- wrap the roster `motion.div` contents: replace the opening `<motion.div key={club.name} ...>` with:

```tsx
                        <motion.div key={club.name} variants={rowV} initial="hidden" animate="show"
                          className="grid grid-cols-[auto_1fr_auto] items-center gap-x-3 border-t border-paper-line py-3.5">
                          <Link to={`/teams/${encodeURIComponent(club.name)}`} className="flex min-w-0 items-center gap-3 no-underline">
                            ...
                          </Link>
                        </motion.div>
```

Keep all existing content inside the `Link` (badge, name, sub-line, ink dot). The link should wrap the badge + text + subtitle; keep the ink-color dot outside the link or inside — either is fine, but the whole row must be clickable.

- [ ] **Step 2: Create the page**

`frontend/src/pages/TeamDetailPage.tsx`:
```tsx
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import Press from '../components/Press';
import OfflineSlate from '../components/OfflineSlate';
import EmptyState from '../components/EmptyState';
import TeamBadge from '../components/TeamBadge';
import FeatureReveal from '../components/FeatureReveal';
import { SvgLineChart } from '../lib/charts';
import { getTeamProfile } from '../api/matches';
import { teamShort } from '../lib/teams';
import { percent } from '../lib/format';
import { getReducedMotionVariants, headVariants } from '../lib/motion';
import type { Match, TeamProfileData } from '../types';

type LoadState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; data: TeamProfileData };

export default function TeamDetailPage() {
  const { teamName = '' } = useParams();
  const [state, setState] = useState<LoadState>({ status: 'loading' });
  const [reloadKey, setReloadKey] = useState(0);
  const reduce = useReducedMotion();
  const headV = reduce ? getReducedMotionVariants(headVariants) : headVariants;

  useEffect(() => {
    let cancelled = false;
    setState({ status: 'loading' });
    getTeamProfile(teamName)
      .then((data) => { if (!cancelled) setState({ status: 'ready', data }); })
      .catch(() => { if (!cancelled) setState({ status: 'error' }); });
    return () => { cancelled = true; };
  }, [teamName, reloadKey]);

  if (state.status === 'loading') return <div className="mx-auto max-w-3xl px-4 pb-4"><Press /></div>;
  if (state.status === 'error') {
    return (
      <div className="mx-auto max-w-3xl px-4 pb-4">
        <OfflineSlate
          message="This club's page could not be set. Check that the press (FastAPI) is running."
          onRetry={() => setReloadKey((k) => k + 1)}
        />
      </div>
    );
  }

  const { data } = state;
  const seasons = data.seasons ?? [];
  const form = data.form ?? [];
  const elo = data.elo_history ?? [];
  const upcoming = data.upcoming ?? [];
  const latest = seasons[0];

  return (
    <div className="mx-auto max-w-3xl px-4 pb-4">
      <motion.div variants={headV} initial="hidden" animate="show" className="pt-8">
        <Link to="/teams" className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-rubric no-underline hover:text-ink">
          ← The Teams Index
        </Link>
        <div className="mt-3 flex items-center gap-3">
          <TeamBadge team={data.team} info={data.team_info} size="lg" />
          <div className="min-w-0">
            <h1 className="truncate font-sans text-2xl sm:text-3xl font-extrabold uppercase tracking-caps text-ink">
              {data.team}
            </h1>
            {latest && (
              <p className="mt-1 font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
                season {latest.season_year} · {latest.played} played · {latest.wins} W · {latest.draws} D · {latest.losses} L · {latest.points} pts
              </p>
            )}
          </div>
        </div>
      </motion.div>

      {seasons.length > 0 && (
        <section className="rule-double mt-8 pt-3">
          <h2 className="font-mono text-xl font-semibold text-rubric">The ledger of the club</h2>
          <div className="mt-3">
            <div className="hidden sm:grid grid-cols-[5rem_1fr_1fr_1fr_1fr_1fr_1fr_3rem] gap-x-2 px-2 pb-1 font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">
              <span>Season</span><span className="text-right">P</span><span className="text-right">W</span>
              <span className="text-right">D</span><span className="text-right">L</span>
              <span className="text-right">GF</span><span className="text-right">GA</span><span className="text-right">Pts</span>
            </div>
            {seasons.map((s) => (
              <div key={s.season_year} className="grid grid-cols-4 items-center gap-x-2 border-t border-paper-line py-2.5 sm:grid-cols-[5rem_1fr_1fr_1fr_1fr_1fr_1fr_3rem] sm:px-2">
                <span className="font-mono text-sm text-ink">{s.season_year}-{String(s.season_year + 1).slice(2)}</span>
                <span className="text-right font-mono text-sm text-ink-soft tnum">{s.played}</span>
                <span className="text-right font-mono text-sm text-ink-soft tnum">{s.wins}</span>
                <span className="text-right font-mono text-sm text-ink-soft tnum">{s.draws}</span>
                <span className="text-right font-mono text-sm text-ink-soft tnum">{s.losses}</span>
                <span className="text-right font-mono text-sm text-ink-soft tnum">{s.gf}</span>
                <span className="text-right font-mono text-sm text-ink-soft tnum">{s.ga}</span>
                <span className="text-right font-mono text-sm font-semibold text-ink tnum">{s.points}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {form.length > 0 && (
        <section className="rule-double mt-10 pt-3">
          <h2 className="font-mono text-xl font-semibold text-rubric">Form — last {form.length}</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {form.map((f, i) => (
              <span key={f.date + i} className={`flex h-9 w-9 items-center justify-center border font-mono text-sm font-semibold ${
                f.result === 'W' ? 'border-ledger text-ledger' : f.result === 'L' ? 'border-rubric text-rubric' : 'border-ink text-ink'
              }`} title={`${f.date} · ${teamShort(f.home_team)} ${f.home_goals}-${f.away_goals} ${teamShort(f.away_team)}`}>
                {f.result}
              </span>
            ))}
          </div>
        </section>
      )}

      {elo.length > 0 && (
        <section className="rule-double mt-10 pt-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="font-mono text-xl font-semibold text-rubric">Club rating</h2>
            <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">
              latest {elo[elo.length - 1].elo}
            </span>
          </div>
          <div className="mt-4">
            <SvgLineChart points={elo.map((e) => ({ x: e.date, y: e.elo }))} />
          </div>
          <p className="mt-2 font-serif text-xs italic text-ink-faint">
            The club's Elo rating before each of its matches, five seasons back.
          </p>
        </section>
      )}

      {upcoming.length > 0 && (
        <section className="rule-double mt-10 pt-3">
          <h2 className="font-mono text-xl font-semibold text-rubric">Fixtures to come</h2>
          <div className="mt-3">
            {upcoming.map((m: Match) => {
              const pred = m.prediction;
              const home = typeof m.home_team === 'string' ? m.home_team : m.home_team?.name ?? '';
              const away = typeof m.away_team === 'string' ? m.away_team : m.away_team?.name ?? '';
              return (
                <article key={m.id} className="border-t border-paper-line py-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-serif text-xs italic text-ink-faint">{printDate(m.date)}</span>
                    <span className="min-w-0 truncate font-sans text-sm font-bold uppercase tracking-caps text-ink">
                      {teamShort(home)} <span className="font-mono font-normal text-ink-faint">vs</span> {teamShort(away)}
                    </span>
                    {pred && (
                      <span className="stamp text-xs">{pred.winner ?? '—'} · {percent(pred.prob_home)}/{percent(pred.prob_draw)}/{percent(pred.prob_away)}</span>
                    )}
                  </div>
                  <FeatureReveal match={m} />
                </article>
              );
            })}
          </div>
        </section>
      )}

      {seasons.length === 0 && form.length === 0 && elo.length === 0 && (
        <div className="mt-8">
          <EmptyState
            title="This page is blank"
            note="No records for this club in the training ledger. It may be a newly promoted side."
          />
        </div>
      )}
    </div>
  );
}
```

Notes:
- `teamShort(home)` / `teamShort(away)` resolve the club names from `m.home_team` / `m.away_team` (which may be strings or Team objects) — resolved explicitly in the map above.
- `printDate` is imported from `lib/format` — it exists (used by `LedgerRow`).

- [ ] **Step 3: Verify**

Run: `npm run lint` and `npm run build` in `frontend/`. Expected: PASS (all modules now exist).
With backend up, visit `/teams`, click a club, and confirm: back link works, seasons table, form strip, Elo chart, and upcoming fixtures render. `/teams/Arsenal` directly also works.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/TeamDetailPage.tsx frontend/src/pages/TeamsPage.tsx
git commit -m "feat: team detail pages and indexed roster links"
```

---

### Task 14: Head-to-head section on the team page

**Files:**
- Modify: `frontend/src/pages/TeamDetailPage.tsx`

**Interfaces:**
- Consumes: `getHeadToHead(team, vs)`, `H2HData`, `teamsFromMatches` fallback not needed — use `/api/teams` via `getTeams` for the opponent picker (import `getTeams` from `api/matches`), `teamShort`, `TeamBadge`.
- Produces: a "Head to head" section on `/teams/:teamName`:
  - Opponent `<select>` populated from `getTeams()` (exclude the current team), defaulting to the first option; changing it fetches `getHeadToHead(team, vs)`.
  - On data: summary line ("X meetings · A W–D–L B · A scored n, conceded m"), then the meetings list rendered as compact ruled rows (`date · home a-b away · winner`).
  - Loading state: small serif italic "setting the fixture…" line. Error state: inline note, not the full-page slate.
  - Fetch is debounced by `vs` change only (auto-cancel stale requests with a cancelled flag).

- [ ] **Step 1: Implement**

In `frontend/src/pages/TeamDetailPage.tsx`, add imports and the section. Add to the imports:

```tsx
import { useCallback } from 'react';
import { getHeadToHead, getTeams } from '../api/matches';
import type { H2HData } from '../types';
```

Add inside the component (before the `return`), state + effects:

```tsx
  const [vsList, setVsList] = useState<string[]>([]);
  const [vs, setVs] = useState<string>('');
  const [h2h, setH2h] = useState<H2HData | null>(null);
  const [h2hLoading, setH2hLoading] = useState(false);
  const [h2hError, setH2hError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getTeams()
      .then((teams) => {
        if (cancelled) return;
        const others = teams.map((t) => t.name).filter((n) => n !== data?.team).sort();
        setVsList(others);
        if (others.length > 0) setVs(others[0]);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [data?.team]);

  useEffect(() => {
    if (!vs) return;
    let cancelled = false;
    setH2hLoading(true);
    setH2hError(false);
    getHeadToHead(data.team, vs)
      .then((res) => { if (!cancelled) setH2h(res); })
      .catch(() => { if (!cancelled) setH2hError(true); })
      .finally(() => { if (!cancelled) setH2hLoading(false); });
    return () => { cancelled = true; };
  }, [data.team, vs]);

  const onVsChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setVs(e.target.value);
  }, []);
```

And the section JSX (insert after the "Fixtures to come" section):

```tsx
      <section className="rule-double mt-10 pt-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="font-mono text-xl font-semibold text-rubric">Head to head</h2>
          <label className="flex items-center gap-2">
            <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">opponent</span>
            <select
              value={vs}
              onChange={onVsChange}
              className="border border-paper-line bg-paper-white px-2 py-1 font-mono text-xs uppercase tracking-wider-caps text-ink"
            >
              {vsList.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
        </div>

        {h2hLoading && <p className="mt-3 font-serif text-xs italic text-ink-faint" role="status">Setting the fixture…</p>}
        {h2hError && !h2hLoading && (
          <p className="mt-3 font-serif text-xs italic text-rubric">This fixture could not be set — try another opponent.</p>
        )}
        {h2h && !h2hLoading && (
          <>
            <p className="mt-3 font-serif text-sm italic text-ink-soft">
              {h2h.summary.meetings} meetings · {teamShort(h2h.team_a)} {h2h.summary.team_a_wins}–{h2h.summary.draws}–{h2h.summary.team_b_wins} {teamShort(h2h.team_b)}
              · {teamShort(h2h.team_a)} scored {h2h.summary.team_a_for}, conceded {h2h.summary.team_a_against}
            </p>
            <div className="mt-3">
              {h2h.meetings.length === 0 ? (
                <p className="font-serif text-xs italic text-ink-faint">No recorded meetings in the training ledger.</p>
              ) : (
                h2h.meetings.map((m) => (
                  <div key={m.date + m.home_team + m.away_team} className="flex flex-wrap items-center justify-between gap-x-3 border-t border-paper-line py-2.5">
                    <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-faint">{m.date}</span>
                    <span className="min-w-0 truncate font-sans text-sm font-bold uppercase tracking-caps text-ink">
                      {teamShort(m.home_team)} <span className="font-mono font-normal text-ink-faint">{m.home_goals}–{m.away_goals}</span> {teamShort(m.away_team)}
                    </span>
                    <span className="font-mono text-[0.6875rem] uppercase tracking-wider-caps text-ink-soft">
                      {m.winner === 'Draw' ? 'draw' : `${teamShort(m.winner)} win`}
                    </span>
                  </div>
                ))
              )}
            </div>
          </>
        )}
      </section>
```

- [ ] **Step 2: Verify**

Run: `npm run lint` and `npm run build` in `frontend/`. Expected: PASS.
With backend up, open a team page: opponent picker populates, switching opponents updates the meetings; unknown/no-meeting opponents show the empty note; network failure shows the inline error.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/TeamDetailPage.tsx
git commit -m "feat: head-to-head fixture picker on team pages"
```

---

### Task 15: Full verification pass

**Files:** none (verification only)

- [ ] **Step 1: Backend test suite**

Run: `python -m pytest tests -q`
Expected: ALL PASS (16 from insights + 1 predictor + 8 endpoints + 1 automation = 26 tests, modulo exact counts).

- [ ] **Step 2: Frontend lint + build**

Run: `npm run lint` in `frontend/` — PASS.
Run: `npm run build` in `frontend/` — PASS (all page modules exist since Task 13).

- [ ] **Step 3: End-to-end dev check**

Run `python -m backend.server` and `npm run dev`, then exercise:
- `/` — matchday renders; a plate with `features` shows the reveal; a stored prediction without features shows none.
- `/forecast` — table renders (network up: projected rows; network down: either season-complete or offline states; never a crash).
- `/calibration` — empty ledger state now; the moment `data/results/*.json` exist, curve + chart render.
- `/teams` → click any club → team detail: seasons, form, Elo chart; head-to-head picker works.
- Unknown slug `/teams/NotAClub` — error state or empty state, no crash.
- Backend down during frontend load — pages show `OfflineSlate` with working retry.

- [ ] **Step 4: Run the morning job once (network permitting)**

Run: `python -m backend.automation morning`
Expected: predictions saved AND `data/forecast/<today>.json` written. Confirm the file exists and its JSON is valid via `Get-Content data/forecast/*.json | ConvertFrom-Json`.

- [ ] **Step 5: Final commit (if any file changed during verification)**

```bash
git add -A
git commit -m "chore: verification fixes for insights expansion"
```
(Only if fixes were made; otherwise skip — do not create empty commits.)

- [ ] **Step 6: Report**

Summarize for the user: all 26 tests pass, lint/build clean, the five features live at `/forecast`, `/calibration`, `/teams/:name` (+ head-to-head), the matchday feature reveal, and the daily forecast cache commits via the morning CI job.