from backend import predictor


def test_select_winner_uses_aggregate_mass_not_peak_scoreline():
    # 1-1 is the likeliest single scoreline, but home owns the mass.
    winner, score = predictor._select_winner(
        "Arsenal", "Chelsea", 0.45, 0.27, 0.28, (2, 1), (1, 1), (1, 2))
    assert winner == "Arsenal"
    assert score == (2, 1)


def test_select_winner_draw_and_away():
    assert predictor._select_winner(
        "Arsenal", "Chelsea", 0.25, 0.45, 0.30, (1, 0), (1, 1), (0, 1))[0] == "Draw"
    assert predictor._select_winner(
        "Arsenal", "Chelsea", 0.25, 0.30, 0.45, (1, 0), (1, 1), (0, 1)) == ("Chelsea", (0, 1))


def test_select_winner_tie_breaks_home():
    winner, _ = predictor._select_winner(
        "Arsenal", "Chelsea", 0.4, 0.4, 0.2, (1, 0), (1, 1), (0, 1))
    assert winner == "Arsenal"


def test_models_expect_production_features_including_elo_difference():
    from backend import features as features_mod
    assert predictor.model_home.n_features_in_ == len(features_mod.PRODUCTION_FEATURE_COLUMNS)
    assert predictor.model_away.n_features_in_ == len(features_mod.PRODUCTION_FEATURE_COLUMNS)


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


def test_predict_match_without_elo_uses_current_ratings():
    from backend import elo
    pred = predictor.predict_match({
        "home_team": "Arsenal",
        "away_team": "Chelsea",
    })
    assert "features" in pred
    assert pred["features"]["home_elo"] == int(elo.rating("Arsenal"))
    assert pred["features"]["away_elo"] == int(elo.rating("Chelsea"))


def test_predict_match_unknown_team_still_1500():
    pred = predictor.predict_match({
        "home_team": "Arsenal",
        "away_team": "Grimsby Town",
    })
    assert pred["features"]["away_elo"] == 1500


def _assert_real_prediction(pred):
    # Random fallback has no features and exact 0.33/0.34/0.33 probs.
    assert "features" in pred
    assert not (pred["prob_home"] == 0.33 and pred["prob_draw"] == 0.34
                and pred["prob_away"] == 0.33)


def test_predict_match_nan_elo_falls_back_to_1500():
    import math
    pred = predictor.predict_match({
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "home_elo": float("nan"),
        "away_elo": float("nan"),
    })
    _assert_real_prediction(pred)
    assert pred["home_elo"] == 1500
    assert pred["away_elo"] == 1500


def test_predict_match_garbage_elo_falls_back_to_1500(monkeypatch):
    for bad in (float("inf"), float("-inf"), "garbage", 0):
        pred = predictor.predict_match({
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "home_elo": bad,
            "away_elo": bad,
        })
        _assert_real_prediction(pred)
        assert pred["home_elo"] == 1500
        assert pred["away_elo"] == 1500


def test_predict_match_none_elo_uses_current_ratings():
    pred = predictor.predict_match({
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "home_elo": None,
        "away_elo": None,
    })
    _assert_real_prediction(pred)
    assert pred["home_elo"] != 1500


def test_resolve_elo_skips_nan_ratings():
    assert predictor._resolve_elo({"Chelsea": float("nan")}, "Chelsea") == 1500
    assert predictor._resolve_elo({"Arsenal": 1850.0}, "Arsenal") == 1850.0


def test_safe_elo():
    from backend import utils
    assert utils.safe_elo(None) == 1500.0
    assert utils.safe_elo(float("nan")) == 1500.0
    assert utils.safe_elo(float("inf")) == 1500.0
    assert utils.safe_elo("garbage") == 1500.0
    assert utils.safe_elo(0) == 1500.0
    assert utils.safe_elo(1900) == 1900.0
    assert utils.safe_elo(1850.7) == 1850.7

def test_batch_matches_single_predictions():
    fixtures = [
        {"home_team": "Arsenal", "away_team": "Chelsea", "home_elo": 1714, "away_elo": 1499},
        {"home_team": "Hull", "away_team": "Liverpool", "home_elo": 1394, "away_elo": 1576,
         "date": "2026-10-03"},
        {"home_team": "Nowhere Rovers", "away_team": "Arsenal"},
    ]
    batch = predictor.predict_matches(fixtures)
    assert len(batch) == 3
    for f, b in zip(fixtures, batch):
        single = predictor.predict_match(f)
        assert b["model_version"] == single["model_version"] == predictor.MODEL_VERSION
        for key in ("prob_home", "prob_draw", "prob_away", "home_goals", "away_goals", "score", "winner"):
            assert b[key] == single[key], key
    assert predictor.predict_matches([]) == []


def test_bad_row_falls_back_without_sinking_the_batch(monkeypatch):
    real = predictor._match_features

    def flaky(m, state, form_of):
        if m["home_team"] == "Chelsea":
            raise ValueError("boom")
        return real(m, state, form_of)

    monkeypatch.setattr(predictor, "_match_features", flaky)
    out = predictor.predict_matches([
        {"home_team": "Arsenal", "away_team": "Everton"},
        {"home_team": "Chelsea", "away_team": "Everton"},
    ])
    assert out[0]["model_version"] == predictor.MODEL_VERSION
    assert out[1]["model_version"] == predictor.FALLBACK_VERSION


def test_read_endpoints_do_not_load_the_model():
    """Read endpoints, team pages included, never unpickle the forests."""
    import subprocess
    import sys
    code = (
        "import sys, backend.server as s\n"
        "from fastapi.testclient import TestClient\n"
        "c = TestClient(s.app)\n"
        "for p in ('/api/matches', '/api/teams', '/api/calibration', '/api/health',\n"
        "          '/api/teams/arsenal', '/api/teams/arsenal/h2h?vs=chelsea'):\n"
        "    assert c.get(p).status_code == 200, p\n"
        "assert 'sklearn' not in sys.modules, 'scikit-learn was imported'\n"
        "assert s.predictor._models is None, 'models were loaded'\n"
        "assert c.get('/api/predict?home=arsenal&away=chelsea').status_code == 200\n"
        "assert s.predictor._models is not None\n"
    )
    import os
    import tempfile
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{tempfile.mkdtemp()}/cold.db"}
    env.pop("POSTGRES_URL", None)
    result = subprocess.run([sys.executable, "-W", "ignore", "-c", code], env=env,
                            capture_output=True, text=True,
                            cwd=os.path.join(os.path.dirname(__file__), ".."))
    assert result.returncode == 0, result.stderr[-2000:]


def test_latest_stats_only_count_matches_before_the_cutoff():
    import pandas as pd
    df = pd.DataFrame([
        {"date": pd.Timestamp("2026-09-05"), "home_team": "Arsenal", "away_team": "Chelsea",
         "home_goals": 1, "away_goals": 0},
        {"date": pd.Timestamp("2026-09-12"), "home_team": "Arsenal", "away_team": "Everton",
         "home_goals": 5, "away_goals": 0},
    ])
    assert predictor.get_latest_stats("Arsenal", df)[0] == 3.0
    # Midnight of match day: the 12 Sep result is not known yet.
    assert predictor.get_latest_stats("Arsenal", df, before="2026-09-12")[0] == 1.0
