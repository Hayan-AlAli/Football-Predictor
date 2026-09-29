from datetime import datetime, timezone

import numpy as np
import pandas as pd

from backend import predictor
from backend import utils


def season_year_of(ts):
    return ts.year if ts.month >= 8 else ts.year - 1


def _season_col(df):
    return df["date"].dt.year - (df["date"].dt.month < 8).astype(int)


def build_standings(training_df, season_year):
    df = training_df[_season_col(training_df) == season_year]
    df = df.copy()
    df["home_team"] = utils.normalize_column(df["home_team"])
    df["away_team"] = utils.normalize_column(df["away_team"])
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


def _season_matches(training_df, season_year, results=None):
    """A season's played matches from training rows plus stored results.

    The bundled training frame is frozen at train time, so on its own it
    misses every match played since (a new season's table came out empty
    and the forecast started all 20 teams from zero points). Stored results
    ([{date, home_team, away_team, home_goals, away_goals}]) fill that gap;
    a match present in both is counted once.
    """
    cols = ["date", "home_team", "away_team", "home_goals", "away_goals"]
    frames = []
    if training_df is not None and not training_df.empty:
        frames.append(training_df[cols].copy())
    if results:
        frames.append(pd.DataFrame(list(results))[cols])
    if not frames:
        return pd.DataFrame(columns=cols)
    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["home_goals", "away_goals"])
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_localize(None)
    df["home_team"] = utils.normalize_column(df["home_team"])
    df["away_team"] = utils.normalize_column(df["away_team"])
    df["_day"] = df["date"].dt.date
    df = df.drop_duplicates(subset=["_day", "home_team", "away_team"], keep="last")
    df = df.drop(columns="_day")
    return df[_season_col(df) == season_year]


def standings_for_season(training_df, season_year, results=None):
    """League table for a season (see _season_matches)."""
    df = _season_matches(training_df, season_year, results)
    return build_standings(df, season_year) if not df.empty else []


LEAGUE_SIZE = 20


def complete_fixtures(fixtures, teams, played):
    """Add every unplayed pairing the fixture feed is missing.

    In a double round-robin each ordered (home, away) pair meets exactly
    once, so the remaining fixtures are all pairs minus those played. ESPN
    omits matches awaiting a date (TV picks, cup clashes): ~48 in Sept 2026,
    which the forecast then silently never simulated.
    fixtures: [{home, away, home_elo, away_elo}]; teams: the league's
    clubs; played: iterable of (home, away) already played.
    """
    from backend import elo
    if len(teams) != LEAGUE_SIZE:
        return fixtures
    norm = utils.normalize_team_name
    known = {(norm(f["home"]), norm(f["away"])) for f in fixtures}
    known |= {(norm(h), norm(a)) for h, a in played}
    ratings = elo.current_ratings()
    out = list(fixtures)
    for h in sorted(teams):
        for a in sorted(teams):
            if h != a and (h, a) not in known:
                out.append({"home": h, "away": a,
                            "home_elo": elo.rating(h, ratings),
                            "away_elo": elo.rating(a, ratings)})
    return out


def _poisson_sims(home_lambda, away_lambda, n_sims, seed):
    rng = np.random.default_rng(seed)
    return rng.poisson(home_lambda, size=n_sims), rng.poisson(away_lambda, size=n_sims)


def simulate_season(standings, fixture_rows, n_sims=10000, seed=42):
    inputs = [{"home_team": utils.normalize_team_name(f["home"]),
               "away_team": utils.normalize_team_name(f["away"]),
               "home_elo": f["home_elo"], "away_elo": f["away_elo"]} for f in fixture_rows]
    rows = [(m["home_team"], m["away_team"],
             max(float(p.get("home_goals") or 0.0), 0.0),
             max(float(p.get("away_goals") or 0.0), 0.0))
            for m, p in zip(inputs, predictor.predict_matches(inputs))]

    team_names = sorted({r["team"] for r in standings}
                        | {h for h, _, _, _ in rows}
                        | {a for _, a, _, _ in rows})
    # Current points are the starting total: the sim only adds points earned
    # in the remaining fixtures. Teams in fixtures but outside the standings
    # (no games played yet) start from zero.
    base_points = {r["team"]: float(r.get("points", 0) or 0) for r in standings}
    points = {t: np.full(n_sims, base_points.get(t, 0.0)) for t in team_names}

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


