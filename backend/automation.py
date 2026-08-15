import argparse
from datetime import datetime, timezone

from backend import utils_data
from backend import data_manager
from backend import insights


def run_morning_job():
    print("Starting Morning Job (Prediction)...")
    utils_data.ensure_directories()

    current_date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    print(f"Target Date: {current_date_str}")

    upcoming_df = data_manager.fetch_upcoming_matches()

    if upcoming_df.empty:
        print("No matches found from data manager.")
        return

    predictions = utils_data.generate_predictions_for_date(current_date_str, upcoming_df)

    if not predictions:
        print(f"No matches scheduled for today ({current_date_str}).")
        return

    print(f"Found {len(predictions)} matches for today.")

    output_path = utils_data.get_prediction_file_path(current_date_str)
    utils_data.save_json(predictions, output_path)

    forecast_path = insights.write_forecast_file()
    if forecast_path:
        print(f"Forecast cache written to {forecast_path}")
    print("Morning job completed successfully.")


def run_evening_job():
    print("Starting Evening Job (Results)...")
    utils_data.ensure_directories()

    current_date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    print(f"Target Date: {current_date_str}")

    pred_path = utils_data.get_prediction_file_path(current_date_str)
    predictions = utils_data.load_json(pred_path)

    if not predictions:
        print(f"No predictions found for {current_date_str}. Nothing to compare.")
        return

    completed_matches = data_manager.fetch_latest_results(current_date_str)

    if not completed_matches:
        print("No completed matches found.")
        return

    results_map = {}
    for res in completed_matches:
        key = (res['home_team'], res['away_team'])
        results_map[key] = {
            'home_goals': res['home_goals'],
            'away_goals': res['away_goals'],
            'score': f"{res['home_goals']}-{res['away_goals']}"
        }

    def find_result(pred_home, pred_away):
        key = (pred_home, pred_away)
        if key in results_map:
            return results_map[key]
        for (r_home, r_away), val in results_map.items():
            if (pred_home in r_home or r_home in pred_home) and (pred_away in r_away or r_away in pred_away):
                print(f"Fuzzy match: ({pred_home}, {pred_away}) -> ({r_home}, {r_away})")
                return val
        return None

    comparison_results = []

    for pred in predictions:
        result_entry = {
            'match': pred,
            'actual': None,
            'status': 'PENDING'
        }

        actual = find_result(pred['home_team'], pred['away_team'])
        if actual is not None:
            result_entry['actual'] = actual

            hg = actual['home_goals']
            ag = actual['away_goals']
            if hg > ag:
                actual_winner = pred['home_team']
            elif ag > hg:
                actual_winner = pred['away_team']
            else:
                actual_winner = "Draw"

            result_entry['actual']['winner'] = actual_winner

            predicted_winner = pred['prediction']['winner']
            if predicted_winner == actual_winner:
                result_entry['status'] = 'CORRECT'
            else:
                result_entry['status'] = 'INCORRECT'
        else:
            print(f"Result not found for {pred['home_team']} vs {pred['away_team']}")

        comparison_results.append(result_entry)

    matched_count = sum(1 for r in comparison_results if r['actual'] is not None)
    if matched_count == 0:
        print(f"No actual results matched predictions for {current_date_str}. Nothing to save.")
        return

    output_path = utils_data.get_result_file_path(current_date_str)
    utils_data.save_json(comparison_results, output_path)
    print(f"Evening job completed successfully. {matched_count}/{len(comparison_results)} predictions matched.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Football Predictor")
    parser.add_argument('mode', choices=['morning', 'evening'], help="Mode of operation")

    args = parser.parse_args()

    if args.mode == 'morning':
        run_morning_job()
    elif args.mode == 'evening':
        run_evening_job()
