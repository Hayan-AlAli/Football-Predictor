import pandas as pd
import requests
import time
import random
import os

# URL for Premier League Schedule and Results (2025-2026 Season - generic placeholders for now)
# Usually FBref URLs format: https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures
FBREF_URL = "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures"

def scrape_data():
    """
    Scrapes FBref for PL fixtures.
    Returns a tuple: (completed_df, upcoming_df)
    """
    print("Scraping FBref.com...")
    
    # Random sleep to be polite
    time.sleep(random.uniform(1, 3))
    
    try:
        # Fallback to system curl command to bypass potential python-requests blocking (TLS fingerprinting)
        import subprocess
        
        # We'll save to a temp file
        temp_file = "fbref_data.html"
        cmd = [
            "curl", 
            "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "-o", temp_file,
            FBREF_URL
        ]
        
        print("Running system curl...")
        subprocess.run(cmd, check=True)
        
        # Read the file
        dfs = pd.read_html(temp_file)
        
        # Clean up optional
        try:
             os.remove(temp_file)
        except:
             pass
        
        # usually the first table is the schedule
        df = dfs[0]
        
        # Clean basic columns
        # Filter rows that are actual matches (exclude headers repeated in table)
        if 'Wk' in df.columns:
            df = df[df['Wk'] != 'Wk']
            # Rename for consistency
            df = df.rename(columns={'Wk': 'gameweek'})
        
        # Convert Date
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
        # Split Score "2–1" into HomeGoals, AwayGoals
        # Score column format is usually "2–1"
        def parse_score(score_str):
            try:
                if pd.isna(score_str) or '–' not in str(score_str):
                    return None, None
                parts = str(score_str).split('–')
                return int(parts[0]), int(parts[1])
            except:
                return None, None

        if 'Score' not in df.columns:
             print("Warning: 'Score' column not found in scraped data. Structure might have changed.")
             return pd.DataFrame(), pd.DataFrame()

        df[['HomeGoals', 'AwayGoals']] = df['Score'].apply(lambda x: pd.Series(parse_score(x)))
        
        # Extract xG (Expected Goals)
        # FBRef usually has valid xG columns named 'xG' and 'xG.1' (for away)
        # We need to be careful as they might not imply Home/Away depending on table structure,
        # but in the Schedule table: Home, xG, Score, xG, Away is standard.
        # Pandas read_html likely renames the second xG to xG.1
        
        if 'xG' in df.columns:
            # Check if there is a duplicate (the away one)
            xg_cols = [c for c in df.columns if 'xG' in c]
            if len(xg_cols) >= 2:
                # Assuming standard order: Home comes first
                df = df.rename(columns={xg_cols[0]: 'home_xg', xg_cols[1]: 'away_xg'})
                
                # Convert to numeric
                df['home_xg'] = pd.to_numeric(df['home_xg'], errors='coerce')
                df['away_xg'] = pd.to_numeric(df['away_xg'], errors='coerce')
            else:
                print("Warning: Only one xG column found. Skipping xG extraction.")
                df['home_xg'] = None
                df['away_xg'] = None
        else:
            df['home_xg'] = None
            df['away_xg'] = None
        
        # Filter Completed Matches (Have Goals)
        completed_matches = df.dropna(subset=['HomeGoals', 'AwayGoals']).copy()
        
        # Filter Upcoming Matches (No Goals, Future Date)
        # We can just check if Score is NaN and Date is valid
        upcoming_fixtures = df[df['Score'].isna()].copy()
        
        # Sort upcoming by Date
        upcoming_fixtures = upcoming_fixtures.sort_values(by='Date')
        
        # Filter to only future from TODAY (optional, but good for "upcoming")
        today = pd.Timestamp.now().normalize()
        upcoming_fixtures = upcoming_fixtures[upcoming_fixtures['Date'] >= today]

        print(f"Scraped {len(completed_matches)} completed matches and {len(upcoming_fixtures)} upcoming fixtures.")
        
        return completed_matches, upcoming_fixtures

    except Exception as e:
        print(f"Error scraping FBref: {e}")
        return pd.DataFrame(), pd.DataFrame()

if __name__ == "__main__":
    # Test run
    c, u = scrape_data()
    if not c.empty:
        print("\nCompleted Sample:")
        print(c[['Date', 'Home', 'Score', 'Away']].head())
    if not u.empty:
        print("\nUpcoming Sample:")
        print(u[['Date', 'Home', 'Time', 'Away']].head())
