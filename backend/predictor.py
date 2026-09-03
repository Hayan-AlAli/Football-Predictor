import joblib
import pandas as pd
import os
import random
import re
import time
from backend import utils
import math
import concurrent.futures

_ELO_TIMEOUT = 15
_ELO_CACHE_TTL = 24 * 3600  # re-hit the live API at most once a day per process
_ELO_CACHE_PATH = os.path.join(os.path.dirname(__file__), '..', 'elo_state.pkl')

_live_elo_cache = None
_live_elo_cache_ts = 0.0
_live_elo_failed_ts = 0.0
_LIVE_ELO_RETRY_AFTER = 3600  # don't hammer a dead API: retry at most hourly


def _load_elo_disk_cache():
    try:
        if not os.path.exists(_ELO_CACHE_PATH):
            return None
        if time.time() - os.path.getmtime(_ELO_CACHE_PATH) > _ELO_CACHE_TTL:
            return None
        cached = joblib.load(_ELO_CACHE_PATH)
        if isinstance(cached, dict) and cached:
            return cached
    except Exception:
        pass
    return None


def _save_elo_disk_cache(lookup):
    try:
        joblib.dump(lookup, _ELO_CACHE_PATH)
    except Exception:
        pass


def _fetch_live_elo():
    """Live ClubElo ratings, memoized in-process and cached on disk (24h).

    Returns None when the API is unreachable so callers can fall back
    to training-data Elo instead of hammering a dead endpoint.
    """
    global _live_elo_cache, _live_elo_cache_ts, _live_elo_failed_ts
    now = time.time()
    if _live_elo_cache is not None and now - _live_elo_cache_ts < _ELO_CACHE_TTL:
        return _live_elo_cache
    if now - _live_elo_failed_ts < _LIVE_ELO_RETRY_AFTER:
        return None
    disk = _load_elo_disk_cache()
    if disk is not None:
        _live_elo_cache, _live_elo_cache_ts = disk, now
        return disk
    try:
        import soccerdata
        import datetime
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(lambda: soccerdata.ClubElo().read_by_date(datetime.date.today().strftime('%Y-%m-%d')))
        ratings = future.result(timeout=_ELO_TIMEOUT)
        pool.shutdown(wait=False)
        if ratings is not None and not ratings.empty:
            lookup = {}
            for team, row in ratings.iterrows():
                lookup[utils.normalize_team_name(str(team))] = row['elo']
            _live_elo_cache, _live_elo_cache_ts = lookup, now
            _save_elo_disk_cache(lookup)
            return lookup
    except Exception:
        pass
    _live_elo_failed_ts = time.time()
    return None


def training_elo_lookup():
    """Latest known Elo per team from the bundled training data.

    Offline fallback for when the live ClubElo API is unreachable.
    Exact-1500.0 readings are skipped: they are fallback artifacts
    written when Elo was unavailable, not genuine ratings.
    """
    if training_df is None or training_df.empty:
        return {}
    try:
        df = training_df.copy()
        df['date'] = pd.to_datetime(df['date'])
        lookup = {}
        ordered = df.sort_values('date')
        for _, row in ordered.iterrows():
            for team_col, elo_col in (('home_team', 'home_elo'), ('away_team', 'away_elo')):
                try:
                    elo = float(row[elo_col])
                except (KeyError, TypeError, ValueError):
                    continue
                if pd.isna(elo) or elo == 1500.0:
                    continue
                lookup[utils.normalize_team_name(str(row[team_col]))] = elo
        return lookup
    except Exception:
        return {}


def resolve_elo(team_name, live_lookup=None):
    """Best-effort Elo for a team: live ratings → training data → 1500."""
    if live_lookup:
        elo = _resolve_elo(live_lookup, team_name)
        if elo != 1500:
            return elo
    return _resolve_elo(training_elo_lookup(), team_name)

