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
    df = df.copy()
    df["home_team"] = df["home_team"].apply(utils.normalize_team_name)
    df["away_team"] = df["away_team"].apply(utils.normalize_team_name)
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
    name_order = np.argsort(np.array(team_names), kind="stable")
    order = name_order[np.argsort(-mat[name_order], axis=0, kind="stable")]
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


def _safe_elo(value):
    if pd.isna(value) or not value:
        return 1500.0
    return float(value)


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
                    "home_elo": _safe_elo(row.get("home_elo")),
                    "away_elo": _safe_elo(row.get("away_elo")),
                })

    df = predictor.training_df
    if season_year is None and df is not None and not df.empty:
        season_year = season_year_of(df["date"].max())

    standings = []
    if df is not None:
        standings = build_standings(df, season_year) if season_year is not None else []

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


def upcoming_fixtures(team_name):
    norm = utils.normalize_team_name(team_name)
    try:
        upcoming = data_manager.fetch_upcoming_matches()
    except Exception:
        return []
    if upcoming is None or upcoming.empty:
        return []
    out = []
    for _, row in upcoming.iterrows():
        h = utils.normalize_team_name(row["home_team"])
        a = utils.normalize_team_name(row["away_team"])
        if norm not in (h, a):
            continue
        pred = predictor.predict_match({
            "home_team": h,
            "away_team": a,
            "date": row["date"],
            "home_elo": float(row.get("home_elo") or 1500),
            "away_elo": float(row.get("away_elo") or 1500),
        })
        out.append({
            "id": utils_data.generate_match_id(row["date"], h, a),
            "date": row["date"].strftime("%Y-%m-%d"),
            "time": row["date"].strftime("%H:%M"),
            "home_team": h,
            "away_team": a,
            "prediction": pred,
        })
    return out
