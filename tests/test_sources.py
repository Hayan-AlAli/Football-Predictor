from datetime import date, datetime

import pytest

from backend.sources import espn, football_data
from espn_fake import CLUBS, event, season_events

ARS, CHE = ("359", "Arsenal"), ("363", "Chelsea")


def test_parse_event_scheduled_resolves_teams_by_espn_id():
    ev = event(1, datetime(2026, 9, 12, 16, 30), ("361", "Newcastle United"), ("380", "Wolves FC"))
    row, metas = espn.parse_event(ev)
    # 380 is registered as Wolverhampton: the id wins over the unfamiliar spelling
    assert (row["home_team"], row["away_team"]) == ("Newcastle", "Wolverhampton")
    assert row["match_date"] == date(2026, 9, 12)
    assert row["kickoff"] == datetime(2026, 9, 12, 16, 30)
    assert row["status"] == "scheduled"
    assert "home_goals" not in row
    assert metas[0]["badge_url"].endswith("/361.png")
    assert metas[0]["color"] == "#112233"


def test_parse_event_finished_carries_score():
    ev = event(2, datetime(2026, 8, 16, 14), ARS, CHE, "post", "STATUS_FULL_TIME", (3, 1))
    row, _ = espn.parse_event(ev)
    assert row["status"] == "finished"
    assert (row["home_goals"], row["away_goals"]) == (3, 1)


def test_parse_event_unconfirmed_time_has_no_kickoff():
    ev = event(3, datetime(2027, 2, 6, 0, 0), ARS, CHE, time_valid=False)
    row, _ = espn.parse_event(ev)
    assert row["kickoff"] is None and row["match_date"] == date(2027, 2, 6)


@pytest.mark.parametrize("name,state,expected", [
    ("STATUS_POSTPONED", "post", "postponed"),
    ("STATUS_CANCELED", "pre", "postponed"),
    ("STATUS_FIRST_HALF", "in", "in_progress"),
    ("STATUS_SCHEDULED", "pre", "scheduled"),
    ("STATUS_FINAL_PEN", "post", "finished"),
])
def test_status_mapping(name, state, expected):
    ev = event(4, datetime(2026, 10, 3, 15), ARS, CHE, state, name, (1, 1))
    assert espn.parse_event(ev)[0]["status"] == expected


def test_malformed_events_are_skipped():
    assert espn.parse_event({"id": "x", "competitions": [{"competitors": []}]}) is None
    assert espn.parse_event({"id": "y"}) is None


def test_postponed_twin_keeps_the_rescheduled_match():
    original = event(5, datetime(2026, 10, 3, 15), ARS, CHE, "post", "STATUS_POSTPONED")
    moved = event(6, datetime(2026, 10, 21, 19, 45), ARS, CHE)
    rows, _ = espn.parse_events([original, moved], season=2026)
    assert len(rows) == 1
    assert rows[0]["espn_id"] == "6" and rows[0]["status"] == "scheduled"


def test_parse_events_filters_other_seasons():
    ev = event(7, datetime(2026, 5, 20, 15), ARS, CHE, "post", "STATUS_FULL_TIME", (0, 0))
    assert espn.parse_events([ev], season=2026)[0] == []


def test_season_windows_cover_august_to_june():
    windows = espn.season_windows(2026)
    assert windows[0][0] == date(2026, 8, 1)
    assert windows[-1][1] == date(2027, 6, 15)
    for (_, end), (start, _) in zip(windows, windows[1:]):
        assert (start - end).days == 1


def test_fetch_season_full_and_partial(monkeypatch):
    events = season_events()

    def fake_get(params, attempts=3):
        a, b = params["dates"].split("-")
        return {"events": [e for e in events if a <= e["date"][:10].replace("-", "") <= b]}

    monkeypatch.setattr(espn, "_get", fake_get)
    rows, teams, complete = espn.fetch_season(2026)
    assert len(rows) == 380 and len(teams) == len(CLUBS) and complete

    def flaky(params, attempts=3):
        if params["dates"].startswith("202609"):
            raise espn.FeedError("boom")
        return fake_get(params)

    monkeypatch.setattr(espn, "_get", flaky)
    rows, _, complete = espn.fetch_season(2026)
    assert 0 < len(rows) < 380 and not complete

    monkeypatch.setattr(espn, "_get", lambda params, attempts=3: (_ for _ in ()).throw(espn.FeedError("down")))
    with pytest.raises(espn.FeedError):
        espn.fetch_season(2026)


CSV_SAMPLE = """Div,Date,HomeTeam,AwayTeam,FTHG,FTAG
E0,22/08/2026,Hull,Man United,2,0
E0,22/08/2026,Everton,Crystal Palace,2,0
E0,23/08/2026,Arsenal,Chelsea,,
"""


def test_football_data_parse_results_normalizes_and_skips_blanks():
    rows = football_data.parse_results(CSV_SAMPLE, season=2026)
    assert rows == [
        {"match_date": date(2026, 8, 22), "home_team": "Hull", "away_team": "Manchester United",
         "home_goals": 2, "away_goals": 0, "season": 2026},
        {"match_date": date(2026, 8, 22), "home_team": "Everton", "away_team": "Crystal Palace",
         "home_goals": 2, "away_goals": 0, "season": 2026},
    ]


def test_football_data_season_code():
    assert football_data.season_code(2026) == "2627"
    assert football_data.season_code(1999) == "9900"
