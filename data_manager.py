import pandas as pd
import soccerdata
import datetime
import utils
import logging
import concurrent.futures

# Timeout for external soccerdata network calls (seconds)
_SOCCERDATA_TIMEOUT = 45

def _run_with_timeout(func, timeout=_SOCCERDATA_TIMEOUT):
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = pool.submit(func)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        raise TimeoutError(f"Operation timed out after {timeout}s")
    finally:
        pool.shutdown(wait=False)

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
LEAGUES = "ENG-Premier League" # Can be made configurable

def fetch_training_data(years=5):
    """
    Fetches historical match data for training from Understat 
    (because it includes scores and xG reliably) and merges with ClubElo.
    
    Args:
        years (int): Number of past seasons to fetch.
        
    Returns:
        pd.DataFrame: Merged dataframe with features ready for training.
    """
    logger.info(f"Fetching {years} seasons of training data...")
    
    # 1. Determine seasons
    # soccerdata expects "2023" for 23/24, "2022" for 22/23 etc.
    current_year = datetime.datetime.now().year
    # If we are in early 2026, the current season started in 2025.
    # Logic: If month > 7, current season start year is current year. Else previous year.
    if datetime.datetime.now().month > 7:
        start_year = current_year
    else:
        start_year = current_year - 1
        
    seasons = [str(y) for y in range(start_year - years, start_year + 1)]
    logger.info(f"Seasons: {seasons}")

    # 2. Fetch Match Data (Understat)
    try:
        # We use Understat for history because it has goals/xG in the schedule view.
        # ESPN read_schedule() lacks scores.
        scraper = soccerdata.Understat(leagues=LEAGUES, seasons=seasons)
        matches = _run_with_timeout(scraper.read_schedule)
        
        # Reset index if needed (soccerdata usually returns robust indices)
        matches = matches.reset_index()
        
        # Select relevant columns
        # Standardizing names to match our existing pipeline expectations where possible
        # Understat cols: ['date', 'home_team', 'away_team', 'home_goals', 'away_goals', 'home_xg', 'away_xg']
        cols_map = {
            'date': 'date',
            'home_team': 'home_team',
            'away_team': 'away_team',
            'home_goals': 'home_goals',
            'away_goals': 'away_goals',
            'home_xg': 'home_xg',
            'away_xg': 'away_xg'
        }
        
        # Filter for completed matches (have goals)
        mask_complete = matches['home_goals'].notna() & matches['away_goals'].notna()
        completed_matches = matches.loc[mask_complete, list(cols_map.keys())].copy()
        
        # Clean data
        completed_matches['date'] = pd.to_datetime(completed_matches['date'])
        
        logger.info(f"Fetched {len(completed_matches)} completed matches from Understat.")
        
    except Exception as e:
        logger.error(f"Error fetching Understat data: {e}")
        return pd.DataFrame()

    # 3. Fetch ELO Data (ClubElo)
    return merge_data_with_elo(completed_matches)

def merge_data_with_elo(matches_df):
    """
    Augments the matches dataframe with 'home_elo' and 'away_elo' from ClubElo.
    """
    if matches_df.empty:
        return matches_df
        
    logger.info("Merging ELO ratings...")
    
    # Pre-fetch or on-demand? 
    # Let's use on-demand with caching to minimize unique date requests.
    elo_scraper = soccerdata.ClubElo()
    
    # We need to map team names from Understat to ClubElo.
    # Utils.normalize might help, but let's see.
    
    unique_dates = matches_df['date'].dt.date.unique()
    
    # Limit: If we have > 100 dates, maybe just fetch last year? 
    # 5 seasons = ~190 match weeks. 
    # Calling read_by_date 190 times is hefty but likely acceptable if cached.
    
    count = 0
    total = len(unique_dates)
    
    home_elos = []
    away_elos = []
    
    # Create a dictionary for fast lookup
    # key: (date, team_name) -> elo
    lookup = {}
    
    for d in unique_dates:
        try:
            # Check cache or fetch
            # soccerdata caches to disk, so repeated runs are fast.
            # Convert date object to string YYYY-MM-DD as soccerdata requires strictly datetime or string
            d_str = d.strftime('%Y-%m-%d')
            daily_ratings = _run_with_timeout(lambda: elo_scraper.read_by_date(d_str))
            if daily_ratings is None or daily_ratings.empty:
                continue
                
            # daily_ratings index is team name? Or column?
            # From analysis: index is 'Man City', 'Arsenal' etc.
            # We need to normalize names potentially.
            
            for team_idx, row in daily_ratings.iterrows():
                # team_idx is the name in ClubElo
                # We store it normalized
                norm_name = utils.normalize_team_name(str(team_idx))
                lookup[(d, norm_name)] = row['elo']
                
        except Exception as e:
            logger.warning(f"Failed to get ELO for {d}: {e}")
            
        count += 1
        if count % 20 == 0:
            logger.info(f"Processed {count}/{total} dates for ELO...")

    # Now apply to dataframe
    for idx, row in matches_df.iterrows():
        d = row['date'].date()
        h_team = utils.normalize_team_name(row['home_team'])
        a_team = utils.normalize_team_name(row['away_team'])
        
        h_elo = lookup.get((d, h_team), 1500) # Default 1500
        a_elo = lookup.get((d, a_team), 1500)
        
        home_elos.append(h_elo)
        away_elos.append(a_elo)
        
    matches_df['home_elo'] = home_elos
    matches_df['away_elo'] = away_elos
    
    return matches_df

