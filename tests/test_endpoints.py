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
    monkeypatch.setattr(insights, "generate_forecast", lambda *a, **k: payload)
    r = _client().get("/api/season/forecast")
    assert r.status_code == 200
    assert r.json()["season_year"] == 2026


def test_season_forecast_unavailable(monkeypatch):
    monkeypatch.setattr(insights, "generate_forecast", lambda *a, **k: None)
    r = _client().get("/api/season/forecast")
    assert r.status_code == 503


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


def test_team_profile_includes_upcoming(monkeypatch):
    def fake_profile(df, name):
        return {"team": "Arsenal", "seasons": [], "form": [], "elo_history": []}
    monkeypatch.setattr(insights, "team_profile", fake_profile)
    monkeypatch.setattr(insights, "upcoming_fixtures", lambda name: [])
    r = _client().get("/api/teams/Arsenal")
    assert r.status_code == 200
    assert r.json()["upcoming"] == []