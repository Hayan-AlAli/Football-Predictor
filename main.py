import sys
from fbref_scraper import scrape_data
import utils
from match_manager import display_matches, get_match_by_index, filter_by_gameweek
from predictor import predict_match
import config

def main():
    print("Welcome to the Football Match Prediction App")
    print("Fetching upcoming fixtures from FBRef...")

    try:
        # Step 1: Fetch Data (Scraper)
        # We only need 'upcoming' for the main app flow here
        _, upcoming_df = scrape_data()
        
        if upcoming_df.empty:
            print("No upcoming matches found.")
            return

        # Step 2: Process Data
        # Convert DataFrame to list of dicts for the existing app flow
        upcoming_matches = []
        for _, row in upcoming_df.iterrows():
            upcoming_matches.append({
                'home_team': utils.normalize_team_name(row['Home']),
                'away_team': utils.normalize_team_name(row['Away']),
                'date': row['Date'], # pandas timestamp
                'time': row.get('Time', 'Unknown'),
                'gameweek': row.get('gameweek', 'Unknown')
            })
            
        # Filter to show only the immediate next Gameweek
        upcoming_matches = filter_by_gameweek(upcoming_matches)
            
        # Step 3: Display Matches
        display_matches(upcoming_matches)

        # Step 4: User Selection
        while True:
            try:
                choice = input("\nEnter match number to predict (or 'q' to quit): ")
                if choice.lower() == 'q':
                    break
                
                match_index = int(choice)
                selected_match = get_match_by_index(upcoming_matches, match_index)
                
                if selected_match:
                    # Step 5: Prediction
                    prediction = predict_match(selected_match)
                    
                    home_team = selected_match['home_team']
                    away_team = selected_match['away_team']
                    
                    prob_home = prediction.get('prob_home', 0.0) * 100
                    prob_draw = prediction.get('prob_draw', 0.0) * 100
                    prob_away = prediction.get('prob_away', 0.0) * 100
                    
                    print(f"\nPrediction for {home_team} vs {away_team}:")
                    print(f"{home_team}: {prob_home:.1f}%")
                    print(f"{away_team}: {prob_away:.1f}%")
                    print(f"Draw: {prob_draw:.1f}%")
                    print(f"Expected score: {prediction['score']}")
                else:
                    print("Invalid match number. Please try again.")

            except ValueError:
                print("Invalid input. Please enter a number.")
            except Exception as e:
                print(f"An error occurred: {e}")

    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    main()