def fetch_upcoming_matches():
    """
    Fetches the upcoming schedule for the current/next matchday using ESPN.
    Used for daily automation.
    """
    logger.info("Fetching upcoming matches from ESPN...")
    try:
        # ESPN for schedule
        current_season = str(datetime.datetime.now().year) 
        if datetime.datetime.now().month <= 6:
             current_season = str(datetime.datetime.now().year - 1)
             
        espn = soccerdata.ESPN(leagues=LEAGUES, seasons=current_season)
        schedule = _run_with_timeout(espn.read_schedule)
        
        if schedule.empty:
            return pd.DataFrame()
            
        schedule = schedule.reset_index()
        
        # Filter for future matches
        now = pd.Timestamp.now(tz='UTC')
        
        # Ensure 'date' is dt aware
        schedule['date'] = pd.to_datetime(schedule['date'])
        if schedule['date'].dt.tz is None:
             schedule['date'] = schedule['date'].dt.tz_localize('UTC')
        
        # Normalize timezone to UTC for comparison if checking 'upcoming'
        # ESPN date is usually UTC.
        
        # Filter for upcoming: Date >= Now
        upcoming = schedule[schedule['date'] >= now].copy()
        
        # Sort
        upcoming = upcoming.sort_values('date')
        
        # Add ELO (Current Ratings)
        # We use today's ratings
        today = datetime.date.today()
        today_str = today.strftime('%Y-%m-%d')
        elo_scraper = soccerdata.ClubElo()
        logger.info(f"Fetching current ELO for {today_str}...")
        todays_elo = _run_with_timeout(lambda: elo_scraper.read_by_date(today_str))
        
        # Create lookup
        elo_lookup = {}
        if not todays_elo.empty:
            for team, row in todays_elo.iterrows():
                norm = utils.normalize_team_name(str(team))
                elo_lookup[norm] = row['elo']
                
        # Apply
        h_elos = []
        a_elos = []
        
        for idx, row in upcoming.iterrows():
            h_team = utils.normalize_team_name(row['home_team'])
            a_team = utils.normalize_team_name(row['away_team'])
            
            h_elos.append(elo_lookup.get(h_team, 1500))
            a_elos.append(elo_lookup.get(a_team, 1500))
            
        upcoming['home_elo'] = h_elos
        upcoming['away_elo'] = a_elos
        
        return upcoming
        
    except Exception as e:
        logger.error(f"Error fetching upcoming matches: {e}")
        return pd.DataFrame()

def fetch_latest_results(date_str):
    """
    Fetches results for a specific date to compare predictions.
    Uses Understat as it has scores.
    """
    logger.info(f"Fetching results for {date_str}...")
    try:
        # Season logic
        y = int(date_str.split('-')[0])
        # simplified season guess
        season = str(y) if int(date_str.split('-')[1]) > 7 else str(y-1)
        
        scraper = soccerdata.Understat(leagues=LEAGUES, seasons=season)
        matches = _run_with_timeout(scraper.read_schedule)
        matches = matches.reset_index()
        
        matches['date_str'] = matches['date'].dt.strftime('%Y-%m-%d')
        
        days_matches = matches[matches['date_str'] == date_str].copy()
        
        # Return dict of results
        results = []
        for _, row in days_matches.iterrows():
            if pd.isna(row['home_goals']): continue
            
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


