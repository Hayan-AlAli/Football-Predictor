import sqlite3
from datetime import date

from backend import db


def _fixture(home, away, day, **extra):
    return {"home_team": home, "away_team": away, "match_date": day, **extra}


def test_match_id_is_stable_across_reschedules_and_spellings():
    a = db.match_id(db.season_of("2026-10-03"), "Wolves", "Newcastle United")
    b = db.match_id(db.season_of("2026-10-21"), "Wolverhampton", "Newcastle")
    assert a == b == "2026-wolverhampton-wanderers-newcastle-united"
    # the return fixture is a different match
    assert db.match_id(2026, "Newcastle", "Wolves") != a


def test_season_boundary():
    assert db.season_of("2026-08-01") == 2026
    assert db.season_of("2026-07-31") == 2025
    assert db.season_of(date(2027, 5, 20)) == 2026


def test_upsert_only_touches_supplied_columns():
    [mid] = db.upsert_matches([_fixture("Arsenal", "Chelsea", "2026-10-03",
                                        kickoff="2026-10-03T16:30:00Z", status="scheduled")])
    # a results-only row (football-data fallback) must not erase the kickoff
    db.upsert_matches([_fixture("Arsenal", "Chelsea", "2026-10-03",
                                status="finished", home_goals=2, away_goals=2)])
    [m] = db.load_matches()
    assert m["id"] == mid
    assert m["time"] == "16:30" and m["kickoff"] == "2026-10-03T16:30:00Z"
    assert (m["status"], m["home_goals"], m["away_goals"]) == ("finished", 2, 2)


def test_reschedule_moves_the_same_row():
    db.upsert_matches([_fixture("Arsenal", "Chelsea", "2026-10-03", status="scheduled")])
    db.upsert_matches([_fixture("Arsenal", "Chelsea", "2026-10-21", status="scheduled")])
    rows = db.load_matches()
    assert len(rows) == 1 and rows[0]["date"] == "2026-10-21"


def test_load_matches_filters_and_joins_predictions():
    ids = db.upsert_matches([
        _fixture("Arsenal", "Chelsea", "2026-08-16", status="finished", home_goals=1, away_goals=0),
        _fixture("Chelsea", "Everton", "2026-09-20", status="scheduled"),
        _fixture("Arsenal", "Everton", "2025-09-20", status="finished", home_goals=0, away_goals=0),
    ])
    db.upsert_predictions([{"match_id": ids[0], "prob_home": 0.6, "prob_draw": 0.25,
                            "prob_away": 0.15, "winner": "Arsenal", "score": "1-0",
                            "model_version": "rf", "features": {"elo_gap": 90}}])
    season = db.load_matches(season=2026)
    assert [m["id"] for m in season] == ids[:2]
    assert season[0]["prediction"]["features"] == {"elo_gap": 90}
    assert season[1]["prediction"] is None
    assert [m["id"] for m in db.load_matches(team="Everton")] == [ids[2], ids[1]]
    assert [m["id"] for m in db.load_matches(status="finished", season=2026)] == ids[:1]
    assert db.latest_season() == 2026


def test_results_since_is_flat_and_strictly_after():
    db.upsert_matches([
        _fixture("Arsenal", "Chelsea", "2026-09-20", status="finished", home_goals=1, away_goals=0),
        _fixture("Everton", "Fulham", "2026-09-21", status="finished", home_goals=2, away_goals=2),
        _fixture("Fulham", "Everton", "2026-12-21", status="scheduled"),
    ])
    rows = db.results_since("2026-09-20")
    assert rows == [{"date": "2026-09-21", "home_team": "Everton", "away_team": "Fulham",
                     "home_goals": 2, "away_goals": 2, "season": 2026}]


def test_delete_scheduled_except_never_touches_results():
    ids = db.upsert_matches([
        _fixture("Arsenal", "Chelsea", "2026-08-16", status="finished", home_goals=1, away_goals=0),
        _fixture("Chelsea", "Everton", "2026-09-20", status="scheduled"),
        _fixture("Everton", "Arsenal", "2026-09-27", status="scheduled"),
    ])
    db.upsert_predictions([{"match_id": ids[1], "prob_home": 0.5}])
    assert db.delete_scheduled_except(2026, [ids[2]]) == 1
    assert [m["id"] for m in db.load_matches()] == [ids[0], ids[2]]


def test_forecasts_keep_newest():
    db.save_forecast(2026, {"generated": "a"})
    db.save_forecast(2026, {"generated": "b"})
    assert db.latest_forecast() == {"generated": "b"}


