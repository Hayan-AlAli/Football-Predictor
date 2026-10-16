"""Match predictions: a time-weighted Dixon-Coles model on an xG / goals blend
(backend/dixon_coles.py), fitted to the bundled history plus every stored
result. Elo-only Poisson is the fallback if the fit cannot run."""
import math
import os
import re
import time

import joblib
import numpy as np
import pandas as pd

from backend import dixon_coles, elo, utils

TRAINING_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'training_data.pkl')

MODEL_VERSION = "dixon-coles-xg"
FALLBACK_VERSION = "elo-poisson"
LEAGUE_GOALS_PER_MATCH = 2.75


def resolve_elo(team_name, lookup=None):
    """Current Elo for a team (see backend/elo.py); 1500 when unknown."""
    return _resolve_elo(lookup if lookup is not None else elo.current_ratings(), team_name)


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


_data = None


def _load_data():
    """The bundled match history (Understat, 2020-21 onwards, with xG), loaded once.

    Names are normalised on load: the frame predates the team registry and
    stores e.g. 'Newcastle United' / 'Wolves' / 'Ipswich'.
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
        for col in ("home_team", "away_team"):
            df[col] = utils.normalize_column(df[col])
    _data = {'training_df': df}
    return _data


def __getattr__(name):
    """predictor.training_df loads on first access."""
    if name == 'training_df':
        return _load_data()['training_df']
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


_HISTORY_COLS = ['date', 'home_team', 'away_team', 'home_goals', 'away_goals', 'home_xg', 'away_xg']
_FORM_CACHE_TTL = 3600
_form_cache = None
_form_cache_ts = 0.0


def form_frame():
    """Every result we know: the bundled history plus each stored result
    played since it ends (with xG once Understat has been synced).

    The model is fitted on this, and the cards' form figures come from it.
    """
    global _form_cache, _form_cache_ts
    training_df = _load_data()['training_df']
    if training_df is None or training_df.empty:
        return training_df
    now = time.time()
    if _form_cache is not None and now - _form_cache_ts < _FORM_CACHE_TTL:
        return _form_cache
    frame = training_df
    try:
        since = pd.to_datetime(training_df['date']).max().strftime('%Y-%m-%d')
        stored = elo.stored_results_since(since)
        if stored:
            extra = pd.DataFrame(stored).reindex(columns=_HISTORY_COLS)
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


def _naive_utc(value):
    """Datetime(s) as tz-naive UTC so tz-aware kickoffs and naive history compare."""
    ts = pd.to_datetime(value, utc=True)
    if isinstance(ts, pd.Series):
        return ts.dt.tz_localize(None)
    return ts.tz_localize(None)


def get_latest_stats(team_name, df, window=5, before=None):
    """Mean goals and xG over a team's last `window` matches, counting only
    matches played strictly before `before` when it is given."""
    norm = utils.normalize_team_name(team_name)
    home_matches = df[utils.normalize_column(df['home_team']) == norm]
    away_matches = df[utils.normalize_column(df['away_team']) == norm]

    all_matches = pd.concat([home_matches, away_matches]).sort_values(by='date')
    if before is not None:
        all_matches = all_matches[_naive_utc(all_matches['date']) < _naive_utc(before)]

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
    # Results synced before their xG arrived: use goals when no recent row has it.
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

    Used when the Dixon-Coles fit is unavailable or fails, instead of the old
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


# ---------------------------------------------------------------- the model

_MODEL_CACHE_TTL = 3600
_model_cache = {}   # cutoff day (or None for the latest) -> (fitted at, Model)


def model_as_of(day=None):
    """The Dixon-Coles fit on results before `day` (a date); None = all results.

    Calls for matches still to come use the latest fit (refreshed hourly and
    whenever the sync drops the caches). A call rebuilt for a match already
    played is fitted only on what was known before that match day.
    """
    key = None if day is None else pd.Timestamp(day).normalize()
    hit = _model_cache.get(key)
    if hit and (key is not None or time.time() - hit[0] < _MODEL_CACHE_TTL):
        return hit[1]
    history = form_frame()
    if history is None or history.empty:
        raise ValueError('no match history to fit on')
    history = history.assign(date=_naive_utc(history['date']))
    as_of = key if key is not None else history['date'].max() + pd.Timedelta(days=1)
    model = dixon_coles.fit(history, as_of)
    _model_cache[key] = (time.time(), model)
    return model


def reset_caches():
    global _form_cache
    _form_cache = None
    _model_cache.clear()


def _cutoff(match_date):
    """The model a fixture is called with: matches from today on use the
    latest fit; a past match uses the fit as of its own day."""
    if match_date is None:
        return None
    day = _naive_utc(match_date).normalize()
    return day if day < pd.Timestamp.now(tz='UTC').tz_localize(None).normalize() else None


def _outcomes(grid):
    """(P home, P draw, P away) and the likeliest scoreline within each."""
    home_mask = np.tril(np.ones_like(grid, dtype=bool), -1)
    away_mask = np.triu(np.ones_like(grid, dtype=bool), 1)
    best = []
    for mask in (home_mask, np.eye(len(grid), dtype=bool), away_mask):
        masked = np.where(mask, grid, -1)
        best.append(tuple(int(v) for v in np.unravel_index(masked.argmax(), grid.shape)))
    return (float(grid[home_mask].sum()), float(np.trace(grid)), float(grid[away_mask].sum()), *best)


def _display_features(home, away, home_elo, away_elo, history, before):
    """The figures a card prints next to the call: Elo and recent form."""
    h_g, h_xg = get_latest_stats(home, history, before=before)
    a_g, a_xg = get_latest_stats(away, history, before=before)
    recent = history.tail(380)
    league_goals = float(pd.concat([recent['home_goals'], recent['away_goals']]).mean())
    xg = pd.concat([recent['home_xg'], recent['away_xg']]) if 'home_xg' in recent else pd.Series(dtype=float)
    league_xg = float(xg.mean()) if xg.notna().any() else league_goals
    return {
        'home_elo': int(home_elo),
        'away_elo': int(away_elo),
        'elo_gap': int(home_elo - away_elo),
        'home_rolling_goals': round(float(h_g), 3),
        'away_rolling_goals': round(float(a_g), 3),
        'home_rolling_xg': round(float(h_xg), 3),
        'away_rolling_xg': round(float(a_xg), 3),
        'league_avg_goals': round(league_goals, 3),
        'league_avg_xg': round(league_xg, 3),
    }


def _dixon_coles_prediction(m, ratings, history):
    home, away = m['home_team'], m['away_team']
    home_elo, away_elo = m.get('home_elo'), m.get('away_elo')
    if home_elo is None:
        home_elo = _resolve_elo(ratings(), utils.normalize_team_name(home))
    if away_elo is None:
        away_elo = _resolve_elo(ratings(), utils.normalize_team_name(away))
    home_elo, away_elo = utils.safe_elo(home_elo), utils.safe_elo(away_elo)

    model = model_as_of(_cutoff(m.get('date')))
    hg, ag = model.expected_goals(home, away)
    ph, pd_, pa, bh, bd, ba = _outcomes(model.score_matrix(hg, ag))
    winner, (sh, sa) = _select_winner(home, away, ph, pd_, pa, bh, bd, ba)
    return {
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
        'features': _display_features(home, away, home_elo, away_elo, history, m.get('date')),
    }


def predict_match(match_data):
    """One prediction; see predict_matches."""
    return predict_matches([match_data])[0]


def predict_matches(matches):
    """Predictions for fixtures: [{home_team, away_team, date?, home_elo?, away_elo?}].

    One Dixon-Coles fit serves the whole batch (one per day for past
    matches). A fixture that cannot be called that way falls back to the
    Elo-only model rather than a guess.
    """
    matches = list(matches)
    history = form_frame()
    cache = {}

    def ratings():
        if 'r' not in cache:
            cache['r'] = elo.current_ratings()
        return cache['r']

    out = []
    for m in matches:
        try:
            if history is None or history.empty:
                raise ValueError('no match history')
            out.append(_dixon_coles_prediction(m, ratings, history))
        except Exception as e:
            print(f"predict_matches: Dixon-Coles unavailable for {m.get('home_team')} vs {m.get('away_team')}: {e}")
            out.append(elo_prediction(m['home_team'], m['away_team'], m.get('home_elo'), m.get('away_elo')))
    return out
