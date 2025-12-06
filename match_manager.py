from datetime import datetime
import utils

def filter_by_gameweek(matches):
    """
    Filters the list of matches to include ONLY those belonging to the
    earliest upcoming Gameweek.
    """
    if not matches:
        return []
        
    s_matches = sorted(matches, key=lambda x: x['date'])
    
    # The first match determines the "Current/Next Gameweek"
    # Note: 'gameweek' might be NaN or string, need to handle carefully
    # FBRef usually gives integers or '12' strings.
    if 'gameweek' not in s_matches[0]:
        return s_matches # Cannot filter if missing
        
    current_gw = s_matches[0]['gameweek']
    
    # Filter
    # We treat it as string comparison to be safe against "12" vs 12
    filtered = [m for m in matches if str(m.get('gameweek')) == str(current_gw)]
    return filtered

def display_matches(matches):
    """Prints a numbered list of matches."""
    if not matches:
        print("No matches to display.")
        return

    # Check Gameweek for header
    gw_label = matches[0].get('gameweek', 'Unknown')
    
    print(f"\nFound {len(matches)} upcoming matches for Gameweek {gw_label}:")
    print("-" * 50)
    for i, match in enumerate(matches, 1):
        home = match['home_team']
        away = match['away_team']
        # match['date'] is likely a pandas timestamp or string
        match_time = utils.format_match_time(match['date'])
        print(f"{i}. {home} vs {away} [{match_time}]")
    print("-" * 50)

def get_match_by_index(matches, index):
    """Returns the match object at the selected index (1-based)."""
    if 1 <= index <= len(matches):
        return matches[index - 1]
    return None
