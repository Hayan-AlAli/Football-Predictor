
import soccerdata
import datetime
import logging

# Configure basic logging to see soccerdata output
logging.basicConfig(level=logging.INFO)

def test_fetch():
    print("Testing soccerdata fetch...")
    
    # Logic from data_manager.py
    current_year = datetime.datetime.now().year
    if datetime.datetime.now().month > 7:
        start_year = current_year
    else:
        start_year = current_year - 1
        
    years = 1 # Try just 1 year first to be fast
    seasons = [str(y) for y in range(start_year - years, start_year + 1)]
    print(f"Seasons calculated: {seasons}")
    
    try:
        scraper = soccerdata.Understat(leagues="ENG-Premier League", seasons=seasons)
        print("Scraper initialized.")
        matches = scraper.read_schedule()
        print(f"Matches found: {len(matches)}")
        
        # Check columns
        print("Columns:", matches.columns)
        
        if 'home_goals' in matches.columns:
            print("Home Goals sample:")
            print(matches['home_goals'].head(10))
            print(f"NaN Home Goals: {matches['home_goals'].isna().sum()}")
        else:
            print("ERROR: 'home_goals' column MISSING")

        if 'away_goals' in matches.columns:
            print("Away Goals sample:")
            print(matches['away_goals'].head(10))
        else:
             print("ERROR: 'away_goals' column MISSING")

        # Simulate the filtering from data_manager.py
        if 'home_goals' in matches.columns and 'away_goals' in matches.columns:
            mask_complete = matches['home_goals'].notna() & matches['away_goals'].notna()
            completed = matches[mask_complete]
            print(f"Completed matches (not NaN goals): {len(completed)}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_fetch()
