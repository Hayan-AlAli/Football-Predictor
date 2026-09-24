from backend import server, utils_data
from fastapi.testclient import TestClient


def _p(date, home, away, time="14:00"):
    return {"id": utils_data.generate_match_id(date, home, away), "date": date,
            "time": time, "home_team": home, "away_team": away,
            "prediction": {"winner": home}}


def test_canonical_drops_renamed_duplicate_and_rescheduled_row():
    preds = [
        _p("2026-09-14", "Leeds", "Newcastle"),
        _p("2026-09-14", "Leeds United", "Newcastle"),
        _p("2026-09-19", "Manchester City", "Sunderland"),
        _p("2026-09-20", "Manchester City", "Sunderland"),
        _p("2026-09-19", "Leeds", "Crystal Palace"),
        _p("2026-09-20", "Leeds United", "Crystal Palace"),
    ]
    kept = {p["id"] for p in utils_data.canonical_predictions(preds)}
    assert kept == {
        "2026-09-14_leedsunited_newcastle",
        "2026-09-20_manchestercity_sunderland",
        "2026-09-20_leedsunited_crystalpalace",
    }


def _round(dates, teams):
    """10 matches spread over the given dates, teams paired off in order."""
    out = []
    for i in range(10):
        out.append(_p(dates[i % len(dates)], teams[2 * i], teams[2 * i + 1]))
    return out


TEAMS = [f"T{i:02d}" for i in range(20)]


def test_gameweeks_follow_match_dates_not_blocks_of_ten():
    wk5 = _round(["2026-09-18", "2026-09-19", "2026-09-20"], TEAMS)
    # A short round (7 games) then a full one: blocks of ten would mix them.
    wk6 = _round(["2026-10-10"], TEAMS)[:7]
    wk7 = _round(["2026-10-17", "2026-10-18"], TEAMS[::-1])
    gws = utils_data.assign_gameweeks(wk5 + wk6 + wk7)
    by_gw = {}
    for p in wk5 + wk6 + wk7:
        by_gw.setdefault(gws[p["id"]], set()).add(p["date"])
    assert by_gw == {
        1: {"2026-09-18", "2026-09-19", "2026-09-20"},
        2: {"2026-10-10"},
        3: {"2026-10-17", "2026-10-18"},
    }


def test_back_to_back_rounds_split_when_a_team_would_play_twice():
    # Monday night game then a Tuesday midweek round: no empty day between.
    mon = [_p("2026-09-14", "T00", "T01")]
    tue = [_p("2026-09-15", "T01", "T02"), _p("2026-09-15", "T03", "T04")]
    gws = utils_data.assign_gameweeks(mon + tue)
    assert gws[mon[0]["id"]] == 1
    assert {gws[p["id"]] for p in tue} == {2}


def test_matches_all_endpoint_dedupes_and_groups(monkeypatch):
    preds = [
        _p("2026-09-14", "Leeds", "Newcastle"),
        _p("2026-09-14", "Leeds United", "Newcastle"),
        _p("2026-09-19", "Chelsea", "Hull"),
        _p("2026-10-10", "Chelsea", "Bournemouth"),
        _p("2026-10-17", "Everton", "Chelsea"),
    ]
    monkeypatch.setattr(server, "DB_AVAILABLE", True)
    monkeypatch.setattr(server.db, "load_all_predictions", lambda: preds)
    body = TestClient(server.app).get("/api/matches/all").json()
    assert len(body["matches"]) == 4
    assert body["gameweeks"] == [1, 2, 3, 4]
    for gw in body["gameweeks"]:
        chelsea = [m for m in body["matches"] if m["gameweek"] == gw
                   and "Chelsea" in (m["home_team"], m["away_team"])]
        assert len(chelsea) <= 1


def test_results_endpoint_hides_superseded_rows(monkeypatch):
    preds = [
        _p("2026-09-19", "Manchester City", "Sunderland"),
        _p("2026-09-19", "Brighton", "Arsenal"),
        _p("2026-09-20", "Manchester City", "Sunderland"),
    ]
    monkeypatch.setattr(server, "DB_AVAILABLE", True)
    monkeypatch.setattr(server.db, "load_all_predictions", lambda: preds)
    monkeypatch.setattr(server.db, "load_predictions",
                        lambda d: [p for p in preds if p["date"] == d])
    monkeypatch.setattr(server.db, "load_results", lambda d: [
        {"home_team": "Brighton", "away_team": "Arsenal", "home_goals": 3, "away_goals": 0}
    ] if d == "2026-09-19" else [])
    body = TestClient(server.app).get("/api/matches/results?date=2026-09-19").json()
    assert [r["status"] for r in body["results"]] == ["CORRECT"]
