"""Premier League results from football-data.co.uk's season CSVs.

Two uses: the full history since 1995/96 that the Elo replay needs, and a
results fallback for the sync job when ESPN is unreachable.
"""
import io
import time
from datetime import datetime

import pandas as pd
import requests

from backend import teams as registry

BASE_URL = "https://football-data.co.uk/mmz4281"
# First 20-team season. Starting here reproduces sinceawin.com's ratings to
# within 0.5 points; including the 22-team 1993-95 seasons drifts ~13.
FIRST_SEASON = 1995


def season_code(season):
    return f"{str(season)[2:]}{str(season + 1)[2:]}"


def season_csv(season, attempts=3):
    """Raw E0.csv text for one season (start year), retried on timeouts."""
    url = f"{BASE_URL}/{season_code(season)}/E0.csv"
    for attempt in range(attempts):
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            return resp.content.decode('latin1')
        except requests.RequestException:
            if attempt == attempts - 1:
                raise
            time.sleep(2 * (attempt + 1))


def parse_results(text, season=None):
    """E0.csv text -> [{match_date, home_team, away_team, home_goals, away_goals}]."""
    raw = pd.read_csv(io.StringIO(text),
                      usecols=lambda c: c in ('Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG'),
                      on_bad_lines='skip')
    raw = raw.dropna(subset=['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG'])
    dates = pd.to_datetime(raw['Date'], dayfirst=True, format='mixed', errors='coerce')
    rows = []
    for d, r in zip(dates, raw.itertuples()):
        if pd.isna(d):
            continue
        rows.append({
            'match_date': d.date(),
            'home_team': registry.normalize(str(r.HomeTeam)),
            'away_team': registry.normalize(str(r.AwayTeam)),
            'home_goals': int(r.FTHG),
            'away_goals': int(r.FTAG),
            **({'season': season} if season is not None else {}),
        })
    return rows


def season_results(season):
    return parse_results(season_csv(season), season=season)


def historical_results(last_season=None):
    """Every Premier League result since 1995/96 as a DataFrame
    (date, home_team, away_team, home_goals, away_goals, season).

    The Elo system (backend/elo.py) needs the full history: ratings are a
    running total, so starting later gives different numbers.
    """
    if last_season is None:
        now = datetime.now()
        last_season = now.year if now.month >= 8 else now.year - 1
    rows = []
    for season in range(FIRST_SEASON, last_season + 1):
        rows.extend(season_results(season))
    df = pd.DataFrame(rows).rename(columns={'match_date': 'date'})
    df['date'] = pd.to_datetime(df['date'])
    return df
