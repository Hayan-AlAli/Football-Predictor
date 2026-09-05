import pandas as pd
import pytest

from backend import features


def _df(rows):
    return pd.DataFrame(rows)


def test_add_elo_difference_basic_and_nan_fill():
    df = features.add_elo_difference(_df([
        {"home_elo": 1900.0, "away_elo": 1800.0},
        {"home_elo": float("nan"), "away_elo": 1700.0},
        {"home_elo": 1600.0, "away_elo": float("nan")},
    ]))
    assert list(df["elo_difference"]) == [100.0, -200.0, 100.0]


def test_production_feature_columns_appends_elo_difference_last():
    assert features.PRODUCTION_FEATURE_COLUMNS[:8] == [
        "home_team_code", "away_team_code", "home_elo", "away_elo",
        "home_rolling_goals", "away_rolling_goals",
        "home_rolling_xg", "away_rolling_xg",
    ]
    assert features.PRODUCTION_FEATURE_COLUMNS[8] == "elo_difference"
    assert features.PRODUCTION_FEATURE_COLUMNS[9:] == features.multi_window_columns()
    assert len(features.PRODUCTION_FEATURE_COLUMNS) == 25


def test_team_window_form_last3_and_last10():
    rows = [
        {"date": pd.Timestamp("2026-01-01"), "home_team": "A", "away_team": "X",
         "home_goals": 1, "away_goals": 0, "home_xg": 1.0, "away_xg": 0.5},
        {"date": pd.Timestamp("2026-01-08"), "home_team": "Y", "away_team": "A",
         "home_goals": 2, "away_goals": 2, "home_xg": 2.0, "away_xg": 1.5},
        {"date": pd.Timestamp("2026-01-15"), "home_team": "A", "away_team": "Z",
         "home_goals": 3, "away_goals": 1, "home_xg": 2.5, "away_xg": 1.0},
        {"date": pd.Timestamp("2026-01-22"), "home_team": "W", "away_team": "A",
         "home_goals": 0, "away_goals": 1, "home_xg": 0.5, "away_xg": 1.0},
    ]
    df = _df(rows)
    f3 = features.team_window_form(df, "A", 3, before=pd.Timestamp("2026-02-01"))
    # Last 3 of A: 2-2 away, 3-1 home, 1-0 away
    assert f3["scored"] == pytest.approx((2 + 3 + 1) / 3)
    assert f3["conceded"] == pytest.approx((2 + 1 + 0) / 3)
    assert f3["xg_for"] == pytest.approx((1.5 + 2.5 + 1.0) / 3)
    assert f3["xg_against"] == pytest.approx((2.0 + 1.0 + 0.5) / 3)
    f10 = features.team_window_form(df, "A", 10, before=pd.Timestamp("2026-02-01"))
    # All 4 of A: adds 1-0 home win
    assert f10["scored"] == pytest.approx((1 + 2 + 3 + 1) / 4)
    assert f10["conceded"] == pytest.approx((0 + 2 + 1 + 0) / 4)


def test_team_window_form_excludes_fixture_and_future():
    rows = [
        {"date": pd.Timestamp("2026-01-01"), "home_team": "A", "away_team": "X",
         "home_goals": 5, "away_goals": 0, "home_xg": 4.0, "away_xg": 0.5},
        {"date": pd.Timestamp("2026-01-08"), "home_team": "A", "away_team": "Y",
         "home_goals": 5, "away_goals": 0, "home_xg": 4.0, "away_xg": 0.5},
    ]
    df = _df(rows)
    # Same-date matches are not prior: only the 01-01 game counts.
    f = features.team_window_form(df, "A", 10, before=pd.Timestamp("2026-01-08"))
    assert f["scored"] == 5.0
    assert f["conceded"] == 0.0


def test_team_window_form_empty_history_is_zero():
    df = _df([
        {"date": pd.Timestamp("2026-01-01"), "home_team": "A", "away_team": "X",
         "home_goals": 1, "away_goals": 0, "home_xg": 1.0, "away_xg": 0.5},
    ])
    assert features.team_window_form(df, "ZZZ", 3, before=pd.Timestamp("2026-02-01")) == {
        "scored": 0.0, "conceded": 0.0, "xg_for": 0.0, "xg_against": 0.0}


def test_add_multi_window_form_columns_and_no_leakage():
    rows = [
        {"date": pd.Timestamp("2026-01-01"), "home_team": "A", "away_team": "B",
         "home_goals": 2, "away_goals": 0, "home_xg": 2.0, "away_xg": 0.5,
         "home_elo": 1800.0, "away_elo": 1700.0},
        {"date": pd.Timestamp("2026-01-08"), "home_team": "B", "away_team": "A",
         "home_goals": 1, "away_goals": 1, "home_xg": 1.0, "away_xg": 1.0,
         "home_elo": 1700.0, "away_elo": 1800.0},
    ]
    df = features.add_multi_window_form(_df(rows))
    for col in features.multi_window_columns():
        assert col in df.columns
    # Row 0: no prior matches -> zeros. Row 1: only row 0 counts (not itself).
    assert df.loc[0, "home_form_3_scored"] == 0.0
    assert df.loc[1, "home_form_3_scored"] == 0.0  # B had no prior games
    assert df.loc[1, "away_form_3_scored"] == 2.0  # A scored 2 in row 0
    assert df.loc[1, "away_form_3_conceded"] == 0.0


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