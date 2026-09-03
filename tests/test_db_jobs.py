import pytest
from backend import database as db

needs_db = pytest.mark.skipif(db.DATABASE_URL is None, reason="POSTGRES_URL not set")


@needs_db
def test_save_and_load_results_roundtrip():
    db.init_db()
    rows = [{"date": "2026-01-03", "home_team": "Arsenal", "away_team": "Chelsea",
             "home_goals": 2, "away_goals": 1}]
    db.save_results(rows)
    loaded = db.load_results("2026-01-03")
    assert {"home_team": "Arsenal", "away_team": "Chelsea",
            "home_goals": 2, "away_goals": 1} in loaded


@needs_db
def test_save_results_upsert_is_idempotent():
    rows = [{"date": "2026-01-03", "home_team": "Arsenal", "away_team": "Chelsea",
             "home_goals": 2, "away_goals": 1}]
    db.save_results(rows)
    db.save_results(rows)
    assert len(db.load_results("2026-01-03")) == 1


@needs_db
def test_save_and_load_forecast_roundtrip():
    db.init_db()
    payload = {"generated": "2026-01-03", "entries": 1}
    db.save_forecast("2026-01-03", payload)
    assert db.load_forecast("2026-01-03") == payload
    assert db.load_latest_forecast()["generated"] == "2026-01-03"
