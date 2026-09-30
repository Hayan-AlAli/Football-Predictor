import joblib
import pandas as pd
import os
import re
from backend import elo
from backend import utils
from backend import features
import math

def resolve_elo(team_name, lookup=None):
    """Current Elo for a team (see backend/elo.py); 1500 when unknown."""
    return _resolve_elo(lookup if lookup is not None else elo.current_ratings(), team_name)


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


_DATA_KEYS = ('training_df', 'ELO_RANGE')
_MODEL_KEYS = ('model_home', 'model_away', 'encoder', 'UNKNOWN_TEAM_CODE')
_data = None
_models = None


def _load_data():
    """The training frame, loaded on first use.

    Team pages and head-to-heads only need this, and it is quick to load:
    keeping it apart from the forests means they never import scikit-learn.
    """
    global _data
    if _data is not None:
        return _data
    df = None
    try:
        if os.path.exists(TRAINING_DATA_PATH):
            df = joblib.load(TRAINING_DATA_PATH)
    except Exception as e:
        print(f"Error loading {TRAINING_DATA_PATH}: {e}")
    if df is not None and not df.empty:
        # The bundled frame predates consistent normalization (it stores e.g.
        # 'Newcastle United' / 'Wolves' / 'Ipswich'). Normalize once so every
        # lookup compares like with like.
        for col in ("home_team", "away_team"):
            if col in df.columns:
                df[col] = utils.normalize_column(df[col])
    _data = {'training_df': df, 'ELO_RANGE': _elo_range(df)}
    return _data


def _load_models():
    """The forests and team encoder, loaded on first prediction.

    Unpickling them imports scikit-learn (~1s), which only prediction and
    the sync job need; read-only requests never pay for it.
    """
    global _models
    if _models is not None:
        return _models
    m = dict.fromkeys(_MODEL_KEYS)
    for key, path in (('model_home', MODEL_PATH_HOME), ('model_away', MODEL_PATH_AWAY),
                      ('encoder', ENCODER_PATH)):
        try:
            if os.path.exists(path):
                m[key] = joblib.load(path)
        except Exception as e:
            print(f"Error loading {path}: {e}")
    m['UNKNOWN_TEAM_CODE'] = _neutral_team_code(m['encoder'])
    _models = m
    return _models


def _load():
    """Everything prediction needs: training frame plus models."""
    return {**_load_data(), **_load_models()}


def __getattr__(name):
    """predictor.model_home, predictor.training_df, ... load on first access."""
    if name in _DATA_KEYS:
        return _load_data()[name]
    if name in _MODEL_KEYS:
        return _load_models()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


_FORM_CACHE_TTL = 3600
_form_cache = None
_form_cache_ts = 0.0


def form_frame():
    """Match history for form features: training data plus every stored
    result played since it was built.

    The bundled frame is frozen at train time, so on its own every team's
    "recent form" is months old and promoted sides have none at all.
    """
    global _form_cache, _form_cache_ts
    training_df = _load_data()['training_df']
    if training_df is None or training_df.empty:
        return training_df
    import time
    now = time.time()
    if _form_cache is not None and now - _form_cache_ts < _FORM_CACHE_TTL:
        return _form_cache
    frame = training_df
    try:
        since = pd.to_datetime(training_df['date']).max().strftime('%Y-%m-%d')
        stored = elo.stored_results_since(since)
        if stored:
            extra = pd.DataFrame(stored)[['date', 'home_team', 'away_team', 'home_goals', 'away_goals']]
            extra = extra.dropna(subset=['home_goals', 'away_goals'])
            extra['date'] = pd.to_datetime(extra['date'])
            for col in ('home_team', 'away_team'):
                extra[col] = utils.normalize_column(extra[col])
            extra = extra.drop_duplicates(subset=['date', 'home_team', 'away_team'], keep='last')
            frame = pd.concat([training_df, extra], ignore_index=True).sort_values('date', kind='stable')
    except Exception as e:
        print(f"form_frame: stored results unavailable ({e}); using training data only.")
    _form_cache, _form_cache_ts = frame, now
    return frame


def _elo_range(training_df):
    """Elo span the models were trained on: inputs outside it land in
    sparse forest leaves and produce wild goal estimates."""
    try:
        vals = pd.concat([training_df['home_elo'], training_df['away_elo']])
        return float(vals.min()), float(vals.max())
    except Exception:
        return None



def _neutral_team_code(encoder):
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



def _team_code(team_name):
    """Trained code for a team, robust to spelling variants.

    Tries the normalized name, then any encoder class that normalizes to
    the same value (e.g. query 'Newcastle' -> stored 'Newcastle United').
    Unseen teams get UNKNOWN_TEAM_CODE, never another club's identity.
    """
    state = _load_models()
    encoder, unknown = state['encoder'], state['UNKNOWN_TEAM_CODE']
    if encoder is None:
        return unknown
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
    return unknown


