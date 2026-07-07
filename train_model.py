import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
import joblib
import utils
import features

def train():
    print("Fetching training data from Data Manager...")
    import data_manager
    
    # Fetch 5 seasons of history
    df = data_manager.fetch_training_data(years=5)
    
    if df.empty:
        print("No matches found to train on.")
        return

    print(f"Training on {len(df)} matches.")
    
    # Ensure numeric types
    df['home_goals'] = pd.to_numeric(df['home_goals'])
    df['away_goals'] = pd.to_numeric(df['away_goals'])
    df['home_xg'] = pd.to_numeric(df['home_xg'])
    df['away_xg'] = pd.to_numeric(df['away_xg'])

    # Normalize Team Names (Already done in data_manager actually? 
    # data_manager does NOT normalize team names in the dataframe, only in the ELO lookup.
    # We should normalize here just to be safe for encoding).
    df['home_team'] = df['home_team'].apply(utils.normalize_team_name)
    df['away_team'] = df['away_team'].apply(utils.normalize_team_name)

    # --- Feature Engineering ---
    print("Engineering features (Rolling Stats, Encoded Teams)...")
    
    # 1. ELO Ratings (Already in DF from data_manager)
    # We don't calculate them manually anymore! 
    # But we need to save the 'elo_state' for the predictor?
    # NO. The predictor will use ClubElo directly for "current" ratings.
    # So we DO NOT need to save 'elo_state.pkl'. We can delete it or just not save it.
    
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
    
    # Save Feature Engineering State
    # We NO LONGER save elo_state.pkl because we use ClubElo API.
    # We DO save training_df because we need it for rolling stats (past matches).
    joblib.dump(df, 'training_data.pkl') 
    
    print("Models and Training Data saved to disk.")

if __name__ == "__main__":
    train()
