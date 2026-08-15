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


def test_build_standings_normalizes_team_names():
    df = pd.DataFrame([
        # same club under two spellings — must count as ONE team
        {"date": pd.Timestamp("2024-08-17"), "home_team": "Manchester Utd", "away_team": "Chelsea",
         "home_goals": 2, "away_goals": 0},
        {"date": pd.Timestamp("2024-08-24"), "home_team": "Chelsea", "away_team": "Manchester United",
         "home_goals": 1, "away_goals": 1},
    ])
    rows = build_standings(df, 2024)
    by_name = {r["team"]: r for r in rows}
    assert "Manchester Utd" not in by_name
    assert by_name["Manchester United"]["played"] == 2
    assert by_name["Manchester United"]["points"] == 4
    assert by_name["Manchester United"]["gf"] == 3
    assert by_name["Manchester United"]["ga"] == 1


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
    # Robust to the trained model's exact lambdas: the Elo-favourite must be
    # the more likely title winner, clearly, and the odds must be exhaustive.
    assert by["Arsenal"]["title_odds"] > 0.6
    assert by["Arsenal"]["title_odds"] > by["Chelsea"]["title_odds"]
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
    # The favourite must never be projected below the underdog on points.
    assert by["Arsenal"]["points_p50"] >= by["Chelsea"]["points_p50"]
    assert by["Arsenal"]["title_odds"] >= by["Chelsea"]["title_odds"]


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