from datetime import datetime, timezone

import pytest

from backend import db, elo, predictor, sync
from backend.sources import espn, football_data
from espn_fake import event, season_events

NOW = datetime(2026, 9, 29, 6, 0, tzinfo=timezone.utc)  # after 7 played rounds


@pytest.fixture
def feed(monkeypatch):
    """A mutable ESPN season served through the real parser."""
    events = season_events(played_rounds=7)

    def fake_get(params, attempts=3):
        a, b = params["dates"].split("-")
        return {"events": [e for e in events if a <= e["date"][:10].replace("-", "") <= b]}

    monkeypatch.setattr(espn, "_get", fake_get)
    # The Elo model keeps these tests fast; the RF path has its own tests.
    monkeypatch.setattr(predictor, "predict_matches",
                        lambda ms: [predictor.elo_prediction(m["home_team"], m["away_team"],
                                                             m.get("home_elo"), m.get("away_elo"))
                                    for m in ms])
    return events


def test_first_sync_loads_season_predicts_horizon_and_forecasts(feed):
    summary = sync.run_sync(now=NOW)
    assert summary["source"] == "espn"
    assert summary["matches"] == 380 and summary["new_results"] == 70
    assert summary["forecast"] == "regenerated"
    rows = db.load_matches(season=2026)
    assert sum(m["status"] == "finished" for m in rows) == 70
    predicted = [m for m in rows if m["prediction"]]
    assert len(predicted) == summary["predictions"] == 40  # 4 rounds inside 28 days
    assert all(m["status"] == "scheduled" for m in predicted)
    assert all(m["prediction"]["model_version"] == "elo-poisson" for m in predicted)
    forecast = db.latest_forecast()
    assert forecast["fixtures_remaining"] == 310 and len(forecast["standings"]) == 20
    assert db.last_runs()["sync"]["ok"] is True
    # feed crests are stored; the curated colour is kept
    assert db.team_info("Arsenal")["badge_url"].endswith("/359.png")
    assert db.team_info("Arsenal")["color"] == "#EF0107"


def test_predictions_freeze_at_kickoff(feed, monkeypatch):
    sync.run_sync(now=NOW)
    before = {m["id"]: m["prediction"] for m in db.load_matches() if m["prediction"]}
    # Round 8 (3 Oct) is played; a week later the sync must not re-call it.
    later = datetime(2026, 10, 5, 6, 0, tzinfo=timezone.utc)
    for e in feed:
        if e["date"].startswith("2026-10-03"):
            for c in e["competitions"][0]["competitors"]:
                c["score"] = "1"
            e["status"] = e["competitions"][0]["status"] = {
                "type": {"name": "STATUS_FULL_TIME", "state": "post", "completed": True}}
    elo_call = predictor.predict_matches
    monkeypatch.setattr(predictor, "predict_matches",
                        lambda ms: [{**p, "prob_home": 0.99} for p in elo_call(ms)])
    summary = sync.run_sync(now=later)
    assert summary["new_results"] == 10
    after = {m["id"]: m for m in db.load_matches()}
    played = [i for i, m in after.items() if m["date"] == "2026-10-03"]
    assert len(played) == 10
    for i in played:
        assert after[i]["prediction"] == before[i]          # frozen call
        assert after[i]["status"] == "finished"
    upcoming = [m for m in after.values() if m["prediction"] and m["status"] == "scheduled"]
    assert upcoming and all(m["prediction"]["prob_home"] == 0.99 for m in upcoming)


def test_removed_fixture_is_pruned_only_on_a_complete_pull(feed, monkeypatch):
    sync.run_sync(now=NOW)
    gone = feed.pop()  # last-round match vanishes from the feed
    summary = sync.run_sync(now=NOW)
    assert summary["removed"] == 1
    assert len(db.load_matches()) == 379
    feed.append(gone)
    real_get = espn._get

    def partial(params, attempts=3):
        if params["dates"].startswith("202702"):
            raise espn.FeedError("one month down")
        return real_get(params)

    monkeypatch.setattr(espn, "_get", partial)
    feed.pop(0)  # would look removed, but the pull is partial
    summary = sync.run_sync(now=NOW)
    assert summary["removed"] == 0


