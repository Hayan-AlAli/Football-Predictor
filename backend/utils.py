from backend import teams


def normalize_team_name(name):
    """Canonical team name (see backend/teams.py and data/teams.json)."""
    return teams.normalize(name)


def normalize_column(series):
    """normalize_team_name over a pandas Series, one lookup per distinct name."""
    mapping = {n: teams.normalize(n) for n in series.dropna().unique()}
    return series.map(mapping)


def safe_elo(value, default=1500.0):
    """Coerce an Elo rating to a finite float, falling back to `default`.

    Guards the whole pipeline against missing/garbage ratings (None, NaN,
    pd.NA, inf, non-numeric strings, 0): previously such values slipped
    past `x is None` / `x or 1500` checks (NaN is truthy) and crashed
    `int(elo)` with ValueError, which predict_match swallowed and turned
    into a random 0.33/0.34/0.33 fallback prediction.
    """
    try:
        if value is None:
            return default
        f = float(value)
    except (TypeError, ValueError):
        return default
    try:
        if not f or f != f or f in (float("inf"), float("-inf")):
            return default
    except Exception:
        return default
    return f