def test_team_overrides_feed_team_info():
    db.upsert_teams([{"name": "Arsenal", "badge_url": "https://x/ars.png", "color": "#123456"},
                     {"name": "Nowhere Rovers", "badge_url": "https://x/now.png", "color": "#654321"}])
    db._team_overrides_cached.cache_clear()
    info = db.team_info("Arsenal F.C.")
    assert info["badge_url"] == "https://x/ars.png" and info["color"] == "#EF0107"
    assert info["short_name"] == "ARS"
    # an unregistered club (say, newly promoted) is fully described by the feed
    new = db.team_info("Nowhere Rovers")
    assert new["badge_url"] == "https://x/now.png" and new["color"] == "#654321"


def test_job_log():
    db.log_run("sync", True, {"matches": 3})
    db.log_run("sync", False, {"error": "x"})
    assert db.last_runs()["sync"]["ok"] is False


def test_legacy_tables_migrate_once(tmp_path):
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.executescript("""
    CREATE TABLE predictions (id TEXT PRIMARY KEY, match_date DATE, match_time TEXT,
        home_team TEXT, away_team TEXT, prob_home REAL, prob_draw REAL, prob_away REAL,
        score TEXT, winner TEXT, home_goals REAL, away_goals REAL, home_elo REAL, away_elo REAL,
        created_at TEXT);
    CREATE TABLE results (match_date DATE, home_team TEXT, away_team TEXT,
        home_goals REAL, away_goals REAL);
    CREATE TABLE fixtures (id TEXT, match_date DATE, match_time TEXT, home_team TEXT,
        away_team TEXT, gameweek INT, home_elo REAL, away_elo REAL);
    CREATE TABLE forecast_cache (match_date DATE PRIMARY KEY, payload TEXT, created_at TEXT);
    CREATE TABLE teams (name TEXT PRIMARY KEY, short_name TEXT, badge_url TEXT);
    INSERT INTO teams VALUES ('Arsenal', 'ARS', 'https://old/badges/50/t3.png');
    -- a renamed twin: the later, canonically named row is the real one
    INSERT INTO predictions VALUES ('a','2026-08-16','14:00','Leeds','Arsenal',
        0.2,0.3,0.5,'0-1','Arsenal',0.9,1.4,1480,1700,NULL);
    INSERT INTO predictions VALUES ('b','2026-08-23','14:00','Leeds United','Arsenal',
        0.25,0.3,0.45,'1-1','Arsenal',1.0,1.3,1480,1700,NULL);
    INSERT INTO predictions VALUES ('c','2026-08-30','15:00','Wolves','Everton',
        0.4,0.3,0.3,'1-0','Wolves',1.3,1.0,1450,1490,NULL);
    INSERT INTO results VALUES ('2026-08-23','Leeds United','Arsenal',2,1);
    INSERT INTO fixtures VALUES ('f','2026-10-04','16:30','Wolves','Chelsea',7,1400,1500);
    INSERT INTO forecast_cache VALUES ('2026-09-28','{"season_year": 2026, "projected": []}',NULL);
    """)
    conn.commit()
    conn.close()

    db.reset_for_tests(f"sqlite:///{path}")
    rows = {m["id"]: m for m in db.load_matches()}
    assert set(rows) == {"2026-leeds-united-arsenal", "2026-wolverhampton-wanderers-everton",
                         "2026-wolverhampton-wanderers-chelsea"}
    leeds = rows["2026-leeds-united-arsenal"]
    assert (leeds["status"], leeds["home_goals"], leeds["away_goals"]) == ("finished", 2, 1)
    assert leeds["prediction"]["score"] == "1-1" and leeds["prediction"]["model_version"] == "legacy-rf"
    assert rows["2026-wolverhampton-wanderers-everton"]["prediction"]["winner"] == "Wolverhampton"
    assert rows["2026-wolverhampton-wanderers-chelsea"]["time"] == "16:30"
    assert db.latest_forecast() == {"season_year": 2026, "projected": []}
    # the old teams table is upgraded in place and its stale crests dropped
    db._team_overrides_cached.cache_clear()
    assert "espncdn" in db.team_info("Arsenal")["badge_url"]
    db.upsert_teams([{"name": "Arsenal", "espn_id": "359", "color": "#EF0107"}])

    # a second start must not migrate again
    db.reset_for_tests(f"sqlite:///{path}")
    assert len(db.load_matches()) == 3
