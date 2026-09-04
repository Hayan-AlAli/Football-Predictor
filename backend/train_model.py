import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
import joblib
from backend import utils
from backend import features


def train():
    print("Fetching training data from Data Manager...")
    from backend import data_manager

    df = data_manager.fetch_training_data(years=5)

    if df.empty:
        print("No matches found to train on.")
        return

    print(f"Training on {len(df)} matches.")

    df['home_goals'] = pd.to_numeric(df['home_goals'])
    df['away_goals'] = pd.to_numeric(df['away_goals'])
    df['home_xg'] = pd.to_numeric(df['home_xg'])
    df['away_xg'] = pd.to_numeric(df['away_xg'])

    df['home_team'] = df['home_team'].apply(utils.normalize_team_name)
    df['away_team'] = df['away_team'].apply(utils.normalize_team_name)

    print("Engineering features (Rolling Stats, Encoded Teams)...")

    df = features.calculate_rolling_stats(df)

    df = features.add_elo_difference(df)

    le = LabelEncoder()
    all_teams = pd.concat([df['home_team'], df['away_team']]).unique()
    le.fit(all_teams)

    df['home_team_code'] = le.transform(df['home_team'])
    df['away_team_code'] = le.transform(df['away_team'])

    feature_cols = features.PRODUCTION_FEATURE_COLUMNS

    X = df[feature_cols]
    y_home = df['home_goals']
    y_away = df['away_goals']

    print("Training Random Forest with Advanced Features...")
    model_home = RandomForestRegressor(n_estimators=100, random_state=42)
    model_away = RandomForestRegressor(n_estimators=100, random_state=42)

    model_home.fit(X, y_home)
    model_away.fit(X, y_away)

    print("Model training complete.")

    joblib.dump(model_home, 'model_home.pkl')
    joblib.dump(model_away, 'model_away.pkl')
    joblib.dump(le, 'team_encoder.pkl')

    joblib.dump(df, 'training_data.pkl')

    print("Models and Training Data saved to disk.")


if __name__ == "__main__":
    train()
