import os
import json
from datetime import datetime
import pandas as pd
from backend.predictor import predict_match
from backend import utils

DATA_DIR = "data"
PREDICTIONS_DIR = os.path.join(DATA_DIR, "predictions")
RESULTS_DIR = os.path.join(DATA_DIR, "results")

try:
    os.makedirs(PREDICTIONS_DIR, exist_ok=True)
except OSError:
    DATA_DIR = "/tmp/data"
    PREDICTIONS_DIR = os.path.join(DATA_DIR, "predictions")
    RESULTS_DIR = os.path.join(DATA_DIR, "results")


def ensure_directories():
    os.makedirs(PREDICTIONS_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)


def generate_match_id(date, home_team, away_team):
    if isinstance(date, pd.Timestamp):
        date_str = date.strftime('%Y-%m-%d')
    else:
        date_str = str(date).split()[0]

    raw_id = f"{date_str}_{home_team}_{away_team}"
    clean_id = raw_id.replace(" ", "").replace("/", "").lower()
    return clean_id


def get_prediction_file_path(date_str=None):
    if date_str is None:
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
    return os.path.join(PREDICTIONS_DIR, f"{date_str}.json")


def get_result_file_path(date_str=None):
    if date_str is None:
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
    return os.path.join(RESULTS_DIR, f"{date_str}.json")


def save_json(data, path):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"Saved data to {path}")
    except Exception as e:
        print(f"Error saving JSON to {path}: {e}")


def load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON from {path}: {e}")
        return None


def generate_predictions_for_date(date_str, upcoming_df):
    if upcoming_df is None or upcoming_df.empty:
        return []

    upcoming_df = upcoming_df.copy()
    upcoming_df['date_str'] = upcoming_df['date'].dt.strftime('%Y-%m-%d')
    days_matches = upcoming_df[upcoming_df['date_str'] == date_str]

    predictions = []
    for _, row in days_matches.iterrows():
        home_team = utils.normalize_team_name(row['home_team'])
        away_team = utils.normalize_team_name(row['away_team'])
        match_input = {
            'home_team': home_team,
            'away_team': away_team,
            'date': row['date'],
            'home_elo': row.get('home_elo', 1500),
            'away_elo': row.get('away_elo', 1500)
        }
        pred_result = predict_match(match_input)
        match_id = generate_match_id(row['date'], home_team, away_team)
        match_time = row['date'].strftime('%H:%M')
        predictions.append({
            'id': match_id,
            'date': date_str,
            'time': match_time,
            'home_team': home_team,
            'away_team': away_team,
            'prediction': pred_result
        })
    return predictions
