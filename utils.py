from datetime import datetime
import pytz
import config

def get_current_time():
    """Returns the current aware datetime in UTC."""
    if config.DEMO_MODE:
        # Mock date for testing with Free Tier API (which only gives 2023 season)
        return datetime(2023, 9, 1, tzinfo=pytz.utc)
    else:
        return datetime.now(pytz.utc)

def parse_iso8601(date_str):
    """Parses an ISO 8601 date string to a datetime object."""
    # API Football returns dates in ISO 8601 format, e.g., "2023-12-01T15:00:00+00:00"
    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))

def format_match_time(date_obj):
    """Formats a datetime object for display."""
    return date_obj.strftime("%Y-%m-%d %H:%M")

def is_same_day(date1, date2):
    """Checks if two datetime objects represent the same calendar day."""
    return date1.date() == date2.date()

def normalize_team_name(name):
    """
    Normalizes team names from FBRef/Scraper to match API-Football names.
    API-Football names are generally shorter / standard.
    """
    mapping = {
        "Manchester Utd": "Manchester United",
        "Newcastle Utd": "Newcastle",
        "Nott'ham Forest": "Nottingham Forest",
        "Wolverhampton Wanderers": "Wolves",
        "West Ham United": "West Ham",
        "Brighton & Hove Albion": "Brighton",
        "Tottenham Hotspur": "Tottenham",
        "Luton Town": "Luton",
        "Leeds United": "Leeds",
        "Leicester City": "Leicester",
        "Norwich City": "Norwich"
    }
    return mapping.get(name, name)
