from datetime import datetime
import config

def normalize_team_name(name):
    """
    Normalizes team names from various sources (ESPN, Understat, FBRef)
    to canonical names matching teams.json keys.
    """
    mapping = {
        # Manchester
        "Manchester Utd": "Manchester United",
        "Man United": "Manchester United",
        "Man Utd": "Manchester United",
        "Man City": "Manchester City",
        "Manchester City F.C.": "Manchester City",
        # Newcastle
        "Newcastle Utd": "Newcastle",
        "Newcastle United": "Newcastle",
        "Newcastle United F.C.": "Newcastle",
        # Nottingham Forest
        "Nott'ham Forest": "Nottingham Forest",
        "Forest": "Nottingham Forest",
        "Nottingham Forest F.C.": "Nottingham Forest",
        # Wolverhampton
        "Wolverhampton Wanderers": "Wolverhampton",
        "Wolverhampton": "Wolverhampton",
        "Wolves": "Wolverhampton",
        "Wolverhampton Wanderers F.C.": "Wolverhampton",
        # West Ham
        "West Ham United": "West Ham",
        "West Ham United F.C.": "West Ham",
        # Brighton
        "Brighton & Hove Albion": "Brighton",
        "Brighton and Hove Albion": "Brighton",
        "Brighton & Hove Albion F.C.": "Brighton",
        # Tottenham
        "Tottenham Hotspur": "Tottenham",
        "Tottenham Hotspur F.C.": "Tottenham",
        # Leicester (fixed: no circular mapping)
        "Leicester": "Leicester City",
        "Leicester City F.C.": "Leicester City",
        # Bournemouth
        "AFC Bournemouth": "Bournemouth",
        # Aston Villa
        "Aston Villa F.C.": "Aston Villa",
        # Liverpool
        "Liverpool F.C.": "Liverpool",
        # Chelsea
        "Chelsea F.C.": "Chelsea",
        # Arsenal
        "Arsenal F.C.": "Arsenal",
        # Everton
        "Everton F.C.": "Everton",
        # Other standardisations
        "Ipswich Town": "Ipswich Town",
        "Ipswich Town F.C.": "Ipswich Town",
        "Sheffield Utd": "Sheffield United",
        "Leeds United": "Leeds",
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
        "Sheffield Weds": "Sheffield Wednesday"
    }
    return mapping.get(name, name)
