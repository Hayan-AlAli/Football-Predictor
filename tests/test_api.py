import pytest
from fastapi.testclient import TestClient

from backend import db, insights, server


@pytest.fixture
def client():
    return TestClient(server.app)


@pytest.fixture
def season():
    ids = db.upsert_matches([
        {"home_team": "Arsenal", "away_team": "Chelsea", "match_date": "2026-08-15",
         "kickoff": "2026-08-15T14:00:00Z", "status": "finished", "home_goals": 2, "away_goals": 0},
        {"home_team": "Everton", "away_team": "Wolves", "match_date": "2026-08-16",
         "status": "finished", "home_goals": 1, "away_goals": 1},
        {"home_team": "Chelsea", "away_team": "Everton", "match_date": "2026-08-22",
         "kickoff": "2026-08-22T16:30:00Z", "status": "finished", "home_goals": 0, "away_goals": 1},
        {"home_team": "Wolves", "away_team": "Arsenal", "match_date": "2099-08-23", "season": 2026,
         "status": "scheduled"},
        {"home_team": "Arsenal", "away_team": "Everton", "match_date": "2026-09-01",
         "status": "postponed"},
    ])
    pred = {"prob_home": 0.6, "prob_draw": 0.25, "prob_away": 0.15, "score": "1-0",
            "exp_home_goals": 1.7, "exp_away_goals": 0.9, "model_version": "rf"}
    db.upsert_predictions([
        {**pred, "match_id": ids[0], "winner": "Arsenal"},
        {**pred, "match_id": ids[1], "winner": "Everton"},
        {**pred, "match_id": ids[3], "winner": "Wolverhampton"},
    ])
    return ids


def test_health_reports_database(client):
    body = client.get("/api/health").json()
    assert body["status"] == "online" and body["database"] in ("sqlite", "postgresql")
    assert client.get("/").json()["status"] == "online"


def test_matches_one_call_has_everything(client, season):
    r = client.get("/api/matches")
    assert r.status_code == 200
    assert "s-maxage" in r.headers["cache-control"]
    body = r.json()
    assert body["season"] == 2026
    by_id = {m["id"]: m for m in body["matches"]}
    won = by_id[season[0]]
    assert won["verdict"] == "CORRECT"
    assert won["actual"] == {"home_goals": 2, "away_goals": 0, "score": "2-0", "winner": "Arsenal"}
    assert won["home_team_info"]["slug"] == "arsenal" and won["home_team_info"]["badge_url"]
    assert won["time"] == "14:00"
    assert by_id[season[1]]["verdict"] == "INCORRECT"
    assert by_id[season[2]]["verdict"] is None and by_id[season[2]]["prediction"] is None
    assert by_id[season[3]]["verdict"] == "PENDING" and by_id[season[3]]["actual"] is None
    # postponed matches sit outside the matchweeks
    assert by_id[season[4]]["gameweek"] is None
    assert body["gameweeks"] == [1, 2, 3]


def test_matches_filter_by_team_slug(client, season):
    body = client.get("/api/matches?team=wolverhampton-wanderers").json()
    assert {m["id"] for m in body["matches"]} == {season[1], season[3]}


def test_teams_lists_the_season_clubs(client, season):
    teams = client.get("/api/teams").json()["teams"]
    assert [t["name"] for t in teams] == ["Arsenal", "Chelsea", "Everton", "Wolverhampton"]
    assert all(t["badge_url"] and t["color"] for t in teams)


def test_teams_falls_back_to_registry_when_empty(client):
    assert len(client.get("/api/teams").json()["teams"]) >= 20


def test_forecast_503_until_synced_then_served_with_team_info(client):
    assert client.get("/api/forecast").status_code == 503
    db.save_forecast(2026, {"generated": "2026-09-28", "season_year": 2026, "n_sims": 10,
                            "season_complete": False, "fixtures_remaining": 1,
                            "standings": [{"team": "Arsenal", "points": 3}],
                            "projected": [{"team": "Chelsea"}]})
    body = client.get("/api/forecast").json()
    assert body["standings"][0]["team_info"]["short_name"] == "ARS"
    assert body["projected"][0]["team_info"]["name"] == "Chelsea"


def test_calibration_from_settled_matches(client, season):
    body = client.get("/api/calibration").json()
    assert body["entries"] == 2 and body["accuracy"] == 0.5


def test_team_profile_accepts_slug_and_name(client, monkeypatch):
    monkeypatch.setattr(insights, "team_profile",
                        lambda df, name, current_elo=None: {"team": name, "seasons": [], "form": [], "elo_history": []})
    for ref in ("wolverhampton-wanderers", "Wolves", "Wolverhampton"):
        body = client.get(f"/api/teams/{ref}").json()
        assert body["team"] == "Wolverhampton" and body["team_info"]["slug"] == "wolverhampton-wanderers"


def test_team_profile_404(client, monkeypatch):
    monkeypatch.setattr(insights, "team_profile", lambda df, name, current_elo=None: None)
    assert client.get("/api/teams/nowhere").status_code == 404


def test_head_to_head_requires_vs(client):
    assert client.get("/api/teams/arsenal/h2h").status_code == 422


def test_predict_is_a_read(client):
    body = client.get("/api/predict?home=arsenal&away=Chelsea").json()
    p = body["prediction"]
    assert abs(p["prob_home"] + p["prob_draw"] + p["prob_away"] - 1) < 1e-6
    assert body["home_team_info"]["name"] == "Arsenal"
    assert client.get("/api/predict?home=arsenal&away=arsenal").status_code == 400
    assert db.load_matches() == []


@pytest.mark.parametrize("path", ["/api/jobs/sync", "/api/jobs/morning", "/api/jobs/evening"])
def test_jobs_require_the_cron_secret(client, monkeypatch, path):
    monkeypatch.setenv("CRON_SECRET", "s3cret")
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"authorization": "Bearer wrong"}).status_code == 401
    from backend import sync
    monkeypatch.setattr(sync, "run_sync", lambda force_forecast=False: {"ok": True, "forced": force_forecast})
    r = client.get(f"{path}?forecast=true", headers={"authorization": "Bearer s3cret"})
    assert r.json() == {"ok": True, "forced": True}
    assert "cache-control" not in r.headers


def test_jobs_locked_without_configured_secret(client, monkeypatch):
    monkeypatch.delenv("CRON_SECRET", raising=False)
    assert client.get("/api/jobs/sync", headers={"authorization": "Bearer "}).status_code == 401


def test_old_write_endpoint_is_gone(client):
    assert client.post("/api/matches/predictions/generate").status_code in (404, 405)
