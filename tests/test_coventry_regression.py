"""Regression tests: weaker/unseen teams must not get elite predictions.

Covers the Coventry-2nd bug class:
1. simulate_season must carry current standings points into the simulation.
2. Unseen teams (no training history) must get neutral, not inflated, lambdas.
3. Normalized names (Newcastle/Wolverhampton/Ipswich Town) must resolve to
   their trained team codes and history, not fall back to Arsenal/zeros.
"""
import pandas as pd

from backend import predictor
from backend.insights import simulate_season


def _standings_gap():
    return [
        {"team": "Arsenal", "played": 25, "wins": 18, "draws": 4, "losses": 3,
         "gf": 55, "ga": 22, "gd": 33, "points": 58},
        {"team": "Coventry City", "played": 25, "wins": 2, "draws": 3, "losses": 20,
         "gf": 20, "ga": 60, "gd": -40, "points": 9},
    ]


def test_simulate_season_carries_standings_points():
    """A 49-point lead with one fixture left cannot be overturned."""
    standings = _standings_gap()
    fixtures = [
        {"home": "Coventry City", "away": "Arsenal",
         "home_elo": 1500, "away_elo": 2050},
    ]
    res = simulate_season(standings, fixtures, n_sims=2000, seed=42)["projected"]
    by = {r["team"]: r for r in res}
    # Even losing every sim, Arsenal keeps 58; Coventry caps at 9 + 3 = 12.
    assert by["Arsenal"]["points_p50"] >= 58
    assert by["Coventry City"]["points_p90"] <= 12
    assert by["Arsenal"]["median_position"] == 1
    assert by["Coventry City"]["median_position"] == 2
    assert by["Arsenal"]["title_odds"] == 1.0
    assert by["Coventry City"]["title_odds"] == 0.0


def test_simulate_season_no_remaining_fixtures_keeps_table_order():
    res = simulate_season(_standings_gap(), [], n_sims=500, seed=42)["projected"]
    by = {r["team"]: r for r in res}
    assert by["Arsenal"]["points_p50"] == 58
    assert by["Coventry City"]["points_p50"] == 9
    assert by["Arsenal"]["median_position"] == 1


def test_unknown_team_lambda_not_inflated():
    """Coventry (zero history) must not out-score Arsenal in the same tie."""
    from backend import elo
    cov, ars = elo.rating("Coventry City"), elo.rating("Arsenal")
    cov_home = predictor.predict_match({
        "home_team": "Coventry City", "away_team": "Arsenal",
        "home_elo": cov, "away_elo": ars,
    })
    ars_home = predictor.predict_match({
        "home_team": "Arsenal", "away_team": "Coventry City",
        "home_elo": ars, "away_elo": cov,
    })
    # Pre-fix this was 3.53: all-zero multi-window form extrapolated wildly.
    assert cov_home["home_goals"] < 2.5
    # The unknown side must not be rated above Arsenal's attack.
    assert cov_home["home_goals"] < ars_home["home_goals"]


def test_team_code_resolves_normalized_names():
    """Teams stored raw in training data must keep their own code."""
    from backend import utils
    normed = {
        "Newcastle": "Newcastle United",
        "Wolverhampton": "Wolves",
        "Ipswich Town": "Ipswich",
    }
    for query, raw in normed.items():
        assert utils.normalize_team_name(raw) == query
        got = predictor._team_code(query)
        want = predictor._team_code(raw)
        assert got == want, f"{query} resolved to {got}, expected {want}"
        assert got != predictor._team_code("Arsenal"), \
            f"{query} fell back to Arsenal's code"


def test_unknown_team_code_is_neutral():
    assert predictor._team_code("Coventry City") != predictor._team_code("Arsenal")


def test_latest_stats_find_normalized_names():
    df = pd.DataFrame([
        {"date": pd.Timestamp("2025-08-16"), "home_team": "Newcastle United",
         "away_team": "Chelsea", "home_goals": 2, "away_goals": 0,
         "home_xg": 1.8, "away_xg": 0.5},
    ])
    goals, _ = predictor.get_latest_stats("Newcastle", df)
    assert goals == 2.0


