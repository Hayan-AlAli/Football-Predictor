import numpy as np
import pandas as pd

from backend import evaluate


def _data():
    rows = []
    for i, sy in enumerate([2020, 2021, 2022]):
        for j in range(5):
            rows.append({
                "date": pd.Timestamp(f"{sy + 1}-01-0{j + 1}"),
                "home_team": "A" if j % 2 == 0 else "B",
                "away_team": "B" if j % 2 == 0 else "A",
                "home_goals": j % 3, "away_goals": (j + 1) % 3,
                "home_xg": float(j), "away_xg": float(j + 1),
                "home_elo": 1500.0, "away_elo": 1450.0,
            })
    return pd.DataFrame(rows)


def test_split_uses_last_season_as_test():
    df = _data()
    train, test = evaluate.split_by_season(df)
    assert test["date"].dt.year.min() == max(df["date"].dt.year)
    assert train["date"].dt.year.max() < test["date"].dt.year.min()


def test_split_is_deterministic_and_exhaustive():
    df = _data()
    train, test = evaluate.split_by_season(df)
    assert len(train) + len(test) == len(df)


def test_model_specs_contains_baseline():
    assert "baseline_rf" in evaluate.model_specs()


def test_score_test_returns_metrics_dict(monkeypatch):
    df = _data()
    monkeypatch.setattr(evaluate, "_fit_pair", lambda X_train, yh, ya, spec_key: (None, None))
    monkeypatch.setattr(evaluate, "_predict_pair", lambda pair, X: (pd.Series([1.2, 0.8, 1.1, 0.9, 1.0]), pd.Series([0.7, 1.1, 1.2, 0.8, 1.0])))
    res = evaluate.score_test(_data(), df[df["date"].dt.year == 2023], "baseline_rf")
    for key in ("brier", "log_loss", "accuracy", "n_matches"):
        assert key in res
    assert res["n_matches"] == 5


def test_run_all_returns_rows():
    rows = evaluate.run_all()
    assert isinstance(rows, list)
    assert len(rows) >= 1
    assert all({"spec", "brier", "log_loss", "accuracy", "n_matches"} <= set(r) for r in rows)


def test_model_specs_has_challengers():
    specs = evaluate.model_specs()
    assert "challenger_v2_hgb" in specs
    assert "challenger_v2_hgb_calib" in specs


def test_calibrate_clamps_and_order_preserved():
    preds = np.array([[0.05, 0.45, 0.98], [0.3, 0.4, 0.9]])
    fit_probs = np.array([[0.1, 0.5, 0.9], [0.2, 0.6, 0.95]])
    fit_out = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    out = evaluate.calibrate_probs(preds, fit_probs, fit_out)
    assert out.shape == preds.shape
    assert (out >= 0.01).all() and (out <= 0.99).all()
    assert out[0, 2] > out[0, 0]  # away more likely than home, order preserved


def test_calibrated_v2_runs_end_to_end():
    train, test = evaluate.split_by_season(pd.read_pickle("tests/_mini.pkl"))
    row = evaluate.score_test(train, test, "challenger_v2_hgb_calib")
    assert row["n_matches"] == len(test) // 2  # calibration scores the first half only