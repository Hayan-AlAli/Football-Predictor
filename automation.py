import argparse
import pandas as pd
from datetime import datetime, timezone
import sys

from fbref_scraper import scrape_data
from predictor import predict_match
import utils_data
import utils

def run_morning_job():
    print("Starting Morning Job (Prediction)...")
    utils_data.ensure_directories()
    
    # Current UTC date string for file naming
    current_date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    print(f"Target Date: {current_date_str}")

    # 1. Fetch Data
    # Scraper returns (completed, upcoming)
    _, upcoming_df = scrape_data()
    
    if upcoming_df.empty:
        print("No upcoming matches found from scraper.")
        utils_data.save_json([], utils_data.get_prediction_file_path(current_date_str))
        return

    # 2. Filter for Today
    # We need to match the date string. 
    # The dataframe 'Date' column is Timestamp.
    
    # Create a mask for today's matches
    # Use string comparison to avoid potential timezone headaches with naive timestamps
    upcoming_df['date_str'] = upcoming_df['Date'].dt.strftime('%Y-%m-%d')
    days_matches = upcoming_df[upcoming_df['date_str'] == current_date_str].copy()
    
    if days_matches.empty:
        print(f"No matches scheduled for today ({current_date_str}).")
        utils_data.save_json([], utils_data.get_prediction_file_path(current_date_str))
        return

    print(f"Found {len(days_matches)} matches for today.")
    
    # 3. Generate Predictions
    predictions = []
    
    for _, row in days_matches.iterrows():
        home_team = utils.normalize_team_name(row['Home'])
        away_team = utils.normalize_team_name(row['Away'])
        match_date = row['Date']
        
        # Prepare match dict for predictor
        match_input = {
            'home_team': home_team,
            'away_team': away_team,
            'date': match_date
        }
        
        # Predict
        # Note: We rely on the scraper's 'xg' if available, but predictor.py mainly uses history from training_df
        # The 'match_input' to predict_match just needs names mostly.
        pred_result = predict_match(match_input)
        
        # Feature: Generate ID
        match_id = utils_data.generate_match_id(match_date, home_team, away_team)
        
        # Structure the output
        match_output = {
            'id': match_id,
            'date': current_date_str,
            'time': row.get('Time', 'Unknown'),
            'home_team': home_team,
            'away_team': away_team,
            'prediction': pred_result
        }
        predictions.append(match_output)
        
    # 4. Save Predictions
    output_path = utils_data.get_prediction_file_path(current_date_str)
    utils_data.save_json(predictions, output_path)
    print("Morning job completed successfully.")

def run_evening_job():
    print("Starting Evening Job (Results)...")
    utils_data.ensure_directories()
    
    current_date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    print(f"Target Date: {current_date_str}")
    
    # 1. Load Predictions
    pred_path = utils_data.get_prediction_file_path(current_date_str)
    predictions = utils_data.load_json(pred_path)
    
    if not predictions:
        print(f"No predictions found for {current_date_str}. Nothing to compare.")
        return

    # 2. Fetch Results
    # This time we care about 'completed_df'
    completed_df, _ = scrape_data()
    
    if completed_df.empty:
        print("No completed matches found.")
        # Proceed anyway? If we have predictions but no completed matches, 
        # it means they haven't finished or scraper failed to find them.
    
    # Prepare lookup for completed matches
    # Key: ID -> Data
    # We need to reconstruct IDs for completed matches to match them with predictions
    results_map = {}
    if not completed_df.empty:
        for _, row in completed_df.iterrows():
            h_team = utils.normalize_team_name(row['Home'])
            a_team = utils.normalize_team_name(row['Away'])
            m_date = row['Date']
            m_id = utils_data.generate_match_id(m_date, h_team, a_team)
            
            results_map[m_id] = {
                'home_goals': int(row['HomeGoals']),
                'away_goals': int(row['AwayGoals']),
                'score': f"{int(row['HomeGoals'])}-{int(row['AwayGoals'])}"
            }
            
    # 3. Compare
    comparison_results = []
    
    for pred in predictions:
        m_id = pred['id']
        result_entry = {
            'match': pred,
            'actual': None,
            'status': 'PENDING' # PENDING, CORRECT, INCORRECT, POSTPONED
        }
        
        if m_id in results_map:
            actual = results_map[m_id]
            result_entry['actual'] = actual
            
            # Determine winner
            hg = actual['home_goals']
            ag = actual['away_goals']
            if hg > ag:
                actual_winner = pred['home_team'] # Using name from pred to assume consistency
            elif ag > hg:
                actual_winner = pred['away_team']
            else:
                actual_winner = "Draw"
            
            result_entry['actual']['winner'] = actual_winner
            
            # Check correctness
            predicted_winner = pred['prediction']['winner']
            if predicted_winner == actual_winner:
                result_entry['status'] = 'CORRECT'
            else:
                result_entry['status'] = 'INCORRECT'
        else:
             print(f"Result not found for {m_id}")
             # It might be in 'upcoming' if it played late or was postponed, or timezone diff
             # We just leave it as PENDING/None
             
        comparison_results.append(result_entry)
        
    # 4. Save Results
    output_path = utils_data.get_result_file_path(current_date_str)
    utils_data.save_json(comparison_results, output_path)
    print("Evening job completed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Football Predictor")
    parser.add_argument('mode', choices=['morning', 'evening'], help="Mode of operation")
    
    args = parser.parse_args()
    
    if args.mode == 'morning':
        run_morning_job()
    elif args.mode == 'evening':
        run_evening_job()
