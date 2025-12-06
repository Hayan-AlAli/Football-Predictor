import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
import joblib
import config
import utils
import features
# import api_client - REMOVED
# from match_manager import filter_and_sort_matches - REMOVED

def train():
    print("Fetching training data from Scraper...")
    from fbref_scraper import scrape_data
    
    # Fetch all fixtures (scraper returns completed and upcoming)
    completed_matches, _ = scrape_data()
    
    if completed_matches.empty:
        print("No completed matches found to train on.")
        return

    print(f"Training on {len(completed_matches)} matches.")
    
    # Prepare DataFrame for training
    df = completed_matches.copy()
    
    df = df.rename(columns={
        'Home': 'home_team',
        'Away': 'away_team',
        'HomeGoals': 'home_goals',
        'AwayGoals': 'away_goals',
        'Date': 'date'
    })
    
    # Ensure goals are numeric
    df['home_goals'] = pd.to_numeric(df['home_goals'])
    df['away_goals'] = pd.to_numeric(df['away_goals'])

    # Normalize Team Names
    df['home_team'] = df['home_team'].apply(utils.normalize_team_name)
    df['away_team'] = df['away_team'].apply(utils.normalize_team_name)

    # --- Feature Engineering ---
    print("Engineering features (ELO, Form, xG)...")
    
    # 1. ELO Ratings
    df, elo_rater = features.add_elo_ratings(df)
    
    # 2. Rolling Stats
    df = features.calculate_rolling_stats(df)
    
    # Features and Targets
    # We now use ELO and Form instead of just Team Codes!
    # But we might keep Team Codes as well as categorical embedding proxy
    
    # Encode Team Names (Still useful for ID-based trends)
    le = LabelEncoder()
    all_teams = pd.concat([df['home_team'], df['away_team']]).unique()
    le.fit(all_teams)
    
    df['home_team_code'] = le.transform(df['home_team'])
    df['away_team_code'] = le.transform(df['away_team'])
    
    # Feature Columns
    feature_cols = [
        'home_team_code', 'away_team_code',
        'home_elo', 'away_elo',
        'home_rolling_goals', 'away_rolling_goals',
        'home_rolling_xg', 'away_rolling_xg'
    ]
    
    X = df[feature_cols]
    y_home = df['home_goals']
    y_away = df['away_goals']
    
    # Train Model (Random Forest)
    print("Training Random Forest with Advanced Features...")
    model_home = RandomForestRegressor(n_estimators=100, random_state=42)
    model_away = RandomForestRegressor(n_estimators=100, random_state=42)
    
    model_home.fit(X, y_home)
    model_away.fit(X, y_away)
    
    print("Model training complete.")
    
    # Save artifacts
    joblib.dump(model_home, 'model_home.pkl')
    joblib.dump(model_away, 'model_away.pkl')
    joblib.dump(le, 'team_encoder.pkl')
    
    # Save Feature Engineering State (Current ELOs, Last Match Stats)
    # We need to save the 'elo_rater' and the raw 'df' (to calculate latest rolling stats)
    joblib.dump(elo_rater, 'elo_state.pkl')
    # Save just the minimal needed for rolling stats (last 5 games per team)
    # Actually, saving the whole training DF is easiest for now to recalculate 'current' form
    joblib.dump(df, 'training_data.pkl') 
    
    print("Models and Feature States saved to disk.")

if __name__ == "__main__":
    train()
