import pandas as pd
import numpy as np

class EloRater:
    def __init__(self, k_factor=30, initial_rating=1500):
        self.k_factor = k_factor
        self.ratings = {} # dict: team_name -> rating
        self.initial_rating = initial_rating

    def get_rating(self, team):
        return self.ratings.get(team, self.initial_rating)

    def expected_result(self, rating_a, rating_b):
        """Calculates expected score (probability of winning) for A vs B."""
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    def update_ratings(self, home_team, away_team, home_goals, away_goals):
        rate_h = self.get_rating(home_team)
        rate_a = self.get_rating(away_team)
        
        # Determine actual result
        if home_goals > away_goals:
            actual_h = 1.0
            actual_a = 0.0
        elif home_goals == away_goals:
            actual_h = 0.5
            actual_a = 0.5
        else:
            actual_h = 0.0
            actual_a = 1.0
            
        expected_h = self.expected_result(rate_h, rate_a)
        expected_a = self.expected_result(rate_a, rate_h)
        
        new_rate_h = rate_h + self.k_factor * (actual_h - expected_h)
        new_rate_a = rate_a + self.k_factor * (actual_a - expected_a)
        
        self.ratings[home_team] = new_rate_h
        self.ratings[away_team] = new_rate_a
        
        return rate_h, rate_a # Return PRE-MATCH ratings

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

def add_elo_ratings(df):
    """
    Adds home_elo and away_elo columns to the dataframe.
    """
    rater = EloRater()
    home_elos = []
    away_elos = []
    
    # Sort by date essential
    df = df.sort_values(by='date')
    
    for idx, row in df.iterrows():
        # Get ratings BEFORE update
        h_rating, a_rating = rater.update_ratings(
            row['home_team'], 
            row['away_team'], 
            row['home_goals'], 
            row['away_goals']
        )
        home_elos.append(h_rating)
        away_elos.append(a_rating)
        
    df['home_elo'] = home_elos
    df['away_elo'] = away_elos
    
    return df, rater