def test_rescheduled_match_keeps_one_row(feed):
    sync.run_sync(now=NOW)
    target = next(e for e in feed if e["date"].startswith("2026-10-10"))
    comp = target["competitions"][0]
    home, away = (c["team"] for c in comp["competitors"])
    target["status"] = comp["status"] = {"type": {"name": "STATUS_POSTPONED", "state": "post", "completed": False}}
    feed.append(event(99999, datetime(2026, 10, 14, 19, 45),
                      (home["id"], home["displayName"]), (away["id"], away["displayName"])))
    sync.run_sync(now=NOW)
    ids = [m["id"] for m in db.load_matches()]
    assert len(ids) == len(set(ids)) == 380
    moved = [m for m in db.load_matches() if m["date"] == "2026-10-14"]
    assert len(moved) == 1 and moved[0]["prediction"] is not None
    assert not [m for m in db.load_matches() if m["status"] == "postponed"]


def test_espn_down_falls_back_to_football_data_results(monkeypatch):
    monkeypatch.setattr(espn, "fetch_season",
                        lambda season: (_ for _ in ()).throw(espn.FeedError("down")))
    monkeypatch.setattr(football_data, "season_results", lambda season: [
        {"match_date": datetime(2026, 8, 16).date(), "home_team": "Arsenal",
         "away_team": "Chelsea", "home_goals": 2, "away_goals": 1, "season": 2026},
    ])
    summary = sync.run_sync(now=NOW)
    assert summary["source"] == "football-data" and summary["removed"] == 0
    [m] = db.load_matches()
    assert (m["status"], m["home_goals"]) == ("finished", 2)


def test_failed_sync_is_logged_and_raised(monkeypatch):
    monkeypatch.setattr(sync, "pull_matches", lambda season: (_ for _ in ()).throw(RuntimeError("x")))
    with pytest.raises(RuntimeError):
        sync.run_sync(now=NOW)
    assert db.last_runs()["sync"]["ok"] is False


def test_sync_with_the_real_model(monkeypatch):
    """No stub: the batched forest predicts the horizon and the forecast."""
    events = season_events(played_rounds=7)
    monkeypatch.setattr(espn, "_get", lambda params, attempts=3: {"events": [
        e for e in events
        if params["dates"][:8] <= e["date"][:10].replace("-", "") <= params["dates"][9:]]})
    summary = sync.run_sync(now=NOW)
    assert summary["predictions"] == 40 and summary["forecast"] == "regenerated"
    assert summary["seconds"] < 30
    versions = {m["prediction"]["model_version"] for m in db.load_matches() if m["prediction"]}
    assert versions == {predictor.MODEL_VERSION}


def test_forecast_due_policy():
    assert sync.forecast_due(False, False, weekday=3)
    assert sync.forecast_due(True, True, weekday=3)
    assert sync.forecast_due(True, False, weekday=0)
    assert not sync.forecast_due(True, False, weekday=3)


FLAT = {"prob_home": 0.33, "prob_draw": 0.34, "prob_away": 0.33, "exp_home_goals": 1.2,
        "exp_away_goals": 1.2, "score": "1-1", "winner": "Draw", "model_version": "legacy-rf"}


def test_placeholder_calls_on_played_matches_are_rebuilt(feed):
    sync.run_sync(now=NOW)
    played = {m["id"]: m for m in db.load_matches() if m["status"] == "finished"}
    broken = [i for i, m in played.items() if m["date"] in ("2026-09-12", "2026-09-19")]
    real = next(i for i, m in played.items() if m["date"] == "2026-09-05")
    db.upsert_predictions([{"match_id": i, **FLAT} for i in broken]
                          + [{"match_id": real, **FLAT, "prob_home": 0.6, "prob_away": 0.06}])

    summary = sync.run_sync(now=NOW)
    assert summary["repaired"] == len(broken) == 20
    after = {m["id"]: m for m in db.load_matches()}
    results = db.results_since("2026-09-11")
    for i in broken:
        pred, m = after[i]["prediction"], after[i]
        assert not sync.is_placeholder(pred)
        assert pred["model_version"] == "elo-poisson" + sync.REBUILT_SUFFIX
        # Elo as it stood before that match day, not today's.
        assert pred["home_elo"] == int(elo.ratings_before(m["date"], results)[m["home_team"]])
    assert after[real]["prediction"]["prob_home"] == 0.6      # real calls stay frozen
    assert sync.run_sync(now=NOW)["repaired"] == 0            # idempotent


def test_placeholder_detection():
    assert sync.is_placeholder(FLAT)
    assert sync.is_placeholder({"prob_home": None, "prob_draw": None, "prob_away": None})
    assert not sync.is_placeholder({"prob_home": 0.4, "prob_draw": 0.3, "prob_away": 0.3})
