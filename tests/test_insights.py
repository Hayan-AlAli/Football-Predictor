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


from backend import data_manager
from backend import predictor


def test_generate_forecast_handles_nan_elo(monkeypatch):
    train = pd.DataFrame([
        {"date": pd.Timestamp("2025-08-16"), "home_team": "Arsenal", "away_team": "Chelsea",
         "home_goals": 2, "away_goals": 1},
    ])
    monkeypatch.setattr(predictor, "training_df", train)
    fixtures = pd.DataFrame([
        {"date": pd.Timestamp("2026-08-20"), "home_team": "Arsenal", "away_team": "Chelsea",
         "home_elo": float("nan"), "away_elo": float("nan")},
    ])
    monkeypatch.setattr(data_manager, "fetch_upcoming_matches", lambda: fixtures)
    res = generate_forecast()
    assert res is not None
    assert isinstance(res["projected"], list)
    assert res["fixtures_remaining"] == 1


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


def test_calibration_hand_computed_brier(tmp_path):
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


def test_calibration_empty(tmp_path):
    pred_dir, res_dir = _write_cal_fixture(tmp_path, {}, {})
    res = compute_calibration(pred_dir, res_dir)
    assert res["entries"] == 0 and res["brier"] is None and res["accuracy"] is None
    assert res["bins"] == [] and res["rolling"] == []
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
    assert form[0]["date"] < form[-1]["date"]        # oldest -> newest
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


def test_head_to_head_never_met_empty_record():
    h = head_to_head(H2H_DF, "Everton", "Chelsea")
    assert h is not None
    assert h["summary"] == {
        "meetings": 0,
        "team_a_wins": 0,
        "draws": 0,
        "team_b_wins": 0,
        "team_a_for": 0,
        "team_a_against": 0,
    }
    assert h["meetings"] == []
