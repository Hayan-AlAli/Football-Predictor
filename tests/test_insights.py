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