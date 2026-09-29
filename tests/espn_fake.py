"""A synthetic ESPN scoreboard season, shaped like the real API responses."""
from datetime import datetime, timedelta

CLUBS = [  # (espn id, displayName) - the 2026/27 Premier League
    ("359", "Arsenal"), ("362", "Aston Villa"), ("349", "AFC Bournemouth"), ("337", "Brentford"),
    ("331", "Brighton & Hove Albion"), ("363", "Chelsea"), ("388", "Coventry City"),
    ("384", "Crystal Palace"), ("368", "Everton"), ("370", "Fulham"), ("306", "Hull City"),
    ("373", "Ipswich Town"), ("357", "Leeds United"), ("364", "Liverpool"), ("382", "Manchester City"),
    ("360", "Manchester United"), ("361", "Newcastle United"), ("393", "Nottingham Forest"),
    ("366", "Sunderland"), ("367", "Tottenham Hotspur"),
]


def _competitor(side, club, score=None):
    cid, name = club
    return {"homeAway": side, "score": None if score is None else str(score),
            "team": {"id": cid, "displayName": name, "abbreviation": name[:3].upper(),
                     "color": "112233", "alternateColor": "ffffff",
                     "logo": f"https://a.espncdn.com/i/teamlogos/soccer/500/{cid}.png"}}


def event(eid, when, home, away, state="pre", name="STATUS_SCHEDULED", score=None, time_valid=True):
    status = {"type": {"name": name, "state": state, "completed": state == "post"}}
    hs, as_ = score if score else (None, None)
    return {"id": str(eid), "date": when.strftime("%Y-%m-%dT%H:%MZ"), "status": status,
            "competitions": [{"date": when.strftime("%Y-%m-%dT%H:%MZ"), "timeValid": time_valid,
                              "status": status,
                              "competitors": [_competitor("home", home, hs), _competitor("away", away, as_)]}]}


def season_events(season=2026, played_rounds=7):
    """A double round-robin (circle method), one round per Saturday."""
    clubs = list(CLUBS)
    n = len(clubs)
    rounds = []
    order = clubs[:]
    for r in range(n - 1):
        pairs = [(order[i], order[n - 1 - i]) for i in range(n // 2)]
        rounds.append([(a, b) if r % 2 == 0 else (b, a) for a, b in pairs])
        order = [order[0]] + [order[-1]] + order[1:-1]
    rounds += [[(b, a) for a, b in rnd] for rnd in rounds]
    start = datetime(season, 8, 15, 14, 0)
    events, eid = [], 1000
    for r, rnd in enumerate(rounds):
        day = start + timedelta(days=7 * r)
        for i, (home, away) in enumerate(rnd):
            eid += 1
            if r < played_rounds:
                score = ((i + r) % 3, (i * 2 + r) % 2)
                events.append(event(eid, day, home, away, "post", "STATUS_FULL_TIME", score))
            else:
                events.append(event(eid, day, home, away))
    return events
