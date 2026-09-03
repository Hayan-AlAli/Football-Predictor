import time

import pandas as pd

from backend import data_manager


def test_fetch_upcoming_matches_caches_non_empty(monkeypatch):
    calls = {"n": 0}

    def fake_scrape():
        calls["n"] += 1
        return pd.DataFrame([{"date": pd.Timestamp.now(tz="UTC")}])

    monkeypatch.setattr(data_manager, "_scrape_upcoming_matches", fake_scrape)
    monkeypatch.setattr(data_manager, "_upcoming_cache", None)
    monkeypatch.setattr(data_manager, "_upcoming_cache_ts", 0.0)

    first = data_manager.fetch_upcoming_matches()
    second = data_manager.fetch_upcoming_matches()
    assert calls["n"] == 1
    assert len(first) == 1
    assert len(second) == 1


def test_fetch_upcoming_matches_caches_empty_briefly(monkeypatch):
    calls = {"n": 0}

    def fake_scrape():
        calls["n"] += 1
        return pd.DataFrame()

    monkeypatch.setattr(data_manager, "_scrape_upcoming_matches", fake_scrape)
    monkeypatch.setattr(data_manager, "_upcoming_cache", None)
    monkeypatch.setattr(data_manager, "_upcoming_cache_ts", 0.0)

    data_manager.fetch_upcoming_matches()
    data_manager.fetch_upcoming_matches()
    assert calls["n"] == 1


def test_fetch_upcoming_matches_cache_expires(monkeypatch):
    calls = {"n": 0}

    def fake_scrape():
        calls["n"] += 1
        return pd.DataFrame([{"date": pd.Timestamp.now(tz="UTC")}])

    monkeypatch.setattr(data_manager, "_scrape_upcoming_matches", fake_scrape)
    monkeypatch.setattr(data_manager, "_upcoming_cache", None)
    monkeypatch.setattr(data_manager, "_upcoming_cache_ts", 0.0)

    now = [time.time()]

    def fake_time():
        return now[0]

    monkeypatch.setattr(data_manager.time, "time", fake_time)

    data_manager.fetch_upcoming_matches()
    now[0] += data_manager._UPCOMING_CACHE_TTL + 1
    data_manager.fetch_upcoming_matches()
    assert calls["n"] == 2


def test_fetch_upcoming_matches_cache_result_not_mutated_by_caller(monkeypatch):
    def fake_scrape():
        return pd.DataFrame([{"date": pd.Timestamp.now(tz="UTC")}])

    monkeypatch.setattr(data_manager, "_scrape_upcoming_matches", fake_scrape)
    monkeypatch.setattr(data_manager, "_upcoming_cache", None)
    monkeypatch.setattr(data_manager, "_upcoming_cache_ts", 0.0)

    result = data_manager.fetch_upcoming_matches()
    result["date_str"] = "2099-01-01"
    cached = data_manager.fetch_upcoming_matches()
    assert "date_str" not in cached.columns


def test_scrape_upcoming_matches_survives_dead_elo(monkeypatch):
    import soccerdata

    future = pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=3)
    schedule = pd.DataFrame([{
        "date": future,
        "home_team": "Arsenal",
        "away_team": "Chelsea",
    }])

    class FakeESPN:
        def __init__(self, *a, **k):
            pass

        def read_schedule(self):
            return schedule

    class DeadClubElo:
        def __init__(self, *a, **k):
            pass

        def read_by_date(self, *a, **k):
            raise ConnectionError("api.clubelo.com is down")

    monkeypatch.setattr(soccerdata, "ESPN", FakeESPN)
    monkeypatch.setattr(soccerdata, "ClubElo", DeadClubElo)

    result = data_manager._scrape_upcoming_matches()
    assert not result.empty
    assert len(result) == 1
    # Offline fallback Elo, not the flat 1500 that a dead API used to force.
    assert result.iloc[0]["home_elo"] != 1500
    assert result.iloc[0]["home_elo"] == data_manager.predictor.training_elo_lookup()["Arsenal"]