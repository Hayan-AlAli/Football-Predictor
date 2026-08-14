import sys
import os

_root = os.path.join(os.path.dirname(__file__), '..', '..')
if _root not in sys.path:
    sys.path.insert(0, _root)

from backend import database as db
from backend import utils_data
from backend import predictor


def regenerate():
    if not db.DATABASE_URL:
        print("ERROR: POSTGRES_URL not set")
        return

    db.init_db()
    dates = db.get_available_dates()
    print(f"Found {len(dates)} dates with predictions")

    print("Fetching live club Elo...")
    live_elo = predictor._fetch_live_elo() or {}

    total = 0
    for date_str in dates:
        predictions = db.load_predictions(date_str)
        if not predictions:
            continue

        updated = []
        for pred in predictions:
            match_input = {
                'home_team': pred['home_team'],
                'away_team': pred['away_team'],
                'date': pred['date'],
                'home_elo': predictor._resolve_elo(live_elo, pred['home_team']),
                'away_elo': predictor._resolve_elo(live_elo, pred['away_team']),
            }
            result = predictor.predict_match(match_input)

            updated.append({
                'id': pred['id'],
                'date': pred['date'],
                'time': pred.get('time', 'TBD'),
                'home_team': pred['home_team'],
                'away_team': pred['away_team'],
                'prediction': result,
            })

        db.save_predictions(updated)
        total += len(updated)
        print(f"  {date_str}: {len(updated)} predictions updated")

    print(f"\nDone. {total} predictions regenerated.")


if __name__ == "__main__":
    regenerate()