MODEL_PATH_HOME = os.path.join(os.path.dirname(__file__), '..', 'model_home.pkl')
MODEL_PATH_AWAY = os.path.join(os.path.dirname(__file__), '..', 'model_away.pkl')
ENCODER_PATH = os.path.join(os.path.dirname(__file__), '..', 'team_encoder.pkl')
TRAINING_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'training_data.pkl')


def _tokens(name):
    return set(re.findall(r'[a-z0-9]+', (name or '').lower()))


def _resolve_elo(lookup, team_name):
    if not lookup:
        return 1500
    exact = utils.normalize_team_name(team_name)
    if exact in lookup:
        return lookup[exact]

    team_tokens = _tokens(exact)
    if not team_tokens:
        return 1500

    best = (0, 1500)
    for key, val in lookup.items():
        key_tokens = _tokens(key)
        if not key_tokens:
            continue
        if team_tokens.issuperset(key_tokens) or key_tokens.issuperset(team_tokens):
            shared = len(team_tokens & key_tokens)
            if shared > best[0]:
                best = (shared, val)
    return best[1]


model_home = None
model_away = None
encoder = None
training_df = None

try:
    if os.path.exists(MODEL_PATH_HOME):
        model_home = joblib.load(MODEL_PATH_HOME)
    if os.path.exists(MODEL_PATH_AWAY):
        model_away = joblib.load(MODEL_PATH_AWAY)
    if os.path.exists(ENCODER_PATH):
        encoder = joblib.load(ENCODER_PATH)
    if os.path.exists(TRAINING_DATA_PATH):
        training_df = joblib.load(TRAINING_DATA_PATH)
except Exception as e:
    print(f"Error loading models: {e}")


def get_latest_stats(team_name, df, window=5):
    home_matches = df[df['home_team'] == team_name]
    away_matches = df[df['away_team'] == team_name]

    all_matches = pd.concat([home_matches, away_matches]).sort_values(by='date')

    if all_matches.empty:
        return 0.0, 0.0

    recent = all_matches.tail(window)

    goals = []
    xg = []

    for _, match in recent.iterrows():
        if match['home_team'] == team_name:
            goals.append(match['home_goals'])
            xg.append(match['home_xg'] if not pd.isna(match.get('home_xg')) else 0.0)
        else:
            goals.append(match['away_goals'])
            xg.append(match['away_xg'] if not pd.isna(match.get('away_xg')) else 0.0)

    avg_goals = sum(goals) / len(goals) if goals else 0.0
    avg_xg = sum(xg) / len(xg) if xg else 0.0

    return avg_goals, avg_xg


def poisson_probability(k, lamb):
    return (lamb ** k * math.exp(-lamb)) / math.factorial(k)


def calculate_probabilities(home_avg, away_avg, max_goals=10):
    prob_home_win = 0.0
    prob_draw = 0.0
    prob_away_win = 0.0

    best_home = (0, 0)
    best_draw = (0, 0)
    best_away = (0, 0)
    max_home = -1.0
    max_draw = -1.0
    max_away = -1.0

    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = poisson_probability(h, home_avg) * poisson_probability(a, away_avg)

            if h > a:
                prob_home_win += p
                if p > max_home:
                    max_home = p
                    best_home = (h, a)
            elif a > h:
                prob_away_win += p
                if p > max_away:
                    max_away = p
                    best_away = (h, a)
            else:
                prob_draw += p
                if p > max_draw:
                    max_draw = p
                    best_draw = (h, a)

    total_prob = prob_home_win + prob_draw + prob_away_win
    if total_prob > 0:
        prob_home_win /= total_prob
        prob_draw /= total_prob
        prob_away_win /= total_prob

    return prob_home_win, prob_draw, prob_away_win, best_home, best_draw, best_away, max_home, max_draw, max_away


def random_prediction(home_team, away_team):
    home_score = random.randint(0, 3)
    away_score = random.randint(0, 3)
    if home_score > away_score:
        winner = home_team
    elif away_score > home_score:
        winner = away_team
    else:
        winner = "Draw"

    return {
        "winner": winner,
        "score": f"{home_score}-{away_score}",
        "home_goals": home_score,
        "away_goals": away_score,
        "prob_home": 0.33,
        "prob_draw": 0.34,
        "prob_away": 0.33
    }


