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


def _season_of(date_str):
    year, month = int(date_str[:4]), int(date_str[5:7])
    return year if month >= 8 else year - 1


def canonical_predictions(preds):
    """One prediction per season per (home, away) pairing.

    Past rows are never pruned, so a match that was renamed ("Leeds" ->
    "Leeds United") or rescheduled leaves a stale twin behind. The real
    row is the latest-dated one: a match moved earlier leaves its stale
    twin in the future, where the morning job prunes it. On a same-day
    tie the row already using the canonical team names wins."""
    best = {}
    for p in preds:
        home = utils.normalize_team_name(p['home_team'])
        away = utils.normalize_team_name(p['away_team'])
        key = (_season_of(p['date']), home, away)
        rank = (p['date'], p['home_team'] == home and p['away_team'] == away)
        if key not in best or rank > best[key][0]:
            best[key] = (rank, p)
    kept = {id(p) for _, p in best.values()}
    return [p for p in preds if id(p) in kept]


def assign_gameweeks(preds):
    """Map prediction id -> matchweek number, built from the match dates.

    A matchweek is a run of consecutive match days; a new one starts after
    a day with no games, or on a day where a team would play a second time
    in the current one (a Tuesday round right after a Monday game). A whole
    day always lands in one matchweek. Numbering follows the fixtures as
    listed, so a feed missing a whole round shifts the numbers after it."""
    by_date = {}
    for p in preds:
        by_date.setdefault(p['date'], []).append(p)
    gws = {}
    gw, teams, prev = 0, set(), None
    for date_str in sorted(by_date):
        day = by_date[date_str]
        day_teams = {utils.normalize_team_name(t)
                     for p in day for t in (p['home_team'], p['away_team'])}
        d = datetime.strptime(date_str, '%Y-%m-%d')
        if prev is None or (d - prev).days > 1 or teams & day_teams:
            gw += 1
            teams = set()
        teams |= day_teams
        prev = d
        for p in day:
            gws[p['id']] = gw
    return gws


def get_prediction_file_path(date_str=None):
    if date_str is None:
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
    return os.path.join(PREDICTIONS_DIR, f"{date_str}.json")


def get_result_file_path(date_str=None):
    if date_str is None:
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
    return os.path.join(RESULTS_DIR, f"{date_str}.json")


FIXTURES_FILE_PATH = os.path.join(DATA_DIR, "fixtures.json")


def get_fixtures_file_path():
    return FIXTURES_FILE_PATH


def load_fixtures_file(from_date, team=None):
    rows = load_json(get_fixtures_file_path()) or []
    out = [r for r in rows if r.get('date', '') >= from_date]
    if team:
        out = [r for r in out
               if r.get('home_team') == team or r.get('away_team') == team]
    out.sort(key=lambda r: (r.get('date', ''), r.get('time') or ''))
    return out


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
            'home_elo': utils.safe_elo(row.get('home_elo', 1500)),
            'away_elo': utils.safe_elo(row.get('away_elo', 1500))
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