def test_team_window_form_accepts_tz_aware_before():
    """ESPN fixture dates are tz-aware; training dates are naive.

    Comparing them raised TypeError, which predict_match swallowed into a
    random 0.33/0.34/0.33 prediction for every upcoming fixture.
    """
    from backend import features
    df = pd.DataFrame([
        {"date": pd.Timestamp("2026-01-01"), "home_team": "A", "away_team": "B",
         "home_goals": 2, "away_goals": 0, "home_xg": 1.5, "away_xg": 0.4},
    ])
    form = features.team_window_form(df, "A", 3, before=pd.Timestamp("2026-10-10 14:00", tz="UTC"))
    assert form["scored"] == 2.0


def test_predict_match_with_tz_aware_date_is_not_fallback():
    pred = predictor.predict_match({
        "home_team": "Liverpool", "away_team": "Fulham",
        "home_elo": 1576, "away_elo": 1450,
        "date": pd.Timestamp("2026-10-10 14:00", tz="UTC"),
    })
    assert "home_elo" in pred, "predict_match fell back to random_prediction"
    assert pred["prob_home"] > pred["prob_away"]


def test_forecast_standings_include_stored_results():
    """Results already played this season must seed the forecast table,
    even when the training frame ends before the season started."""
    from backend import insights
    results = [
        {"date": "2026-08-21", "home_team": "Arsenal", "away_team": "Coventry City",
         "home_goals": 3, "away_goals": 0},
        {"date": "2026-08-28", "home_team": "Coventry", "away_team": "Hull",
         "home_goals": 1, "away_goals": 1},
    ]
    table = insights.standings_for_season(predictor.training_df, 2026, results)
    by = {r["team"]: r for r in table}
    assert by["Arsenal"]["points"] == 3
    assert by["Coventry City"]["points"] == 1
    assert by["Coventry City"]["played"] == 2
    assert by["Hull"]["points"] == 1


def test_current_elo_ranks_big_clubs_above_promoted_sides():
    """Every current Premier League club has a real rating (no 1500
    placeholders), and Man City sits well above Coventry."""
    from backend import elo
    ratings = elo.current_ratings()
    for team in ("Manchester City", "Manchester United", "Nottingham Forest",
                 "Coventry City", "Hull"):
        assert predictor._resolve_elo(ratings, team) != 1500, team
    assert elo.rating("Manchester City") - elo.rating("Coventry City") > 300


def test_form_uses_stored_results_after_training(monkeypatch):
    """A promoted side with results this season is judged on them, not on
    league-average form, and missing xG does not count as zero."""
    from backend import elo, features
    stored = [
        {"date": f"2026-09-{d:02d}", "home_team": "Hull", "away_team": "Chelsea",
         "home_goals": 0, "away_goals": 3}
        for d in (1, 8, 15)
    ]
    monkeypatch.setattr(elo, "stored_results_since", lambda as_of: stored)
    frame = predictor.form_frame()
    assert predictor.team_has_history("Hull", frame)
    form = features.team_window_form(frame, "Hull", 3)
    assert form["scored"] == 0.0 and form["conceded"] == 3.0
    assert form["xg_against"] == 3.0  # goals stand in for missing xG


def test_out_of_range_elo_is_clamped():
    lo, hi = predictor.ELO_RANGE
    wild = predictor.predict_match({"home_team": "Coventry City", "away_team": "Arsenal",
                                    "home_elo": lo - 400, "away_elo": hi + 400})
    edge = predictor.predict_match({"home_team": "Coventry City", "away_team": "Arsenal",
                                    "home_elo": lo, "away_elo": hi})
    assert wild["home_goals"] == edge["home_goals"]
    assert wild["home_elo"] == int(lo - 400)  # the reported rating is untouched
