"""
Script to predict upcoming match week(s) in the Premier League.
"""
import data_manager
from predictor import predict_match
import utils

def predict_next_matchweek(days=3):
    """Predict matches for the next N days with fixtures."""
    
    # Fetch upcoming matches
    print("Fetching upcoming matches...")
    df = data_manager.fetch_upcoming_matches()
    
    if df.empty:
        print("No upcoming matches found.")
        return
    
    # Get unique match dates
    df['date_only'] = df['date'].dt.date
    unique_dates = sorted(df['date_only'].unique())[:days]
    
    print("=" * 100)
    print("NEXT MATCHWEEK PREDICTIONS - English Premier League")
    print("=" * 100)
    
    for match_date in unique_dates:
        day_matches = df[df['date_only'] == match_date].copy()
        day_matches = day_matches.sort_values('date')
        
        print(f"\n{match_date.strftime('%A, %B %d, %Y')} ({len(day_matches)} matches)")
        print("-" * 100)
        print(f"{'Time':6} | {'Home Team':24} vs {'Away Team':24} | {'Score':5} | {'Winner':24} | Win Probabilities")
        print("-" * 100)
        
        for _, row in day_matches.iterrows():
            home = utils.normalize_team_name(row['home_team'])
            away = utils.normalize_team_name(row['away_team'])
            
            match_input = {
                'home_team': home,
                'away_team': away,
                'home_elo': row['home_elo'],
                'away_elo': row['away_elo']
            }
            
            pred = predict_match(match_input)
            
            time_str = row['date'].strftime('%H:%M')
            
            prob_str = f"H:{pred['prob_home']*100:4.0f}% D:{pred['prob_draw']*100:4.0f}% A:{pred['prob_away']*100:4.0f}%"
            
            print(f"{time_str:6} | {home:24} vs {away:24} | {pred['score']:5} | {pred['winner']:24} | {prob_str}")
    
    print("\n" + "=" * 100)
    print("ELO Ratings Legend: Higher = Better Team")
    print("Predictions use Random Forest model trained on 5 seasons of Premier League data")
    print("=" * 100)

if __name__ == "__main__":
    predict_next_matchweek(days=3)
