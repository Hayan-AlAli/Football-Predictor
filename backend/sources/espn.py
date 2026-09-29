"""Premier League fixtures, results and club metadata from ESPN's public
scoreboard API - plain JSON over HTTPS, no key, no scraping library.

One pass over a season's scoreboard gives every match with its kickoff,
status and score, plus each club's ESPN id, badge and colours. That replaces
three separate feeds (soccerdata's ESPN schedule for fixtures, Understat and
football-data.co.uk for results) and keeps team identity id-based.
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

import requests

from backend import teams as registry
from backend.db import season_of

logger = logging.getLogger(__name__)

SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard"
TIMEOUT = 15


class FeedError(RuntimeError):
    pass


# Months are fetched concurrently; one shared session keeps the TLS
# connections to ESPN alive between them.
PARALLEL_REQUESTS = 6
_session = requests.Session()
_session.headers['User-Agent'] = 'football-predictor/2.0'
_session.mount('https://', requests.adapters.HTTPAdapter(pool_maxsize=PARALLEL_REQUESTS))


def _get(params, attempts=3):
    for attempt in range(attempts):
        try:
            resp = _session.get(SCOREBOARD_URL, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as e:
            if attempt == attempts - 1:
                raise FeedError(f"ESPN scoreboard {params}: {e}") from e
            time.sleep(1.5 * (attempt + 1))


def season_windows(season):
    """Month-sized date ranges covering a season (Aug to early June).

    Monthly chunks keep each response well under the API's event cap.
    """
    start = date(season, 8, 1)
    end = date(season + 1, 6, 15)
    windows = []
    cur = start
    while cur <= end:
        nxt = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        windows.append((cur, min(nxt - timedelta(days=1), end)))
        cur = nxt
    return windows


def _status(event):
    st = (event.get('status') or {}).get('type') or {}
    name = (st.get('name') or '').upper()
    state = st.get('state')
    if any(word in name for word in ('POSTPONED', 'CANCELED', 'CANCELLED', 'SUSPENDED', 'ABANDONED')):
        return 'postponed'
    if state == 'post' and st.get('completed', True):
        return 'finished'
    if state == 'in':
        return 'in_progress'
    return 'scheduled'


def _score(competitor):
    raw = competitor.get('score')
    if isinstance(raw, dict):
        raw = raw.get('value', raw.get('displayValue'))
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _hex(value):
    if not value:
        return None
    value = str(value).lstrip('#')
    return f"#{value.upper()}" if len(value) == 6 else None


def _team(competitor):
    t = competitor.get('team') or {}
    canon = registry.from_espn_id(t.get('id')) or registry.normalize(t.get('displayName') or t.get('name'))
    logo = t.get('logo')
    if not logo and t.get('logos'):
        logo = t['logos'][0].get('href')
    return canon, {
        'name': canon,
        'espn_id': str(t['id']) if t.get('id') else None,
        'badge_url': logo,
        'color': _hex(t.get('color')),
        'alt_color': _hex(t.get('alternateColor')),
    }


def parse_event(event):
    """One scoreboard event -> (match row, [team rows]) or None if malformed."""
    comp = (event.get('competitions') or [{}])[0]
    sides = {c.get('homeAway'): c for c in comp.get('competitors') or []}
    if 'home' not in sides or 'away' not in sides:
        return None
    home, home_meta = _team(sides['home'])
    away, away_meta = _team(sides['away'])
    if not home or not away:
        return None
    raw_date = comp.get('date') or event.get('date')
    try:
        kickoff = datetime.fromisoformat(raw_date.replace('Z', '+00:00')).astimezone(timezone.utc)
    except (AttributeError, ValueError):
        return None
    status = _status(comp if comp.get('status') else event)
    row = {
        'home_team': home,
        'away_team': away,
        'match_date': kickoff.date(),
        # timeValid=false means ESPN is holding a placeholder slot (TV picks pending).
        'kickoff': kickoff.replace(tzinfo=None) if comp.get('timeValid', True) else None,
        'status': status,
        'espn_id': str(event.get('id')) if event.get('id') else None,
    }
    if status in ('finished', 'in_progress'):
        row['home_goals'] = _score(sides['home'])
        row['away_goals'] = _score(sides['away'])
    if status == 'finished' and (row['home_goals'] is None or row['away_goals'] is None):
        row['status'] = 'scheduled'
    return row, [home_meta, away_meta]


_STATUS_RANK = {'finished': 3, 'in_progress': 2, 'scheduled': 1, 'postponed': 0}


def parse_events(events, season=None):
    """Parse and dedupe a batch of events.

    A postponed match stays in the feed next to its rescheduled replacement;
    both are the same season pairing, so keep the one that is (or will be)
    played: finished > live > scheduled > postponed, then the later date.
    """
    best, team_meta = {}, {}
    for event in events:
        parsed = parse_event(event)
        if parsed is None:
            continue
        row, metas = parsed
        row_season = season_of(row['match_date'])
        if season is not None and row_season != season:
            continue
        key = (row_season, row['home_team'], row['away_team'])
        rank = (_STATUS_RANK[row['status']], row['match_date'])
        if key not in best or rank > best[key][0]:
            best[key] = (rank, row)
        for m in metas:
            team_meta[m['name']] = m
    return [row for _, row in best.values()], list(team_meta.values())


def fetch_season(season):
    """(matches, teams, complete) for a whole season.

    Raises FeedError when no window could be read at all; a failed month is
    logged and skipped, and `complete` is False so callers know not to treat
    the missing fixtures as removed."""
    windows = season_windows(season)

    def fetch(window):
        start, end = window
        try:
            return _get({'dates': f"{start:%Y%m%d}-{end:%Y%m%d}", 'limit': 500}).get('events') or []
        except FeedError as e:
            logger.warning(str(e))
            return None

    # All months at once: the pull takes about as long as its slowest month
    # instead of the sum of all of them. Results keep the calendar order.
    with ThreadPoolExecutor(max_workers=PARALLEL_REQUESTS) as pool:
        pages = list(pool.map(fetch, windows))
    failures = sum(page is None for page in pages)
    events = [e for page in pages if page for e in page]
    if failures == len(windows):
        raise FeedError(f"ESPN unavailable for season {season}")
    matches, team_rows = parse_events(events, season=season)
    logger.info(f"ESPN: {len(matches)} matches, {len(team_rows)} clubs for {season} "
                f"({failures} of {len(windows)} windows failed)")
    return matches, team_rows, failures == 0
