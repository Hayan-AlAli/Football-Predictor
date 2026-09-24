import argparse
import os
from datetime import datetime, timedelta, timezone

from backend import utils_data
from backend import data_manager
from backend import insights


def _should_regenerate_forecast(has_forecast, weekday=None):
    """True on Mondays or when no forecast is stored at all.

    weekday is injectable (0=Monday) so the policy is unit-testable
    without patching datetime.
    """
    if weekday is None:
        weekday = datetime.now(timezone.utc).weekday()
    return weekday == 0 or not has_forecast


def run_morning_job(use_db=False, force_forecast=False):
    print("Starting Morning Job (Prediction)...")

    current_date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    print(f"Target Date: {current_date_str}")

    upcoming_df = data_manager.fetch_upcoming_matches()

    if upcoming_df.empty:
        print("No matches found from data manager.")
        return {"date": current_date_str, "fixtures_synced": 0,
                "dates_predicted": 0, "predictions": 0, "forecast": None}

    from backend import utils
    upcoming_df = upcoming_df.copy()
    upcoming_df['date_str'] = upcoming_df['date'].dt.strftime('%Y-%m-%d')
    upcoming_df = upcoming_df[upcoming_df['date_str'] >= current_date_str].sort_values('date')

    fixtures = []
    for _, row in upcoming_df.iterrows():
        home_team = utils.normalize_team_name(row['home_team'])
        away_team = utils.normalize_team_name(row['away_team'])
        fixtures.append({
            'id': utils_data.generate_match_id(row['date'], home_team, away_team),
            'date': row['date'].strftime('%Y-%m-%d'),
            'time': row['date'].strftime('%H:%M'),
            'home_team': home_team,
            'away_team': away_team,
            'gameweek': row.get('gameweek', None),
            'home_elo': utils.safe_elo(row.get('home_elo', 1500)),
            'away_elo': utils.safe_elo(row.get('away_elo', 1500)),
        })
    print(f"Synced {len(fixtures)} fixtures.")

    if use_db:
        from backend import database as db
        if not db.DATABASE_URL:
            raise RuntimeError("POSTGRES_URL not set")
        db.init_db()
        db.save_fixtures(fixtures)
        db.prune_fixtures([f['id'] for f in fixtures], current_date_str)
    else:
        utils_data.ensure_directories()
        utils_data.save_json(fixtures, utils_data.get_fixtures_file_path())

    dates_done = 0
    total = 0
    for date_str in sorted(upcoming_df['date_str'].unique()):
        predictions = utils_data.generate_predictions_for_date(date_str, upcoming_df)
        if not predictions:
            continue
        if use_db:
            db.save_predictions(predictions)
        else:
            utils_data.save_json(predictions, utils_data.get_prediction_file_path(date_str))
        dates_done += 1
        total += len(predictions)
    print(f"Predicted {total} matches across {dates_done} dates.")

    forecast_status = None
    try:
        if use_db:
            has_forecast = db.load_latest_forecast() is not None
        else:
            has_forecast = insights._today_forecast() is not None
        if force_forecast or _should_regenerate_forecast(has_forecast):
            if use_db:
                season = insights.season_year_of(datetime.now(timezone.utc))
                forecast = insights.generate_forecast(
                    results=db.load_results_since(f"{season}-07-01"))
            else:
                forecast = insights.generate_forecast()
            if forecast:
                if use_db:
                    db.save_forecast(current_date_str, forecast)
                else:
                    insights.write_forecast_file(forecast)
                forecast_status = "regenerated"
                print("Forecast regenerated.")
            else:
                print("Forecast unavailable.")
        else:
            forecast_status = "reused"
            print("Reusing stored forecast.")
    except Exception as e:
        print(f"Forecast step failed (predictions already saved): {e}")
    print("Morning job completed successfully.")
    return {"date": current_date_str, "fixtures_synced": len(fixtures),
            "dates_predicted": dates_done, "predictions": total,
            "forecast": forecast_status}


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
