"""Premier League expected goals (xG) from Understat.

One JSON request per season gives every played match's goals and xG. The
model weighs xG above goals (see backend/dixon_coles.py), and ESPN's
scoreboard has none, so the sync job stores these next to its results.

Understat serves the data to its own pages over XHR: the request needs the
site's cookies (set by loading the league page) and an X-Requested-With
header. That is the same contract the soccerdata library uses.
"""
import logging
from datetime import datetime

import requests

from backend import teams as registry

logger = logging.getLogger(__name__)

BASE_URL = 'https://understat.com'
LEAGUE = 'EPL'
TIMEOUT = 20


class FeedError(RuntimeError):
    pass


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_matches(payload):
    """Understat league JSON -> [{home_team, away_team, match_date, home_xg, away_xg}]
    for played matches with xG on both sides."""
    out = []
    for m in payload.get('dates') or []:
        if not m.get('isResult'):
            continue
        xg = m.get('xG') or {}
        home_xg, away_xg = _float(xg.get('h')), _float(xg.get('a'))
        if home_xg is None or away_xg is None:
            continue
        try:
            played = datetime.strptime(m['datetime'], '%Y-%m-%d %H:%M:%S').date()
            home, away = m['h']['title'], m['a']['title']
        except (KeyError, TypeError, ValueError):
            continue
        out.append({
            'home_team': registry.normalize(home),
            'away_team': registry.normalize(away),
            'match_date': played,
            'home_xg': home_xg,
            'away_xg': away_xg,
        })
    return out


def season_xg(season):
    """Played matches of a season (start year, e.g. 2026 for 2026/27) with xG."""
    session = requests.Session()
    session.headers['User-Agent'] = 'Mozilla/5.0 (football-predictor)'
    try:
        session.get(f'{BASE_URL}/league/{LEAGUE}/{season}', timeout=TIMEOUT).raise_for_status()
        resp = session.get(f'{BASE_URL}/getLeagueData/{LEAGUE}/{season}', timeout=TIMEOUT,
                           headers={'X-Requested-With': 'XMLHttpRequest'})
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError) as e:
        raise FeedError(f'Understat {LEAGUE} {season}: {e}') from e
    matches = parse_matches(payload)
    logger.info(f'Understat: xG for {len(matches)} played matches in {season}')
    return matches
