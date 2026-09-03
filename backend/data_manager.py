import pandas as pd
import soccerdata
import datetime
from backend import utils
import logging
import concurrent.futures
from backend import predictor
import time

_SOCCERDATA_TIMEOUT = 15

_UPCOMING_CACHE_TTL = 21600
_UPCOMING_EMPTY_CACHE_TTL = 900
_upcoming_cache = None
_upcoming_cache_ts = 0.0


def _run_with_timeout(func, timeout=_SOCCERDATA_TIMEOUT):
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = pool.submit(func)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        raise TimeoutError(f"Operation timed out after {timeout}s")
    finally:
        pool.shutdown(wait=False)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LEAGUES = "ENG-Premier League"


def fetch_training_data(years=5):
    logger.info(f"Fetching {years} seasons of training data...")

    current_year = datetime.datetime.now().year
    if datetime.datetime.now().month > 7:
        start_year = current_year
    else:
        start_year = current_year - 1

    seasons = [str(y) for y in range(start_year - years, start_year + 1)]
    logger.info(f"Seasons: {seasons}")

    try:
        scraper = soccerdata.Understat(leagues=LEAGUES, seasons=seasons)
        matches = _run_with_timeout(scraper.read_schedule)

        matches = matches.reset_index()

        cols_map = {
            'date': 'date',
            'home_team': 'home_team',
            'away_team': 'away_team',
            'home_goals': 'home_goals',
            'away_goals': 'away_goals',
            'home_xg': 'home_xg',
            'away_xg': 'away_xg'
        }

        mask_complete = matches['home_goals'].notna() & matches['away_goals'].notna()
        completed_matches = matches.loc[mask_complete, list(cols_map.keys())].copy()

        completed_matches['date'] = pd.to_datetime(completed_matches['date'])

        logger.info(f"Fetched {len(completed_matches)} completed matches from Understat.")

    except Exception as e:
        logger.error(f"Error fetching Understat data: {e}")
        return pd.DataFrame()

    return merge_data_with_elo(completed_matches)


def merge_data_with_elo(matches_df):
    if matches_df.empty:
        return matches_df

    logger.info("Merging ELO ratings...")

    elo_scraper = soccerdata.ClubElo()

    unique_dates = matches_df['date'].dt.date.unique()

    count = 0
    total = len(unique_dates)

    home_elos = []
    away_elos = []

    lookup = {}

    for d in unique_dates:
        try:
            d_str = d.strftime('%Y-%m-%d')
            daily_ratings = _run_with_timeout(lambda: elo_scraper.read_by_date(d_str))
            if daily_ratings is None or daily_ratings.empty:
                continue

            for team_idx, row in daily_ratings.iterrows():
                norm_name = utils.normalize_team_name(str(team_idx))
                lookup[(d, norm_name)] = row['elo']

        except Exception as e:
            logger.warning(f"Failed to get ELO for {d}: {e}")

        count += 1
        if count % 20 == 0:
            logger.info(f"Processed {count}/{total} dates for ELO...")

    for idx, row in matches_df.iterrows():
        d = row['date'].date()
        h_team = utils.normalize_team_name(row['home_team'])
        a_team = utils.normalize_team_name(row['away_team'])

        h_elo = lookup.get((d, h_team), 1500)
        a_elo = lookup.get((d, a_team), 1500)

        home_elos.append(h_elo)
        away_elos.append(a_elo)

    matches_df['home_elo'] = home_elos
    matches_df['away_elo'] = away_elos

    return matches_df


def fetch_upcoming_matches():
    global _upcoming_cache, _upcoming_cache_ts
    now = time.time()
    if _upcoming_cache is not None:
        ttl = _UPCOMING_EMPTY_CACHE_TTL if _upcoming_cache.empty else _UPCOMING_CACHE_TTL
        if now - _upcoming_cache_ts < ttl:
            return _upcoming_cache.copy()
    result = _scrape_upcoming_matches()
    _upcoming_cache = result
    _upcoming_cache_ts = now
    return result.copy()


def _scrape_upcoming_matches():
    logger.info("Fetching upcoming matches from ESPN...")
    try:
        current_season = str(datetime.datetime.now().year)
        if datetime.datetime.now().month <= 6:
            current_season = str(datetime.datetime.now().year - 1)

        espn = soccerdata.ESPN(leagues=LEAGUES, seasons=current_season)
        schedule = _run_with_timeout(espn.read_schedule)

        if schedule.empty:
            return pd.DataFrame()

        schedule = schedule.reset_index()

        now = pd.Timestamp.now(tz='UTC')

        schedule['date'] = pd.to_datetime(schedule['date'])
        if schedule['date'].dt.tz is None:
            schedule['date'] = schedule['date'].dt.tz_localize('UTC')

        upcoming = schedule[schedule['date'] >= now].copy()

        upcoming = upcoming.sort_values('date')

        today = datetime.date.today()
        today_str = today.strftime('%Y-%m-%d')
        elo_lookup = {}
        try:
            elo_scraper = soccerdata.ClubElo()
            logger.info(f"Fetching current ELO for {today_str}...")
            todays_elo = _run_with_timeout(lambda: elo_scraper.read_by_date(today_str))
            if todays_elo is not None and not todays_elo.empty:
                for team, row in todays_elo.iterrows():
                    norm = utils.normalize_team_name(str(team))
                    elo_lookup[norm] = row['elo']
        except Exception as e:
            logger.warning(f"Live ELO unavailable ({e}); using training-data ELO.")
        if not elo_lookup:
            elo_lookup = predictor.training_elo_lookup()

        h_elos = []
        a_elos = []

        for idx, row in upcoming.iterrows():
            h_team = utils.normalize_team_name(row['home_team'])
            a_team = utils.normalize_team_name(row['away_team'])

            h_elos.append(predictor._resolve_elo(elo_lookup, h_team))
            a_elos.append(predictor._resolve_elo(elo_lookup, a_team))

        upcoming['home_elo'] = h_elos
        upcoming['away_elo'] = a_elos

        return upcoming

    except Exception as e:
        logger.error(f"Error fetching upcoming matches: {e}")
        return pd.DataFrame()


def fetch_latest_results(date_str):
    logger.info(f"Fetching results for {date_str}...")
    try:
        y = int(date_str.split('-')[0])
        season = str(y) if int(date_str.split('-')[1]) > 7 else str(y - 1)

        scraper = soccerdata.Understat(leagues=LEAGUES, seasons=season)
        matches = _run_with_timeout(scraper.read_schedule)
        matches = matches.reset_index()

        matches['date_str'] = matches['date'].dt.strftime('%Y-%m-%d')

        days_matches = matches[matches['date_str'] == date_str].copy()

        results = []
        for _, row in days_matches.iterrows():
            if pd.isna(row['home_goals']):
                continue

            results.append({
                'home_team': utils.normalize_team_name(row['home_team']),
                'away_team': utils.normalize_team_name(row['away_team']),
                'home_goals': int(row['home_goals']),
                'away_goals': int(row['away_goals'])
            })

        return results

    except Exception as e:
        logger.error(f"Error fetching results: {e}")
        return []
