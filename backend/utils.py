from datetime import datetime
from backend import config


def normalize_team_name(name):
    mapping = {
        "Manchester Utd": "Manchester United",
        "Man United": "Manchester United",
        "Man Utd": "Manchester United",
        "Man City": "Manchester City",
        "Manchester City F.C.": "Manchester City",
        "Newcastle Utd": "Newcastle",
        "Newcastle United": "Newcastle",
        "Newcastle United F.C.": "Newcastle",
        "Nott'ham Forest": "Nottingham Forest",
        "Nott'm Forest": "Nottingham Forest",
        "Nottm Forest": "Nottingham Forest",
        "Ipswich": "Ipswich Town",
        "Coventry": "Coventry City",
        "Forest": "Nottingham Forest",
        "Nottingham Forest F.C.": "Nottingham Forest",
        "Wolverhampton Wanderers": "Wolverhampton",
        "Wolverhampton": "Wolverhampton",
        "Wolves": "Wolverhampton",
        "Wolverhampton Wanderers F.C.": "Wolverhampton",
        "West Ham United": "West Ham",
        "West Ham United F.C.": "West Ham",
        "Brighton & Hove Albion": "Brighton",
        "Brighton and Hove Albion": "Brighton",
        "Brighton & Hove Albion F.C.": "Brighton",
        "Tottenham Hotspur": "Tottenham",
        "Tottenham Hotspur F.C.": "Tottenham",
        "Leicester": "Leicester City",
        "Leicester City F.C.": "Leicester City",
        "AFC Bournemouth": "Bournemouth",
        "Aston Villa F.C.": "Aston Villa",
        "Liverpool F.C.": "Liverpool",
        "Chelsea F.C.": "Chelsea",
        "Arsenal F.C.": "Arsenal",
        "Everton F.C.": "Everton",
        "Ipswich Town": "Ipswich Town",
        "Ipswich Town F.C.": "Ipswich Town",
        "Sheffield Utd": "Sheffield United",
        "Leeds": "Leeds United",
        "Norwich City": "Norwich",
        "West Brom": "West Bromwich Albion",
        "West Bromwich": "West Bromwich Albion",
        "Stoke City": "Stoke",
        "Swansea City": "Swansea",
        "Cardiff City": "Cardiff",
        "Huddersfield Town": "Huddersfield",
        "Hull City": "Hull",
        "Derby County": "Derby",
        "Blackburn Rovers": "Blackburn",
        "Bolton Wanderers": "Bolton",
        "Wigan Athletic": "Wigan",
        "Queens Park Rangers": "QPR",
        "Luton Town": "Luton",
        "Sheffield Weds": "Sheffield Wednesday",
    }
    return mapping.get(name, name)


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