def generate_forecast(matches, n_sims=10000, seed=42):
    """Monte Carlo forecast of a season from its stored matches.

    matches: one season's rows as db.load_matches returns them. Finished
    ones make the current table; everything else is still to play (plus any
    pairing the feed has not listed yet, see complete_fixtures).
    """
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not matches:
        return None
    season_year = matches[0]["season"]
    played = pd.DataFrame(
        [{"date": m["date"], "home_team": m["home_team"], "away_team": m["away_team"],
          "home_goals": m["home_goals"], "away_goals": m["away_goals"]}
         for m in matches if m["status"] == "finished"],
        columns=["date", "home_team", "away_team", "home_goals", "away_goals"])
    if not played.empty:
        played["date"] = pd.to_datetime(played["date"])
    standings = build_standings(played, season_year) if not played.empty else []

    from backend import elo
    ratings = elo.current_ratings()
    fixtures = [{"home": m["home_team"], "away": m["away_team"],
                 "home_elo": elo.rating(m["home_team"], ratings),
                 "away_elo": elo.rating(m["away_team"], ratings)}
                for m in matches if m["status"] != "finished"]
    league = {r["team"] for r in standings} | {m["home_team"] for m in matches} | {m["away_team"] for m in matches}
    fixtures = complete_fixtures(fixtures, league,
                                 zip(played["home_team"], played["away_team"]))

    base = {"generated": today_str, "season_year": season_year, "standings": standings}
    if not fixtures:
        return {**base, "n_sims": n_sims, "season_complete": True,
                "projected": [], "fixtures_remaining": 0}
    sim = simulate_season(standings, fixtures, n_sims=n_sims, seed=seed)
    return {**base, "n_sims": sim["n_sims"], "season_complete": False,
            "projected": sim["projected"], "fixtures_remaining": sim["fixtures_remaining"]}


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


def verdict(match):
    """CORRECT / INCORRECT once a predicted match is finished, else PENDING
    (None when there is no prediction to judge)."""
    pred = match.get("prediction")
    if not pred:
        return None
    if match.get("status") != "finished" or match.get("home_goals") is None:
        return "PENDING"
    hg, ag = match["home_goals"], match["away_goals"]
    actual = match["home_team"] if hg > ag else match["away_team"] if ag > hg else "Draw"
    called = pred.get("winner")
    if called and called != "Draw":
        called = utils.normalize_team_name(called)
    return "CORRECT" if called == actual else "INCORRECT"


def compute_calibration(matches):
    """Calibration of the model's calls over every settled, predicted match."""
    entries = []
    for m in matches or []:
        v = verdict(m)
        if v not in ("CORRECT", "INCORRECT") or not m["prediction"].get("prob_home"):
            continue
        entries.append({
            "date": m["date"],
            "p": _called_probability(m["prediction"], m["home_team"], m["away_team"]),
            "correct": v == "CORRECT",
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
    out["home_team"] = utils.normalize_column(out["home_team"])
    out["away_team"] = utils.normalize_column(out["away_team"])
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


def _empty_h2h(df, a, b):
    return {
        "team_a": _canonical_name(df, a),
        "team_b": _canonical_name(df, b),
        "summary": {
            "meetings": 0,
            "team_a_wins": 0,
            "draws": 0,
            "team_b_wins": 0,
            "team_a_for": 0,
            "team_a_against": 0,
        },
        "meetings": [],
    }


def team_profile(training_df, team_name, current_elo=None):
    """current_elo: today's rating, appended as the chart's latest point."""
    if training_df is None:
        return None
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
        elo = r.get("home_elo") if r["home_team"] == norm else r.get("away_elo")
        if elo is None or pd.isna(elo):
            continue  # stored live results carry no pre-match Elo
        seen.add(d)
        elo_history.append({"date": d, "elo": int(float(elo))})
    if current_elo is not None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today not in seen:
            elo_history.append({"date": today, "elo": int(current_elo)})

    return {"team": name, "seasons": seasons, "form": form, "elo_history": elo_history}


def head_to_head(training_df, team_a, team_b):
    if training_df is None:
        return None
    df = _norm_df(training_df)
    a = utils.normalize_team_name(team_a)
    b = utils.normalize_team_name(team_b)
    present = set(df["home_team"]) | set(df["away_team"])
    if a not in present or b not in present:
        return None
    if a == b:
        return _empty_h2h(df, a, b)
    meetings = df[
        ((df["home_team"] == a) & (df["away_team"] == b))
        | ((df["home_team"] == b) & (df["away_team"] == a))
    ]
    if meetings.empty:
        return _empty_h2h(df, a, b)

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
    """A team's unplayed fixtures with their predictions, from the DB."""
    from backend import db
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return [m for m in db.load_matches(team=team_name, since=today)
            if m["status"] in ("scheduled", "postponed", "in_progress")]
