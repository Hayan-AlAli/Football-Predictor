import database as db
import utils_data
import predictor

def regenerate():
    if not db.DATABASE_URL:
        print("ERROR: POSTGRES_URL not set")
        return

    db.init_db()
    dates = db.get_available_dates()
    print(f"Found {len(dates)} dates with predictions")

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
                'home_elo': 1500,
                'away_elo': 1500,
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
