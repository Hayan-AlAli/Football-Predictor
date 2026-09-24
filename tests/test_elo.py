import pytest

from backend import elo


def _m(date, home, away, hg, ag, season=None):
    row = {"date": date, "home_team": home, "away_team": away,
           "home_goals": hg, "away_goals": ag}
    if season is not None:
        row["season"] = season
    return row


# sinceawin.com round of 18-20 Sep 2026: (home, away, score, pre-match
# ratings, published home change). Pins K=30 / home advantage 60 / no
# goal-difference multiplier.
SINCEAWIN_ROUND = [
    ("Brentford", "Chelsea", 3, 0, 1521, 1511, +12),
    ("Tottenham", "Aston Villa", 2, 3, 1395, 1519, -12),
    ("Everton", "Ipswich Town", 1, 0, 1489, 1376, +8),
    ("Newcastle", "Hull", 2, 1, 1488, 1403, +9),
    ("Brighton", "Arsenal", 3, 0, 1520, 1735, +21),
    ("Nottingham Forest", "Coventry City", 0, 1, 1490, 1321, -24),
    ("Leeds United", "Crystal Palace", 0, 0, 1490, 1438, -5),
    ("Manchester City", "Sunderland", 5, 3, 1710, 1454, +4),
    ("Bournemouth", "Liverpool", 0, 1, 1556, 1559, -17),
    ("Fulham", "Manchester United", 1, 1, 1447, 1578, +3),
]


@pytest.mark.parametrize("home,away,hg,ag,pre_h,pre_a,published", SINCEAWIN_ROUND)
def test_match_delta_reproduces_sinceawin(home, away, hg, ag, pre_h, pre_a, published):
    assert round(elo.match_delta(pre_h, pre_a, hg, ag)) == published


def test_replay_is_zero_sum_and_starts_at_1500():
    ratings, pre, _ = elo.replay([
        _m("2020-09-12", "A", "B", 2, 0),
        _m("2020-09-19", "B", "A", 1, 1),
    ])
    assert pre[0] == (1500.0, 1500.0)
    assert sum(ratings.values()) == pytest.approx(3000.0)
    assert ratings["A"] > ratings["B"]


def test_promoted_team_inherits_relegated_average():
    season1 = [_m("2020-09-12", "A", "B", 3, 0, 2020), _m("2020-09-19", "C", "A", 0, 2, 2020),
               _m("2020-09-26", "B", "C", 1, 0, 2020)]
    before, _, _ = elo.replay(season1)
    # C is relegated, D promoted in its place.
    after, pre, _ = elo.replay(season1 + [_m("2021-09-11", "D", "A", 0, 0, 2021),
                                          _m("2021-09-18", "B", "D", 0, 0, 2021)])
    assert pre[3] == (pytest.approx(before["C"]), pytest.approx(before["A"]))
    assert "C" not in after
    assert sum(after.values()) == pytest.approx(4500.0)


def test_explicit_season_beats_calendar_rule():
    """2019/20 ran to 26 July 2020: a July match is still last season."""
    rows = [_m("2019-08-10", "A", "B", 1, 0, 2019), _m("2020-07-26", "B", "A", 1, 0, 2019),
            _m("2020-09-12", "A", "B", 1, 0, 2020)]
    _, _, frame = elo.replay(rows)
    assert list(frame["_season"]) == [2019, 2019, 2020]


def test_seed_is_sinceawin_table():
    as_of, seed = elo.load_seed()
    assert as_of == "2026-09-20"
    assert len(seed) == 20
    assert sum(seed.values()) == 30000
    assert seed["Arsenal"] == 1714 and seed["Coventry City"] == 1345


def test_ratings_apply_only_results_after_seed():
    _, seed = elo.load_seed()
    results = [
        _m("2026-09-19", "Brighton", "Arsenal", 3, 0),        # already in the seed
        _m("2026-09-26", "Arsenal", "Coventry", 0, 1),          # new, raw name
    ]
    ratings = elo.current_ratings(results)
    d = elo.match_delta(seed["Arsenal"], seed["Coventry City"], 0, 1)
    assert ratings["Arsenal"] == pytest.approx(seed["Arsenal"] + d)
    assert ratings["Coventry City"] == pytest.approx(seed["Coventry City"] - d)
    assert ratings["Brighton"] == seed["Brighton"]


def test_duplicate_results_counted_once():
    rows = [_m("2026-09-26", "Arsenal", "Chelsea", 1, 0)] * 2
    once = elo.current_ratings(rows[:1])
    assert elo.current_ratings(rows) == once
