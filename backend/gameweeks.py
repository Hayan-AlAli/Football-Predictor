"""Matchweek numbers derived from match dates."""
from datetime import datetime

from backend import utils


def assign_gameweeks(matches):
    """Map match id -> matchweek number, built from the match dates.

    A matchweek is a run of consecutive match days; a new one starts after
    a day with no games, or on a day where a team would play a second time
    in the current one (a Tuesday round right after a Monday game). A whole
    day always lands in one matchweek. Numbering follows the fixtures as
    listed, so a feed missing a whole round shifts the numbers after it."""
    by_date = {}
    for p in matches:
        by_date.setdefault(p['date'], []).append(p)
    gws = {}
    gw, teams, prev = 0, set(), None
    for date_str in sorted(by_date):
        day = by_date[date_str]
        day_teams = {utils.normalize_team_name(t)
                     for p in day for t in (p['home_team'], p['away_team'])}
        d = datetime.strptime(date_str, '%Y-%m-%d')
        if prev is None or (d - prev).days > 1 or teams & day_teams:
            gw += 1
            teams = set()
        teams |= day_teams
        prev = d
        for p in day:
            gws[p['id']] = gw
    return gws