def team_has_history(team_name, df=None):
    """Whether a (possibly un-normalized) team appears anywhere in df."""
    frame = _load_data()['training_df'] if df is None else df
    if frame is None or frame.empty:
        return False
    norm = utils.normalize_team_name(team_name)
    try:
        home = utils.normalize_column(frame["home_team"]) == norm
        away = utils.normalize_column(frame["away_team"]) == norm
        return bool((home | away).any())
    except Exception:
        return False


def get_latest_stats(team_name, df, window=5, before=None):
    """Mean goals and xG over a team's last `window` matches, counting only
    matches played strictly before `before` when it is given."""
    norm = utils.normalize_team_name(team_name)
    home_matches = df[utils.normalize_column(df['home_team']) == norm]
    away_matches = df[utils.normalize_column(df['away_team']) == norm]

    all_matches = pd.concat([home_matches, away_matches]).sort_values(by='date')
    if before is not None:
        all_matches = all_matches[features._naive_utc(all_matches['date']) < features._naive_utc(before)]

    if all_matches.empty:
        return 0.0, 0.0

    recent = all_matches.tail(window)

    goals = []
    xg = []

    for _, match in recent.iterrows():
        if utils.normalize_team_name(match['home_team']) == norm:
            goals.append(match['home_goals'])
            side_xg = match.get('home_xg')
        else:
            goals.append(match['away_goals'])
            side_xg = match.get('away_xg')
        if not pd.isna(side_xg):
            xg.append(side_xg)

    avg_goals = sum(goals) / len(goals) if goals else 0.0
    # Stored live results have no xG: use goals when no recent row has it.
    avg_xg = sum(xg) / len(xg) if xg else avg_goals

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


MODEL_VERSION = "rf-multiwindow"
FALLBACK_VERSION = "elo-poisson"
LEAGUE_GOALS_PER_MATCH = 2.75


def elo_goal_expectations(home_elo, away_elo, total=LEAGUE_GOALS_PER_MATCH):
    """Poisson means whose outcome odds match the Elo expected score.

    Keeps total goals at the league average and solves (by bisection) for
    the home/away split where P(home win) + P(draw) / 2 equals Elo's
    expected home score, home advantage included.
    """
    target = elo.expected_home(home_elo, away_elo)
    lo, hi = 0.02, total - 0.02
    for _ in range(40):
        mid = (lo + hi) / 2
        ph, pd_, _pa, *_ = calculate_probabilities(mid, total - mid)
        if ph + pd_ / 2 < target:
            lo = mid
        else:
            hi = mid
    home = (lo + hi) / 2
    return home, total - home


