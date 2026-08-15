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