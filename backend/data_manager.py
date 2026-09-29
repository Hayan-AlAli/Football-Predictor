"""Training data: Understat matches (for xG) with our own pre-match Elo.

Offline only - the live app reads fixtures and results from ESPN via
backend/sources/espn.py. soccerdata is imported lazily and lives in
requirements-train.txt, so the deployed API never installs it.
"""
import datetime
import logging

import pandas as pd

from backend import utils
from backend.sources import football_data

logger = logging.getLogger(__name__)

LEAGUES = "ENG-Premier League"


def fetch_training_data(years=5):
    import soccerdata

    now = datetime.datetime.now()
    start_year = now.year if now.month > 7 else now.year - 1
    seasons = [str(y) for y in range(start_year - years, start_year + 1)]
    logger.info(f"Fetching Understat seasons {seasons}...")

    try:
        matches = soccerdata.Understat(leagues=LEAGUES, seasons=seasons).read_schedule().reset_index()
    except Exception as e:
        logger.error(f"Error fetching Understat data: {e}")
        return pd.DataFrame()

    cols = ['date', 'home_team', 'away_team', 'home_goals', 'away_goals', 'home_xg', 'away_xg']
    done = matches['home_goals'].notna() & matches['away_goals'].notna()
    completed = matches.loc[done, cols].copy()
    completed['date'] = pd.to_datetime(completed['date'])
    logger.info(f"Fetched {len(completed)} completed matches from Understat.")
    return merge_data_with_elo(completed)


def fetch_historical_results(last_season_start=None):
    return football_data.historical_results(last_season_start)


def merge_data_with_elo(matches_df, history=None):
    """Attach each match's pre-match Elo (our own system, see backend/elo.py)."""
    if matches_df.empty:
        return matches_df

    from backend import elo
    logger.info("Computing Elo ratings from full results history...")
    if history is None:
        history = fetch_historical_results()
    _, pre_match, ordered = elo.replay(history)
    lookup = {
        (r.date.date(), r.home_team, r.away_team): pre
        for r, pre in zip(ordered.itertuples(), pre_match)
    }

    home_elos, away_elos, missing = [], [], 0
    for _, row in matches_df.iterrows():
        key = (pd.Timestamp(row['date']).date(),
               utils.normalize_team_name(row['home_team']),
               utils.normalize_team_name(row['away_team']))
        pre = lookup.get(key)
        if pre is None:
            missing += 1
            pre = (elo.BASE, elo.BASE)
        home_elos.append(pre[0])
        away_elos.append(pre[1])
    if missing:
        logger.warning(f"{missing} matches not found in results history; Elo set to {elo.BASE}.")

    matches_df['home_elo'] = home_elos
    matches_df['away_elo'] = away_elos
    return matches_df