def predict_match(match_data):
    home_team = match_data['home_team']
    away_team = match_data['away_team']

    if model_home and model_away and encoder and training_df is not None:
        try:
            home_team_norm = utils.normalize_team_name(home_team)
            away_team_norm = utils.normalize_team_name(away_team)

            try:
                home_code = encoder.transform([home_team_norm])[0]
            except Exception:
                home_code = 0
            try:
                away_code = encoder.transform([away_team_norm])[0]
            except Exception:
                away_code = 0

            home_elo = match_data.get('home_elo')
            away_elo = match_data.get('away_elo')
            if home_elo is None or away_elo is None:
                live_elo = _fetch_live_elo() or training_elo_lookup()
                if live_elo:
                    if home_elo is None:
                        home_elo = _resolve_elo(live_elo, home_team_norm)
                    if away_elo is None:
                        away_elo = _resolve_elo(live_elo, away_team_norm)
                home_elo = home_elo or 1500
                away_elo = away_elo or 1500

            h_g, h_xg = get_latest_stats(home_team_norm, training_df)
            a_g, a_xg = get_latest_stats(away_team_norm, training_df)

            if h_g == 0.0 and h_xg == 0.0:
                h_g = training_df['home_rolling_goals'].mean()
                h_xg = training_df['home_rolling_xg'].mean()
            if a_g == 0.0 and a_xg == 0.0:
                a_g = training_df['away_rolling_goals'].mean()
                a_xg = training_df['away_rolling_xg'].mean()

            features_dict = {
                'home_team_code': home_code,
                'away_team_code': away_code,
                'home_elo': home_elo,
                'away_elo': away_elo,
                'home_rolling_goals': h_g,
                'away_rolling_goals': a_g,
                'home_rolling_xg': h_xg,
                'away_rolling_xg': a_xg
            }

            league_avg_goals = float(training_df['home_rolling_goals'].mean())
            league_avg_xg = float(training_df['home_rolling_xg'].mean())

            X_pred = pd.DataFrame([features_dict])

            pred_home_goals = model_home.predict(X_pred)[0]
            pred_away_goals = model_away.predict(X_pred)[0]

            pred_home_goals = max(0.0, pred_home_goals)
            pred_away_goals = max(0.0, pred_away_goals)

            prob_home, prob_draw, prob_away, best_home, best_draw, best_away, p_best_home, p_best_draw, p_best_away = calculate_probabilities(pred_home_goals, pred_away_goals)

            if p_best_home >= p_best_draw and p_best_home >= p_best_away:
                winner = home_team
                score_home, score_away = best_home
            elif p_best_away >= p_best_home and p_best_away >= p_best_draw:
                winner = away_team
                score_home, score_away = best_away
            else:
                winner = "Draw"
                score_home, score_away = best_draw

            return {
                'winner': winner,
                'score': f"{score_home}-{score_away}",
                'home_goals': pred_home_goals,
                'away_goals': pred_away_goals,
                'home_elo': int(home_elo),
                'away_elo': int(away_elo),
                'prob_home': prob_home,
                'prob_draw': prob_draw,
                'prob_away': prob_away,
                'features': {
                    'home_elo': int(home_elo),
                    'away_elo': int(away_elo),
                    'elo_gap': int(home_elo - away_elo),
                    'home_rolling_goals': round(h_g, 3),
                    'away_rolling_goals': round(a_g, 3),
                    'home_rolling_xg': round(h_xg, 3),
                    'away_rolling_xg': round(a_xg, 3),
                    'league_avg_goals': round(league_avg_goals, 3),
                    'league_avg_xg': round(league_avg_xg, 3),
                }
            }

        except Exception as e:
            return random_prediction(home_team, away_team)
    else:
        return random_prediction(home_team, away_team)
