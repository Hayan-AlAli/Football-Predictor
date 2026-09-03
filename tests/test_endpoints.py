from datetime import datetime, timezone
import json

from fastapi.testclient import TestClient

from backend import server, insights


def _client():
    return TestClient(server.app)


def test_season_forecast_ok(monkeypatch):
    payload = {
        "generated": "2026-08-15", "season_year": 2026, "n_sims": 10000,
        "season_complete": False, "standings": [], "projected": [],
        "fixtures_remaining": 0,
    }
    monkeypatch.setattr(insights, "_today_forecast", lambda: None)
    monkeypatch.setattr(insights, "generate_forecast", lambda *a, **k: payload)
    monkeypatch.setattr(insights, "write_forecast_file", lambda f: None)
    r = _client().get("/api/season/forecast")
    assert r.status_code == 200
    assert r.json()["season_year"] == 2026


def test_season_forecast_unavailable(monkeypatch):
    monkeypatch.setattr(insights, "_today_forecast", lambda: None)
    monkeypatch.setattr(insights, "generate_forecast", lambda *a, **k: None)
    r = _client().get("/api/season/forecast")
    assert r.status_code == 503


def test_season_forecast_serves_today_cache(monkeypatch, tmp_path):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    payload = {
        "generated": today, "season_year": 2026, "n_sims": 10000,
        "season_complete": False, "standings": [], "projected": [],
        "fixtures_remaining": 0,
    }
    (tmp_path / f"{today}.json").write_text(json.dumps(payload))
    monkeypatch.setattr(insights, "FORECAST_DIR", str(tmp_path))
    monkeypatch.setattr(insights, "generate_forecast",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not recompute")))
    r = _client().get("/api/season/forecast")
    assert r.status_code == 200
    assert r.json()["generated"] == today


def test_season_forecast_writes_cache_on_miss(monkeypatch, tmp_path):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    payload = {
        "generated": today, "season_year": 2026, "n_sims": 10000,
        "season_complete": False, "standings": [], "projected": [],
        "fixtures_remaining": 0,
    }
    monkeypatch.setattr(insights, "FORECAST_DIR", str(tmp_path))
    monkeypatch.setattr(insights, "_today_forecast", lambda: None)
    monkeypatch.setattr(insights, "generate_forecast", lambda *a, **k: payload)
    r = _client().get("/api/season/forecast")
    assert r.status_code == 200
    assert (tmp_path / f"{today}.json").exists()


def test_calibration_ok(monkeypatch):
    payload = {"entries": 0, "brier": None, "accuracy": None, "bins": [], "rolling": []}
    monkeypatch.setattr(insights, "compute_calibration", lambda *a, **k: payload)
    r = _client().get("/api/calibration")
    assert r.status_code == 200
    assert r.json()["entries"] == 0


def test_team_profile_ok(monkeypatch):
    def fake_profile(df, name):
        return {"team": "Arsenal", "seasons": [], "form": [], "elo_history": []}
    monkeypatch.setattr(insights, "team_profile", fake_profile)
    monkeypatch.setattr(insights, "upcoming_fixtures", lambda name: [])
    r = _client().get("/api/teams/Arsenal")
    assert r.status_code == 200
    body = r.json()
    assert body["team"] == "Arsenal"
    assert body["team_info"]["name"] == "Arsenal"


def test_team_profile_404(monkeypatch):
    monkeypatch.setattr(insights, "team_profile", lambda df, name: None)
    r = _client().get("/api/teams/Norwich%20City")
    assert r.status_code == 404


def test_h2h_ok(monkeypatch):
    def fake_h2h(df, a, b):
        return {"team_a": "Arsenal", "team_b": "Chelsea",
                "summary": {"meetings": 1}, "meetings": []}
    monkeypatch.setattr(insights, "head_to_head", fake_h2h)
    r = _client().get("/api/teams/Arsenal/h2h?vs=Chelsea")
    assert r.status_code == 200
    body = r.json()
    assert body["team_a"] == "Arsenal"
    assert body["summary"]["meetings"] == 1


def test_h2h_missing_vs():
    r = _client().get("/api/teams/Arsenal/h2h")
    assert r.status_code == 400


def test_h2h_404(monkeypatch):
    monkeypatch.setattr(insights, "head_to_head", lambda df, a, b: None)
    r = _client().get("/api/teams/Arsenal/h2h?vs=Norwich%20City")
    assert r.status_code == 404


def test_h2h_never_met_empty_record(monkeypatch):
    empty = {
        "team_a": "Everton", "team_b": "Chelsea",
        "summary": {"meetings": 0, "team_a_wins": 0, "draws": 0,
                    "team_b_wins": 0, "team_a_for": 0, "team_a_against": 0},
        "meetings": [],
    }
    monkeypatch.setattr(insights, "head_to_head", lambda df, a, b: empty)
    r = _client().get("/api/teams/Everton/h2h?vs=Chelsea")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["meetings"] == 0
    assert body["meetings"] == []


def test_team_profile_includes_upcoming(monkeypatch):
    def fake_profile(df, name):
        return {"team": "Arsenal", "seasons": [], "form": [], "elo_history": []}
    monkeypatch.setattr(insights, "team_profile", fake_profile)
    monkeypatch.setattr(insights, "upcoming_fixtures", lambda name: [])
    r = _client().get("/api/teams/Arsenal")
    assert r.status_code == 200
    assert r.json()["upcoming"] == []


def test_h2h_self_pair_empty_record(monkeypatch):
    import pandas as pd
    from backend import predictor
    df = pd.DataFrame([
        {"date": pd.Timestamp("2024-08-17"), "home_team": "Arsenal", "away_team": "Chelsea",
         "home_goals": 2, "away_goals": 1, "home_elo": 1900, "away_elo": 1800},
    ])
    monkeypatch.setattr(predictor, "training_df", df)
    r = _client().get("/api/teams/Arsenal/h2h?vs=Arsenal")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["meetings"] == 0
    assert body["meetings"] == []


def test_jobs_require_secret():
    r = _client().post("/api/jobs/morning")
    assert r.status_code == 401


def test_morning_job_ok(monkeypatch):
    import os
    from backend import automation
    monkeypatch.setenv("CRON_SECRET", "test-secret")
    monkeypatch.setattr(automation, "run_morning_job",
                        lambda use_db: {"date": "2026-01-03", "predictions": 5, "forecast": True})
    r = _client().post("/api/jobs/morning", headers={"Authorization": "Bearer test-secret"})
    assert r.status_code == 200
    assert r.json()["predictions"] == 5