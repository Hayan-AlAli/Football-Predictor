import joblib
import pandas as pd
import os
import random
import re
import time
from backend import utils
from backend import features
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
                elo = utils.safe_elo(row['elo'], None)
                if elo is None:
                    continue
                lookup[utils.normalize_team_name(str(team))] = elo
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
        return utils.safe_elo(lookup[exact])

    team_tokens = _tokens(exact)
    if not team_tokens:
        return 1500

    best = (0, 1500)
    for key, val in lookup.items():
        elo = utils.safe_elo(val, None)
        if elo is None:
            continue
        key_tokens = _tokens(key)
        if not key_tokens:
            continue
        if team_tokens.issuperset(key_tokens) or key_tokens.issuperset(team_tokens):
            shared = len(team_tokens & key_tokens)
            if shared > best[0]:
                best = (shared, elo)
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


if training_df is not None and not training_df.empty:
    # The bundled frame predates consistent normalization (it stores e.g.
    # 'Newcastle United' / 'Wolves' / 'Ipswich'). Normalize once so every
    # lookup below compares like with like.
    for _col in ("home_team", "away_team"):
        if _col in training_df.columns:
            training_df[_col] = training_df[_col].apply(utils.normalize_team_name)


def _neutral_team_code():
    """In-distribution fallback code for teams the encoder never saw.

    Unknown teams must NOT map to 0 (Arsenal's code): that made every
    newcomer bat like Arsenal. The median code is the least-biased single
    value in a 0..N-1 label range.
    """
    try:
        n = len(encoder.classes_)
    except Exception:
        return 0
    import statistics
    return int(statistics.median(range(n)))


UNKNOWN_TEAM_CODE = _neutral_team_code()


def _team_code(team_name):
    """Trained code for a team, robust to spelling variants.

    Tries the normalized name, then any encoder class that normalizes to
    the same value (e.g. query 'Newcastle' -> stored 'Newcastle United').
    Unseen teams get UNKNOWN_TEAM_CODE, never another club's identity.
    """
    if encoder is None:
        return UNKNOWN_TEAM_CODE
    norm = utils.normalize_team_name(team_name)
    try:
        return int(encoder.transform([norm])[0])
    except Exception:
        pass
    try:
        for cls in encoder.classes_:
            if utils.normalize_team_name(str(cls)) == norm:
                return int(encoder.transform([cls])[0])
    except Exception:
        pass
    return UNKNOWN_TEAM_CODE


def team_has_history(team_name, df=None):
    """Whether a (possibly un-normalized) team appears anywhere in df."""
    frame = training_df if df is None else df
    if frame is None or frame.empty:
        return False
    norm = utils.normalize_team_name(team_name)
    try:
        home = frame["home_team"].apply(utils.normalize_team_name) == norm
        away = frame["away_team"].apply(utils.normalize_team_name) == norm
        return bool((home | away).any())
    except Exception:
        return False


def get_latest_stats(team_name, df, window=5):
    norm = utils.normalize_team_name(team_name)
    home_matches = df[df['home_team'].apply(utils.normalize_team_name) == norm]
    away_matches = df[df['away_team'].apply(utils.normalize_team_name) == norm]

    all_matches = pd.concat([home_matches, away_matches]).sort_values(by='date')

    if all_matches.empty:
        return 0.0, 0.0

    recent = all_matches.tail(window)

    goals = []
    xg = []

    for _, match in recent.iterrows():
        if utils.normalize_team_name(match['home_team']) == norm:
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


def _select_winner(home_team, away_team, prob_home, prob_draw, prob_away,
                   best_home, best_draw, best_away):
    """Pick the outcome with the highest aggregate probability.

    The likeliest single scoreline is often a draw (e.g. 1-1) even when one
    side owns most of the probability mass — comparing peak scoreline
    densities instead of outcome totals made ~65% of calls draws.
    Ties break toward home (home advantage).
    """
    if prob_home >= prob_draw and prob_home >= prob_away:
        return home_team, best_home
    if prob_away >= prob_home and prob_away >= prob_draw:
        return away_team, best_away
    return "Draw", best_draw


def predict_match(match_data):
    home_team = match_data['home_team']
    away_team = match_data['away_team']

    if model_home and model_away and encoder and training_df is not None:
        try:
            home_team_norm = utils.normalize_team_name(home_team)
            away_team_norm = utils.normalize_team_name(away_team)

            home_code = _team_code(home_team_norm)
            away_code = _team_code(away_team_norm)

            home_elo = match_data.get('home_elo')
            away_elo = match_data.get('away_elo')
            if home_elo is None or away_elo is None:
                live_elo = _fetch_live_elo() or training_elo_lookup()
                if live_elo:
                    if home_elo is None:
                        home_elo = _resolve_elo(live_elo, home_team_norm)
                    if away_elo is None:
                        away_elo = _resolve_elo(live_elo, away_team_norm)
            # Sanitize AFTER the lookup: None/NaN/inf/garbage all become
            # 1500.0. (`x or 1500` missed NaN since NaN is truthy, and the
            # resulting int(NaN) ValueError produced random 33/33/34 odds.)
            home_elo = utils.safe_elo(home_elo)
            away_elo = utils.safe_elo(away_elo)

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

            # Multi-window form through the exact builder training uses,
            # scoped to matches before the fixture (never the future).
            # Teams with no history at all get league-average form: feeding
            # all-zero vectors made the forest extrapolate to ~3.4 goals.
            league_avg_goals = float(training_df['home_rolling_goals'].mean())
            league_avg_xg = float(training_df['home_rolling_xg'].mean())
            _neutral_form = {
                "scored": league_avg_goals, "conceded": league_avg_goals,
                "xg_for": league_avg_xg, "xg_against": league_avg_xg,
            }
            fixture_date = match_data.get('date')
            for _window in features.MULTI_WINDOWS:
                for _side, _team_norm in (("home", home_team_norm), ("away", away_team_norm)):
                    if team_has_history(_team_norm):
                        _form = features.team_window_form(training_df, _team_norm, _window, before=fixture_date)
                    else:
                        _form = _neutral_form
                    for _metric in ("scored", "conceded", "xg_for", "xg_against"):
                        features_dict[f"{_side}_form_{_window}_{_metric}"] = _form[_metric]

            X_pred = features.add_elo_difference(pd.DataFrame([features_dict]))
            X_pred = X_pred[features.PRODUCTION_FEATURE_COLUMNS]

            pred_home_goals = model_home.predict(X_pred)[0]
            pred_away_goals = model_away.predict(X_pred)[0]

            pred_home_goals = max(0.0, pred_home_goals)
            pred_away_goals = max(0.0, pred_away_goals)

            prob_home, prob_draw, prob_away, best_home, best_draw, best_away, p_best_home, p_best_draw, p_best_away = calculate_probabilities(pred_home_goals, pred_away_goals)

            winner, (score_home, score_away) = _select_winner(
                home_team, away_team, prob_home, prob_draw, prob_away,
                best_home, best_draw, best_away)

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
            import traceback as _tb
            print(f"predict_match failed for {home_team} vs {away_team}: {e}")
            _tb.print_exc()
            return random_prediction(home_team, away_team)
    else:
        return random_prediction(home_team, away_team)
