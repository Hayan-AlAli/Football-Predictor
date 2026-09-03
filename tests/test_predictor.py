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


def test_training_elo_lookup_has_real_ratings():
    lookup = predictor.training_elo_lookup()
    assert lookup, "expected offline Elo fallback from training data"
    assert lookup.get("Arsenal", 1500) > 1900
    for team, elo in lookup.items():
        assert elo != 1500.0


def test_predict_match_falls_back_to_training_elo(monkeypatch):
    monkeypatch.setattr(predictor, "_fetch_live_elo", lambda: None)
    pred = predictor.predict_match({
        "home_team": "Arsenal",
        "away_team": "Chelsea",
    })
    assert "features" in pred
    assert pred["features"]["home_elo"] != 1500
    assert pred["features"]["home_elo"] == int(predictor.training_elo_lookup()["Arsenal"])


def test_predict_match_unknown_team_still_1500(monkeypatch):
    monkeypatch.setattr(predictor, "_fetch_live_elo", lambda: None)
    monkeypatch.setattr(predictor, "training_elo_lookup", lambda: {})
    pred = predictor.predict_match({
        "home_team": "Arsenal",
        "away_team": "Chelsea",
    })
    assert pred["features"]["home_elo"] == 1500