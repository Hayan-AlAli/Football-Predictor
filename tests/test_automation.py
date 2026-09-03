import os

from backend import automation
from backend import data_manager
from backend import insights
from backend import utils_data


def test_write_forecast_file_writes_cache(tmp_path):
    payload = {
        "generated": "2026-08-15", "season_year": 2026, "n_sims": 10000,
        "season_complete": False, "standings": [], "projected": [],
        "fixtures_remaining": 380,
    }
    out_dir = str(tmp_path / "forecast")
    path = insights.write_forecast_file(forecast=payload, out_dir=out_dir)
    assert path is not None
    assert os.path.exists(path)


RAW_RESULTS = [
    {"home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 2, "away_goals": 1},
]


def _patch_results_dir(monkeypatch, tmp_path):
    res_dir = tmp_path / "results"
    res_dir.mkdir()
    monkeypatch.setattr(utils_data, "RESULTS_DIR", str(res_dir))
    return res_dir


def test_evening_job_writes_raw_results(monkeypatch, tmp_path):
    from datetime import datetime, timezone
    res_dir = _patch_results_dir(monkeypatch, tmp_path)
    monkeypatch.setattr(data_manager, "fetch_latest_results", lambda d: list(RAW_RESULTS))

    automation.run_evening_job(lookback_days=1)

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    saved = utils_data.load_json(str(res_dir / f"{today}.json"))
    assert saved == RAW_RESULTS


def test_evening_job_skips_recorded_dates(monkeypatch, tmp_path):
    from datetime import datetime, timezone
    res_dir = _patch_results_dir(monkeypatch, tmp_path)
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    (res_dir / f"{today}.json").write_text("[]")

    calls = []
    monkeypatch.setattr(data_manager, "fetch_latest_results", lambda d: calls.append(d) or list(RAW_RESULTS))

    automation.run_evening_job(lookback_days=1)

    assert calls == []
    assert (res_dir / f"{today}.json").read_text() == "[]"


def test_evening_job_backfills_missing_dates(monkeypatch, tmp_path):
    from datetime import datetime, timedelta, timezone
    res_dir = _patch_results_dir(monkeypatch, tmp_path)
    today = datetime.now(timezone.utc).date()
    yesterday = (today - timedelta(days=1)).strftime('%Y-%m-%d')

    def fake_fetch(date_str):
        return [] if date_str == today.strftime('%Y-%m-%d') else list(RAW_RESULTS)

    monkeypatch.setattr(data_manager, "fetch_latest_results", fake_fetch)

    automation.run_evening_job(lookback_days=3)

    assert not (res_dir / f"{today.strftime('%Y-%m-%d')}.json").exists()
    assert utils_data.load_json(str(res_dir / f"{yesterday}.json")) == RAW_RESULTS


def test_morning_job_returns_summary(monkeypatch):
    import pandas as pd
    monkeypatch.setattr(automation.data_manager, "fetch_upcoming_matches", lambda: pd.DataFrame())
    summary = automation.run_morning_job(use_db=False)
    assert summary == {"date": summary["date"], "predictions": 0, "forecast": None}


def test_morning_job_file_success_forecast_is_bool(monkeypatch, tmp_path):
    import pandas as pd
    res_dir = _patch_results_dir(monkeypatch, tmp_path)
    pred_dir = tmp_path / "predictions"
    pred_dir.mkdir()
    monkeypatch.setattr(utils_data, "PREDICTIONS_DIR", str(pred_dir))
    df = pd.DataFrame([{"date": pd.Timestamp.now(tz="UTC"), "home_team": "Arsenal",
                        "away_team": "Chelsea", "home_elo": 1500, "away_elo": 1500}])
    monkeypatch.setattr(data_manager, "fetch_upcoming_matches", lambda: df)
    fake_preds = [{"id": "x", "date": "2026-01-01", "home_team": "Arsenal",
                   "away_team": "Chelsea", "prediction": {}}]
    monkeypatch.setattr(utils_data, "generate_predictions_for_date", lambda d, f: fake_preds)
    monkeypatch.setattr(insights, "write_forecast_file", lambda *a, **k: str(tmp_path / "f.json"))
    summary = automation.run_morning_job(use_db=False)
    assert summary["predictions"] == 1
    assert summary["forecast"] is True
    assert isinstance(summary["forecast"], bool)


def test_morning_job_db_success_writes_db_no_files(monkeypatch):
    import pandas as pd
    from backend import database as db
    df = pd.DataFrame([{"date": pd.Timestamp.now(tz="UTC"), "home_team": "Arsenal",
                        "away_team": "Chelsea", "home_elo": 1500, "away_elo": 1500}])
    monkeypatch.setattr(data_manager, "fetch_upcoming_matches", lambda: df)
    fake_preds = [{"id": "x", "date": "2026-01-01", "home_team": "Arsenal",
                   "away_team": "Chelsea", "prediction": {}}]
    monkeypatch.setattr(utils_data, "generate_predictions_for_date", lambda d, f: fake_preds)
    monkeypatch.setattr(db, "DATABASE_URL", "postgres://fake")
    calls = {}
    monkeypatch.setattr(db, "init_db", lambda: calls.setdefault("init", True))
    monkeypatch.setattr(db, "save_predictions", lambda p: calls.setdefault("preds", p))
    monkeypatch.setattr(db, "save_forecast", lambda d, f: calls.setdefault("forecast", (d, f)))
    monkeypatch.setattr(automation.insights, "generate_forecast", lambda *a, **k: {"generated": "x"})

    def _no_file(*a, **k):
        raise AssertionError("file write in db mode")
    monkeypatch.setattr(utils_data, "save_json", _no_file)
    monkeypatch.setattr(insights, "write_forecast_file", _no_file)

    summary = automation.run_morning_job(use_db=True)
    assert summary["predictions"] == 1
    assert summary["forecast"] is True
    assert calls["preds"] == fake_preds
    assert calls["forecast"][1] == {"generated": "x"}


def test_evening_job_db_mirrors_raw_backfill(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from backend import database as db
    monkeypatch.setattr(db, "DATABASE_URL", "postgres://fake")
    monkeypatch.setattr(db, "init_db", lambda: None)
    today = datetime.now(timezone.utc).date()
    today_str = today.strftime('%Y-%m-%d')
    yesterday_str = (today - timedelta(days=1)).strftime('%Y-%m-%d')

    def fake_load(date_str):
        return [{"home_team": "A", "away_team": "B"}] if date_str == today_str else []
    monkeypatch.setattr(db, "load_results", fake_load)
    calls = []
    monkeypatch.setattr(data_manager, "fetch_latest_results",
                        lambda d: calls.append(d) or list(RAW_RESULTS))
    saved = []
    monkeypatch.setattr(db, "save_results", lambda rows: saved.append(rows))

    def _no_file(*a, **k):
        raise AssertionError("file write in db mode")
    monkeypatch.setattr(utils_data, "save_json", _no_file)

    summary = automation.run_evening_job(use_db=True, lookback_days=3)
    assert today_str not in calls
    assert yesterday_str in calls
    assert saved and saved[0][0]["date"] == yesterday_str
    assert saved[0][0]["home_team"] == "Arsenal"
    assert any(d == yesterday_str for d, _ in summary["saved"])


def test_jobs_db_require_postgres_url(monkeypatch):
    import pandas as pd
    from backend import database as db
    monkeypatch.setattr(db, "DATABASE_URL", None)
    monkeypatch.setattr(automation.data_manager, "fetch_upcoming_matches", lambda: pd.DataFrame())
    # morning empty path still returns summary without needing DB; force non-empty via preds
    df = pd.DataFrame([{"date": pd.Timestamp.now(tz="UTC"), "home_team": "A",
                        "away_team": "B", "home_elo": 1500, "away_elo": 1500}])
    monkeypatch.setattr(data_manager, "fetch_upcoming_matches", lambda: df)
    monkeypatch.setattr(utils_data, "generate_predictions_for_date",
                        lambda d, f: [{"id": "x", "date": d, "home_team": "A",
                                       "away_team": "B", "prediction": {}}])
    try:
        automation.run_morning_job(use_db=True)
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "POSTGRES_URL" in str(e)
    try:
        automation.run_evening_job(use_db=True, lookback_days=1)
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "POSTGRES_URL" in str(e)