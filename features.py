import pandas as pd

def calculate_rolling_stats(df, window=5):
    """
    Calculates rolling averages for goals and xG for each team.
    df must be sorted by Date.
    """
    team_stats = {} # team -> list of matches (dicts)
    
    # Initialize output columns
    home_form_goals = []
    away_form_goals = []
    home_form_xg = []
    away_form_xg = []
    
    for idx, row in df.iterrows():
        h_team = row['home_team']
        a_team = row['away_team']
        
        # Get Stats BEFORE this match
        h_stats = team_stats.get(h_team, [])
        a_stats = team_stats.get(a_team, [])
        
        # Calculate Rolling Averages
        def get_avg(stats, key):
            if not stats: return 0.0
            recent = stats[-window:]
            vals = [s[key] for s in recent if s[key] is not None]
            return sum(vals) / len(vals) if vals else 0.0
            
        home_form_goals.append(get_avg(h_stats, 'goals_scored'))
        away_form_goals.append(get_avg(a_stats, 'goals_scored'))
        home_form_xg.append(get_avg(h_stats, 'xg_for'))
        away_form_xg.append(get_avg(a_stats, 'xg_for'))
        
        # Update Stats AFTER this match (for next iteration)
        # Note: Scraper might return None for xG if missing
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