def elo_prediction(home_team, away_team, home_elo=None, away_elo=None):
    """Model-free prediction from Elo alone.

    Used when the trained models are missing or fail, instead of the old
    random 33/34/33 guess: it is a weaker call, but a real one, and it is
    labelled with its own model_version so the record can tell them apart.
    """
    ratings = None
    if home_elo is None or away_elo is None:
        ratings = elo.current_ratings()
    home_elo = utils.safe_elo(home_elo if home_elo is not None else _resolve_elo(ratings, home_team))
    away_elo = utils.safe_elo(away_elo if away_elo is not None else _resolve_elo(ratings, away_team))
    hg, ag = elo_goal_expectations(home_elo, away_elo)
    ph, pd_, pa, bh, bd, ba, *_ = calculate_probabilities(hg, ag)
    winner, (sh, sa) = _select_winner(home_team, away_team, ph, pd_, pa, bh, bd, ba)
    return {
        'winner': winner,
        'score': f"{sh}-{sa}",
        'home_goals': hg,
        'away_goals': ag,
        'home_elo': int(home_elo),
        'away_elo': int(away_elo),
        'prob_home': ph,
        'prob_draw': pd_,
        'prob_away': pa,
        'model_version': FALLBACK_VERSION,
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
    """One prediction; see predict_matches."""
    return predict_matches([match_data])[0]


def _match_features(m, state, form_of):
    """Model input row and display extras for one fixture."""
    training_df = state['training_df']
    home_norm = utils.normalize_team_name(m['home_team'])
    away_norm = utils.normalize_team_name(m['away_team'])

    home_elo, away_elo = m.get('home_elo'), m.get('away_elo')
    if home_elo is None or away_elo is None:
        ratings = elo.current_ratings()
        if home_elo is None:
            home_elo = _resolve_elo(ratings, home_norm)
        if away_elo is None:
            away_elo = _resolve_elo(ratings, away_norm)
    # Sanitize AFTER the lookup: None/NaN/inf/garbage all become 1500.0.
    # (`x or 1500` missed NaN since NaN is truthy.)
    home_elo, away_elo = utils.safe_elo(home_elo), utils.safe_elo(away_elo)
    if state['ELO_RANGE']:
        lo, hi = state['ELO_RANGE']
        model_home_elo, model_away_elo = min(max(home_elo, lo), hi), min(max(away_elo, lo), hi)
    else:
        model_home_elo, model_away_elo = home_elo, away_elo

    h_g, h_xg = form_of('latest', home_norm, m.get('date'))
    a_g, a_xg = form_of('latest', away_norm, m.get('date'))
    if h_g == 0.0 and h_xg == 0.0:
        h_g, h_xg = training_df['home_rolling_goals'].mean(), training_df['home_rolling_xg'].mean()
    if a_g == 0.0 and a_xg == 0.0:
        a_g, a_xg = training_df['away_rolling_goals'].mean(), training_df['away_rolling_xg'].mean()

    row = {
        'home_team_code': _team_code(home_norm),
        'away_team_code': _team_code(away_norm),
        'home_elo': model_home_elo,
        'away_elo': model_away_elo,
        'home_rolling_goals': h_g,
        'away_rolling_goals': a_g,
        'home_rolling_xg': h_xg,
        'away_rolling_xg': a_xg,
    }
    # Multi-window form through the exact builder training uses, scoped to
    # matches before the fixture (never the future). Teams with no history
    # get league-average form: all-zero vectors made the forest extrapolate
    # to ~3.4 goals.
    for window in features.MULTI_WINDOWS:
        for side, team in (("home", home_norm), ("away", away_norm)):
            form = form_of(window, team, m.get('date'))
            for metric in ("scored", "conceded", "xg_for", "xg_against"):
                row[f"{side}_form_{window}_{metric}"] = form[metric]
    extras = {'home_elo': home_elo, 'away_elo': away_elo,
              'h_g': h_g, 'a_g': a_g, 'h_xg': h_xg, 'a_xg': a_xg}
    return row, extras


def predict_matches(matches):
    """Predictions for many fixtures with one model call per side.

    Form is computed once per (team, window, date) across the batch, and the
    forests score every row together: predicting a season's remaining 310
    fixtures goes from seconds to well under one. A fixture whose features
    fail (or every fixture, if the models are missing) falls back to the
    Elo-only model rather than a guess.
    """
    matches = list(matches)
    if not matches:
        return []
    state = _load()
    training_df = state['training_df']
    if not (state['model_home'] and state['model_away'] and state['encoder']
            and training_df is not None):
        return [elo_prediction(m['home_team'], m['away_team'], m.get('home_elo'), m.get('away_elo'))
                for m in matches]

    history = form_frame()
    league_avg_goals = float(training_df['home_rolling_goals'].mean())
    league_avg_xg = float(training_df['home_rolling_xg'].mean())
    neutral = {"scored": league_avg_goals, "conceded": league_avg_goals,
               "xg_for": league_avg_xg, "xg_against": league_avg_xg}
    has_history, memo = {}, {}

    def form_of(window, team, before):
        day = None if before is None else pd.Timestamp(before).strftime('%Y-%m-%d')
        key = (window, team, day)
        if key not in memo:
            if window == 'latest':
                memo[key] = get_latest_stats(team, history, before=before)
            else:
                if team not in has_history:
                    has_history[team] = team_has_history(team, history)
                memo[key] = (features.team_window_form(history, team, window, before=before)
                             if has_history[team] else neutral)
        return memo[key]

    rows, extras, failed = [], [], {}
    for i, m in enumerate(matches):
        try:
            row, extra = _match_features(m, state, form_of)
            rows.append(row)
            extras.append((i, extra))
        except Exception as e:
            print(f"predict_matches: features failed for {m.get('home_team')} vs {m.get('away_team')}: {e}")
            failed[i] = True

    out = [None] * len(matches)
    if rows:
        X = features.add_elo_difference(pd.DataFrame(rows))[features.PRODUCTION_FEATURE_COLUMNS]
        home_goals = state['model_home'].predict(X)
        away_goals = state['model_away'].predict(X)
        for (i, ex), hg, ag in zip(extras, home_goals, away_goals):
            m = matches[i]
            hg, ag = max(0.0, float(hg)), max(0.0, float(ag))
            ph, pd_, pa, bh, bd, ba, *_ = calculate_probabilities(hg, ag)
            winner, (sh, sa) = _select_winner(m['home_team'], m['away_team'], ph, pd_, pa, bh, bd, ba)
            home_elo, away_elo = ex['home_elo'], ex['away_elo']
            out[i] = {
                'model_version': MODEL_VERSION,
                'winner': winner,
                'score': f"{sh}-{sa}",
                'home_goals': hg,
                'away_goals': ag,
                'home_elo': int(home_elo),
                'away_elo': int(away_elo),
                'prob_home': ph,
                'prob_draw': pd_,
                'prob_away': pa,
                'features': {
                    'home_elo': int(home_elo),
                    'away_elo': int(away_elo),
                    'elo_gap': int(home_elo - away_elo),
                    'home_rolling_goals': round(float(ex['h_g']), 3),
                    'away_rolling_goals': round(float(ex['a_g']), 3),
                    'home_rolling_xg': round(float(ex['h_xg']), 3),
                    'away_rolling_xg': round(float(ex['a_xg']), 3),
                    'league_avg_goals': round(league_avg_goals, 3),
                    'league_avg_xg': round(league_avg_xg, 3),
                },
            }
    for i in failed:
        m = matches[i]
        out[i] = elo_prediction(m['home_team'], m['away_team'], m.get('home_elo'), m.get('away_elo'))
    return out
