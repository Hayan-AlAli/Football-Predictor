"""Premier League Elo ratings, computed in-house.

Same system as sinceawin.com/elo-ratings/premier-league (verified: replaying
every Premier League result since 1995/96, the first 20-team season, through
the rules below reproduces their published table to within 0.5 points):

- every team starts at 1500 in the first season replayed;
- expected home score E = 1 / (1 + 10 ** (-(home - away + HOME_ADVANTAGE) / 400));
- after each match both sides move by K * (S - E), S = 1 / 0.5 / 0 for the
  home side (no goal-difference multiplier);
- ratings carry over between seasons unchanged; promoted teams take the
  average rating of the teams they replace, so the league always sums to
  1500 * teams.

Live ratings start from SEED_PATH (sinceawin's table on its `as_of` date) and
apply every stored result played after that date.
"""
import json
import os
import time

import pandas as pd

from backend import utils

K = 30
HOME_ADVANTAGE = 60
BASE = 1500.0
LEAGUE_SIZE = 20

SEED_PATH = os.path.join(os.path.dirname(__file__), 'elo_seed.json')

_CACHE_TTL = 3600
_cache = None
_cache_ts = 0.0


def season_year_of(ts):
    return ts.year if ts.month >= 8 else ts.year - 1


def expected_home(home_elo, away_elo):
    return 1.0 / (1.0 + 10 ** (-(home_elo - away_elo + HOME_ADVANTAGE) / 400.0))


def match_delta(home_elo, away_elo, home_goals, away_goals):
    """Rating points the home side gains (the away side loses the same)."""
    if home_goals > away_goals:
        score = 1.0
    elif home_goals == away_goals:
        score = 0.5
    else:
        score = 0.0
    return K * (score - expected_home(home_elo, away_elo))


def _results_frame(results):
    cols = ['date', 'home_team', 'away_team', 'home_goals', 'away_goals']
    df = results.copy() if isinstance(results, pd.DataFrame) else pd.DataFrame(list(results), columns=None)
    for col in cols + ['season']:
        if col not in df.columns:
            df[col] = None
    df = df[cols + ['season']]
    df = df.dropna(subset=['home_goals', 'away_goals'])
    df['date'] = pd.to_datetime(df['date'], utc=True).dt.tz_localize(None)
    df['home_team'] = df['home_team'].apply(utils.normalize_team_name)
    df['away_team'] = df['away_team'].apply(utils.normalize_team_name)
    df['_day'] = df['date'].dt.date
    df = df.drop_duplicates(subset=['_day', 'home_team', 'away_team'], keep='last')
    df = df.sort_values('date', kind='stable').reset_index(drop=True)
    # An explicit season wins: the calendar rule mis-files seasons that
    # ran past July (2019/20 finished on 26 July 2020).
    derived = df['date'].apply(season_year_of)
    df['_season'] = pd.to_numeric(df['season'], errors='coerce').fillna(derived).astype(int)
    return df.drop(columns='season')


def _relegated(season_rows, n):
    """The n lowest teams by points (then goal difference) in a season."""
    table = {}
    for r in season_rows.itertuples():
        for team, gf, ga in ((r.home_team, r.home_goals, r.away_goals),
                             (r.away_team, r.away_goals, r.home_goals)):
            pts, gd = table.get(team, (0, 0))
            table[team] = (pts + (3 if gf > ga else 1 if gf == ga else 0), gd + gf - ga)
    return sorted(table, key=lambda t: table[t])[:n]


def replay(results, ratings=None):
    """Run results through the Elo system.

    results: rows/dicts with date, home_team, away_team, home_goals,
    away_goals and optionally season (start year). ratings: starting ratings (defaults to everyone at 1500).
    Returns (final_ratings, pre_match) where pre_match is a list of
    (home_elo, away_elo) before each match, in the returned frame's order.
    """
    df = _results_frame(results)
    ratings = dict(ratings or {})
    pre_match = []
    prev_teams = set(ratings)
    prev_rows = None
    for season, rows in df.groupby('_season', sort=True):
        teams = set(rows['home_team']) | set(rows['away_team'])
        newcomers = teams - prev_teams
        if prev_teams and newcomers:
            leavers = prev_teams - teams
            if len(teams) < LEAGUE_SIZE and prev_rows is not None:
                # Season only partly played: not every survivor has appeared
                # yet, so take the bottom of last season's table instead.
                leavers = set(_relegated(prev_rows, len(newcomers)))
            left = [ratings[t] for t in leavers if t in ratings]
            base = sum(left) / len(left) if left else BASE
            for t in leavers:
                ratings.pop(t, None)
            for t in newcomers:
                ratings[t] = base
        else:
            for t in newcomers:
                ratings[t] = BASE
        for r in rows.itertuples():
            h, a = ratings[r.home_team], ratings[r.away_team]
            pre_match.append((h, a))
            d = match_delta(h, a, r.home_goals, r.away_goals)
            ratings[r.home_team] = h + d
            ratings[r.away_team] = a - d
        prev_teams = set(ratings)
        prev_rows = rows
    return ratings, pre_match, df


def load_seed():
    with open(SEED_PATH, encoding='utf-8') as f:
        seed = json.load(f)
    ratings = {utils.normalize_team_name(t): float(v) for t, v in seed['ratings'].items()}
    return seed['as_of'], ratings


def ratings_from_results(results):
    """Seed ratings plus every result played after the seed date."""
    as_of, ratings = load_seed()
    later = [r for r in results if str(r['date'])[:10] > as_of]
    if not later:
        return ratings
    final, _, _ = replay(later, ratings=ratings)
    return final


def stored_results_since(as_of):
    """Stored results played after as_of (DB when configured, else files)."""
    from backend import database as db
    if db.DATABASE_URL:
        return db.load_results_since(as_of)
    from backend import utils_data
    rows = []
    if os.path.isdir(utils_data.RESULTS_DIR):
        for fname in sorted(os.listdir(utils_data.RESULTS_DIR)):
            date_str = fname[:-5]
            if not fname.endswith('.json') or date_str <= as_of:
                continue
            for r in utils_data.load_json(os.path.join(utils_data.RESULTS_DIR, fname)) or []:
                if 'home_team' in r:
                    rows.append({'date': date_str, **r})
    return rows


def current_ratings(results=None):
    """Current Elo per (normalized) team name.

    results: stored results to apply on top of the seed; loaded from the
    DB (or local results files) when omitted, cached for an hour.
    """
    global _cache, _cache_ts
    if results is not None:
        return ratings_from_results(results)
    now = time.time()
    if _cache is not None and now - _cache_ts < _CACHE_TTL:
        return dict(_cache)
    as_of, seed = load_seed()
    try:
        ratings = ratings_from_results(stored_results_since(as_of))
    except Exception as e:
        print(f"Elo: stored results unavailable ({e}); using seed ratings.")
        ratings = seed
    _cache, _cache_ts = ratings, now
    return dict(ratings)


def rating(team_name, ratings=None):
    """Elo for one team; unknown teams get the league average (1500)."""
    ratings = current_ratings() if ratings is None else ratings
    return float(ratings.get(utils.normalize_team_name(team_name), BASE))
