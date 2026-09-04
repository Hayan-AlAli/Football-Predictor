import pandas as pd


def calculate_rolling_stats(df, window=5):
    team_stats = {}

    home_form_goals = []
    away_form_goals = []
    home_form_xg = []
    away_form_xg = []

    for idx, row in df.iterrows():
        h_team = row['home_team']
        a_team = row['away_team']

        h_stats = team_stats.get(h_team, [])
        a_stats = team_stats.get(a_team, [])

        def get_avg(stats, key):
            if not stats:
                return 0.0
            recent = stats[-window:]
            vals = [s[key] for s in recent if s[key] is not None]
            return sum(vals) / len(vals) if vals else 0.0

        home_form_goals.append(get_avg(h_stats, 'goals_scored'))
        away_form_goals.append(get_avg(a_stats, 'goals_scored'))
        home_form_xg.append(get_avg(h_stats, 'xg_for'))
        away_form_xg.append(get_avg(a_stats, 'xg_for'))

        h_xg = row['home_xg'] if not pd.isna(row.get('home_xg')) else 0.0
        a_xg = row['away_xg'] if not pd.isna(row.get('away_xg')) else 0.0

        h_rec = {'goals_scored': row['home_goals'], 'xg_for': h_xg}
        a_rec = {'goals_scored': row['away_goals'], 'xg_for': a_xg}

        team_stats.setdefault(h_team, []).append(h_rec)
        team_stats.setdefault(a_team, []).append(a_rec)

    df['home_rolling_goals'] = home_form_goals
    df['away_rolling_goals'] = away_form_goals
    df['home_rolling_xg'] = home_form_xg
    df['away_rolling_xg'] = away_form_xg

    return df


import math


def team_decayed_form(team_df, half_life_days=30.0):
    if team_df.empty:
        return 0.0, 0.0
    latest = team_df["date"].max()
    weights = []
    gs, xs = [], []
    for _, r in team_df.iterrows():
        days = max(0.0, (latest - r["date"]).total_seconds() / 86400.0)
        w = math.exp(-days / half_life_days)
        weights.append(w)
        gs.append(0.0 if pd.isna(r.get("goals_scored")) else float(r["goals_scored"]))
        xs.append(0.0 if pd.isna(r.get("xg_for")) else float(r["xg_for"]))
    tw = sum(weights)
    if tw <= 0:
        return 0.0, 0.0
    return sum(w * g for w, g in zip(weights, gs)) / tw, sum(w * x for w, x in zip(weights, xs)) / tw


def _team_matches(df, team_name):
    return df[(df["home_team"] == team_name) | (df["away_team"] == team_name)].copy()


def _team_record(row, team_name):
    if row["home_team"] == team_name:
        return {"date": row["date"], "goals_scored": row["home_goals"], "xg_for": row["home_xg"]}
    return {"date": row["date"], "goals_scored": row["away_goals"], "xg_for": row["away_xg"]}


def calculate_rolling_stats_v2(df, half_life_days=30.0):
    df = df.copy()
    df["home_goals"] = pd.to_numeric(df["home_goals"], errors="coerce").fillna(0.0)
    df["away_goals"] = pd.to_numeric(df["away_goals"], errors="coerce").fillna(0.0)
    df["home_xg"] = pd.to_numeric(df["home_xg"], errors="coerce").fillna(0.0)
    df["away_xg"] = pd.to_numeric(df["away_xg"], errors="coerce").fillna(0.0)

    hg, ag, hx, ax, hrel, arel = [], [], [], [], [], []
    for idx, row in df.iterrows():
        h_team, a_team = row["home_team"], row["away_team"]
        prior = df[df.index < idx]
        h_prior = _team_matches(prior, h_team)
        a_prior = _team_matches(prior, a_team)
        h_rec = [_team_record(r, h_team) for _, r in h_prior.iterrows()]
        a_rec = [_team_record(r, a_team) for _, r in a_prior.iterrows()]
        hg_t, hx_t = team_decayed_form(pd.DataFrame(h_rec) if h_rec else pd.DataFrame(columns=["date", "goals_scored", "xg_for"]), half_life_days)
        ag_t, ax_t = team_decayed_form(pd.DataFrame(a_rec) if a_rec else pd.DataFrame(columns=["date", "goals_scored", "xg_for"]), half_life_days)

        league_vals = []
        for t in sorted(set(df.loc[df.index < idx, "home_team"]) | set(df.loc[df.index < idx, "away_team"])):
            t_rec = [_team_record(r, t) for _, r in _team_matches(prior, t).iterrows()]
            if t_rec:
                league_vals.append(team_decayed_form(pd.DataFrame(t_rec), half_life_days)[0])
        league_avg = sum(league_vals) / len(league_vals) if league_vals else 0.0

        hg.append(hg_t); ag.append(ag_t); hx.append(hx_t); ax.append(ax_t)
        hrel.append(max(0.0, hg_t - league_avg)); arel.append(max(0.0, ag_t - league_avg))

    df["home_rolling_goals"] = hg
    df["away_rolling_goals"] = ag
    df["home_rolling_xg"] = hx
    df["away_rolling_xg"] = ax
    df["home_relative_goals"] = hrel
    df["away_relative_goals"] = arel
    return df


_FEATURE_COLUMNS_V1 = [
    "home_team_code", "away_team_code", "home_elo", "away_elo",
    "home_rolling_goals", "away_rolling_goals", "home_rolling_xg", "away_rolling_xg",
]

# Production feature set: V1 plus the Elo gap. This is the single canonical
# definition used by BOTH training (train_model.py) and inference
# (predictor.py) so the two can never drift apart.
PRODUCTION_FEATURE_COLUMNS = _FEATURE_COLUMNS_V1 + ["elo_difference"]


def add_elo_difference(df):
    """Append elo_difference = home_elo - away_elo (NaN Elo -> 1500.0).

    The one shared implementation for training and prediction.
    """
    df = df.copy()
    df["elo_difference"] = (
        pd.to_numeric(df["home_elo"], errors="coerce").fillna(1500.0)
        - pd.to_numeric(df["away_elo"], errors="coerce").fillna(1500.0)
    )
    return df
_FEATURE_COLUMNS_V2 = _FEATURE_COLUMNS_V1 + ["elo_gap", "home_relative_goals", "away_relative_goals"]


def feature_columns(spec):
    if spec == "v1":
        return list(_FEATURE_COLUMNS_V1)
    if spec == "v2":
        return list(_FEATURE_COLUMNS_V2)
    raise ValueError(f"Unknown feature spec: {spec}")


def build_feature_columns(df, spec):
    df = df.copy()
    if "home_team_code" not in df.columns or "away_team_code" not in df.columns:
        cats, _ = pd.factorize(pd.concat([df["home_team"], df["away_team"]]))
        n = len(df)
        if "home_team_code" not in df.columns:
            df["home_team_code"] = cats[:n]
        if "away_team_code" not in df.columns:
            df["away_team_code"] = cats[n:]
    if spec == "v1":
        df = calculate_rolling_stats(df)
    elif spec == "v2":
        df = calculate_rolling_stats_v2(df)
    else:
        raise ValueError(f"Unknown feature spec: {spec}")
    if "elo_gap" in feature_columns(spec):
        df["elo_gap"] = pd.to_numeric(df["home_elo"], errors="coerce").fillna(1500.0) - pd.to_numeric(df["away_elo"], errors="coerce").fillna(1500.0)
    return df
