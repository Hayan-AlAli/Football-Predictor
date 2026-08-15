import os
from datetime import datetime, timezone

import pandas as pd

from backend import utils_data
from backend import utils

FORECAST_DIR = os.path.join(utils_data.DATA_DIR, "forecast")


def season_year_of(ts):
    return ts.year if ts.month >= 8 else ts.year - 1


def _season_col(df):
    return df["date"].dt.year - (df["date"].dt.month < 8).astype(int)


def build_standings(training_df, season_year):
    df = training_df[_season_col(training_df) == season_year]
    if df.empty:
        return []
    teams = sorted(set(df["home_team"]) | set(df["away_team"]))
    rows = []
    for t in teams:
        home = df[df["home_team"] == t]
        away = df[df["away_team"] == t]
        wins = ((home["home_goals"] > home["away_goals"]).sum()
                + (away["away_goals"] > away["home_goals"]).sum())
        draws = ((home["home_goals"] == home["away_goals"]).sum()
                 + (away["away_goals"] == away["home_goals"]).sum())
        gf = int(home["home_goals"].sum() + away["away_goals"].sum())
        ga = int(home["away_goals"].sum() + away["home_goals"].sum())
        rows.append({
            "team": t,
            "played": int(len(home) + len(away)),
            "wins": int(wins),
            "draws": int(draws),
            "losses": int(len(home) + len(away) - wins - draws),
            "gf": gf,
            "ga": ga,
            "gd": gf - ga,
            "points": int(wins * 3 + draws),
        })
    rows.sort(key=lambda r: (-r["points"], -r["gd"], r["team"]))
    return rows