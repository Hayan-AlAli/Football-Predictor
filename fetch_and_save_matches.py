import os
import sys
from datetime import datetime

import database as db
import data_manager
import utils_data
import utils

def fetch_and_save():
    print("Fetching upcoming matches from ESPN...")
    df = data_manager.fetch_upcoming_matches()

    if df is None or df.empty:
        print("No upcoming matches found.")
        return

    print(f"Found {len(df)} upcoming matches across multiple dates.")

    df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
    dates = sorted(df['date_str'].unique())
    print(f"Dates: {dates}")

    total = 0
    for date_str in dates:
        print(f"\nGenerating predictions for {date_str}...")
        predictions = utils_data.generate_predictions_for_date(date_str, df)
        if not predictions:
            print(f"  No predictions generated for {date_str}")
            continue

        print(f"  {len(predictions)} predictions generated")
        db.save_predictions(predictions)
        total += len(predictions)
        print(f"  Saved to database")

    print(f"\nDone. {total} total predictions saved to database.")

if __name__ == "__main__":
    if not db.DATABASE_URL:
        print("ERROR: POSTGRES_URL environment variable not set")
        sys.exit(1)
    db.init_db()
    fetch_and_save()
