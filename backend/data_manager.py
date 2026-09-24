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


# First 20-team season. Starting here reproduces sinceawin.com's ratings to
# within 0.5 points; including the 22-team 1993-95 seasons drifts ~13.
FOOTBALL_DATA_FIRST_SEASON = 1995
FOOTBALL_DATA_URL = "https://football-data.co.uk/mmz4281"


def _football_data_csv(season_code, attempts=3):
    """Raw E0.csv text for one season (e.g. '2526'), retried on timeouts."""
    import requests
    url = f"{FOOTBALL_DATA_URL}/{season_code}/E0.csv"
    for attempt in range(attempts):
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            return resp.content.decode('latin1')
        except requests.RequestException:
            if attempt == attempts - 1:
                raise
            time.sleep(2 * (attempt + 1))


def fetch_historical_results(last_season_start=None):
    """Every Premier League result since 1995/96 from football-data.co.uk.

    The Elo system (backend/elo.py) needs the full history: ratings are a
    running total, so starting later gives different numbers.
    """
    import io
    if last_season_start is None:
        now = datetime.datetime.now()
        last_season_start = now.year if now.month >= 8 else now.year - 1
    frames = []
    for y in range(FOOTBALL_DATA_FIRST_SEASON, last_season_start + 1):
        code = f"{str(y)[2:]}{str(y + 1)[2:]}"
        raw = pd.read_csv(io.StringIO(_football_data_csv(code)),
                          usecols=lambda c: c in ('Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG'),
                          on_bad_lines='skip')
        raw = raw.dropna(subset=['HomeTeam', 'FTHG', 'FTAG'])
        frames.append(pd.DataFrame({
            'date': pd.to_datetime(raw['Date'], dayfirst=True, format='mixed'),
            'home_team': raw['HomeTeam'],
            'away_team': raw['AwayTeam'],
            'home_goals': raw['FTHG'].astype(int),
            'away_goals': raw['FTAG'].astype(int),
            'season': y,
        }))
    return pd.concat(frames, ignore_index=True)


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

        from backend import elo
        elo_lookup = elo.current_ratings()

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


def _football_data_season_code(date_str):
    y = int(date_str.split('-')[0])
    m = int(date_str.split('-')[1])
    start = y if m > 7 else y - 1
    return f"{str(start)[2:]}{str(start + 1)[2:]}"


def _parse_football_data_csv(text, date_str):
    """Parse football-data.co.uk E0.csv text into raw result dicts for one date."""
    import io
    df = pd.read_csv(io.StringIO(text))
    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
    day = df[df['Date'].dt.strftime('%Y-%m-%d') == date_str]
    results = []
    for _, row in day.iterrows():
        if pd.isna(row.get('FTHG')) or pd.isna(row.get('FTAG')):
            continue
        results.append({
            'home_team': utils.normalize_team_name(str(row['HomeTeam'])),
            'away_team': utils.normalize_team_name(str(row['AwayTeam'])),
            'home_goals': int(row['FTHG']),
            'away_goals': int(row['FTAG']),
        })
    return results


def _fetch_football_data_results(date_str):
    """Results fallback for seasons Understat hasn't published yet.

    football-data.co.uk posts E0.csv within days of each matchweek; Understat
    can lag by weeks at season start (e.g. season 2026 returns ~empty).
    """
    code = _football_data_season_code(date_str)
    return _parse_football_data_csv(_football_data_csv(code), date_str)


def fetch_latest_results(date_str):
    logger.info(f"Fetching results for {date_str}...")
    results = []
    try:
        y = int(date_str.split('-')[0])
        season = str(y) if int(date_str.split('-')[1]) > 7 else str(y - 1)

        scraper = soccerdata.Understat(leagues=LEAGUES, seasons=season)
        matches = _run_with_timeout(scraper.read_schedule)
        matches = matches.reset_index()

        matches['date_str'] = matches['date'].dt.strftime('%Y-%m-%d')

        days_matches = matches[matches['date_str'] == date_str].copy()

        for _, row in days_matches.iterrows():
            if pd.isna(row['home_goals']):
                continue

            results.append({
                'home_team': utils.normalize_team_name(row['home_team']),
                'away_team': utils.normalize_team_name(row['away_team']),
                'home_goals': int(row['home_goals']),
                'away_goals': int(row['away_goals'])
            })

    except Exception as e:
        logger.error(f"Error fetching results: {e}")

    if not results:
        try:
            results = _fetch_football_data_results(date_str)
            logger.info(f"Football-data fallback returned {len(results)} matches for {date_str}.")
        except Exception as e:
            logger.error(f"Error fetching football-data results: {e}")
            results = []

    return results
