import argparse
import os
from datetime import datetime, timedelta, timezone

from backend import utils_data
from backend import data_manager
from backend import insights


def run_morning_job(use_db=False):
    print("Starting Morning Job (Prediction)...")

    current_date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    print(f"Target Date: {current_date_str}")

    upcoming_df = data_manager.fetch_upcoming_matches()

    if upcoming_df.empty:
        print("No matches found from data manager.")
        return {"date": current_date_str, "predictions": 0, "forecast": None}

    predictions = utils_data.generate_predictions_for_date(current_date_str, upcoming_df)

    if not predictions:
        print(f"No matches scheduled for today ({current_date_str}).")
        return {"date": current_date_str, "predictions": 0, "forecast": None}

    print(f"Found {len(predictions)} matches for today.")

    if use_db:
        from backend import database as db
        if not db.DATABASE_URL:
            raise RuntimeError("POSTGRES_URL not set")
        db.init_db()
        db.save_predictions(predictions)
        forecast = insights.generate_forecast()
        if forecast:
            db.save_forecast(current_date_str, forecast)
            print(f"Forecast cached in DB for {current_date_str}")
        print("Morning job completed successfully.")
        return {"date": current_date_str, "predictions": len(predictions),
                "forecast": bool(forecast)}

    utils_data.ensure_directories()
    output_path = utils_data.get_prediction_file_path(current_date_str)
    utils_data.save_json(predictions, output_path)

    forecast_path = insights.write_forecast_file()
    if forecast_path:
        print(f"Forecast cache written to {forecast_path}")
    print("Morning job completed successfully.")
    return {"date": current_date_str, "predictions": len(predictions),
            "forecast": bool(forecast_path)}


def run_evening_job(use_db=False, lookback_days=3):
    """Fetch completed matches and store them as raw results.

    Writes the raw schema the API reads
    ([{home_team, away_team, home_goals, away_goals}]) — verdict
    computation (CORRECT/INCORRECT) happens live in the API, so it is
    not duplicated here. Re-runs fetch recent dates missing a result
    file, so one late data source doesn't leave a permanent gap.
    """
    if use_db:
        from backend import database as db
        if not db.DATABASE_URL:
            raise RuntimeError("POSTGRES_URL not set")
        db.init_db()
        print("Starting Evening Job (Results)...")
        today = datetime.now(timezone.utc).date()
        saved = []
        for offset in range(max(1, lookback_days)):
            date_str = (today - timedelta(days=offset)).strftime('%Y-%m-%d')
            if db.load_results(date_str):
                print(f"Results already recorded for {date_str}, skipping.")
                continue
            completed_matches = data_manager.fetch_latest_results(date_str)
            if not completed_matches:
                print(f"No completed matches found for {date_str}.")
                continue
            db.save_results([{"date": date_str, **r} for r in completed_matches])
            saved.append((date_str, len(completed_matches)))
        if not saved:
            print("Evening job completed with nothing new to save.")
            return {"saved": []}
        total = sum(n for _, n in saved)
        print(f"Evening job completed successfully. Saved {total} results: " +
              ", ".join(f"{d} ({n})" for d, n in saved))
        return {"saved": saved}

    print("Starting Evening Job (Results)...")
    utils_data.ensure_directories()

    today = datetime.now(timezone.utc).date()
    saved = []
    for offset in range(max(1, lookback_days)):
        date_str = (today - timedelta(days=offset)).strftime('%Y-%m-%d')
        output_path = utils_data.get_result_file_path(date_str)
        if os.path.exists(output_path):
            print(f"Results already recorded for {date_str}, skipping.")
            continue

        completed_matches = data_manager.fetch_latest_results(date_str)

        if not completed_matches:
            print(f"No completed matches found for {date_str}.")
            continue

        utils_data.save_json(completed_matches, output_path)
        saved.append((date_str, len(completed_matches)))

    if not saved:
        print("Evening job completed with nothing new to save.")
        return {"saved": []}

    total = sum(n for _, n in saved)
    print(f"Evening job completed successfully. Saved {total} results: " +
          ", ".join(f"{d} ({n})" for d, n in saved))
    return {"saved": saved}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Football Predictor")
    parser.add_argument('mode', choices=['morning', 'evening'], help="Mode of operation")

    args = parser.parse_args()

    if args.mode == 'morning':
        run_morning_job()
    elif args.mode == 'evening':
        run_evening_job()
