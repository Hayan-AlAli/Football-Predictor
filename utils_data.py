import os
import json
import hashlib
from datetime import datetime
import pandas as pd

DATA_DIR = "data"
PREDICTIONS_DIR = os.path.join(DATA_DIR, "predictions")
RESULTS_DIR = os.path.join(DATA_DIR, "results")

def ensure_directories():
    """Ensures data directories exist."""
    os.makedirs(PREDICTIONS_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

def generate_match_id(date, home_team, away_team):
    """Generates a deterministic ID for a match."""
    # Date should be YYYY-MM-DD string
    if isinstance(date, pd.Timestamp):
        date_str = date.strftime('%Y-%m-%d')
    else:
        date_str = str(date).split()[0]
        
    raw_id = f"{date_str}_{home_team}_{away_team}"
    # Using hash to keep it clean, or just the string. 
    # User requested reusability and minimizing duplicate calls, 
    # but meaningful IDs are better for debugging.
    # Let's stick to a clean string ID.
    clean_id = raw_id.replace(" ", "").replace("/", "").lower()
    return clean_id

def get_prediction_file_path(date_str=None):
    """Returns the path for the prediction file."""
    if date_str is None:
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
    return os.path.join(PREDICTIONS_DIR, f"{date_str}.json")

def get_result_file_path(date_str=None):
    """Returns the path for the result file."""
    if date_str is None:
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
    return os.path.join(RESULTS_DIR, f"{date_str}.json")

def save_json(data, path):
    """Saves data to a JSON file."""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"Saved data to {path}")
    except Exception as e:
        print(f"Error saving JSON to {path}: {e}")

def load_json(path):
    """Loads data from a JSON file."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON from {path}: {e}")
        return None
