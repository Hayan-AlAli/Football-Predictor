from backend import db
from backend.gameweeks import assign_gameweeks


def _p(date, home, away, time="14:00"):
    return {"id": f"{date}-{db.match_id(db.season_of(date), home, away)}", "date": date,
            "time": time, "home_team": home, "away_team": away,
            "prediction": {"winner": home}}


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
    gws = assign_gameweeks(wk5 + wk6 + wk7)
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
    gws = assign_gameweeks(mon + tue)
    assert gws[mon[0]["id"]] == 1
    assert {gws[p["id"]] for p in tue} == {2}
