import os
import sys
from datetime import datetime

import database as db
import utils_data

def migrate_teams():
    teams = utils_data.load_json("data/teams.json")
    if not teams:
        print("No teams.json found, skipping team migration")
        return
    db.save_teams(teams)
    print(f"Migrated {len(teams)} teams")

def migrate_predictions():
    pred_dir = utils_data.PREDICTIONS_DIR
    if not os.path.exists(pred_dir):
        print(f"Predictions directory not found: {pred_dir}")
        return
    count = 0
    for filename in sorted(os.listdir(pred_dir)):
        if not filename.endswith('.json'):
            continue
        filepath = os.path.join(pred_dir, filename)
        predictions = utils_data.load_json(filepath)
        if predictions:
            db.save_predictions(predictions)
            count += len(predictions)
            print(f"  Migrated {len(predictions)} predictions from {filename}")
    print(f"Total predictions migrated: {count}")

if __name__ == "__main__":
    if not db.DATABASE_URL:
        print("ERROR: POSTGRES_URL environment variable not set")
        sys.exit(1)
    db.init_db()
    print("Migrating teams...")
    migrate_teams()
    print("Migrating predictions...")
    migrate_predictions()
    print("Migration complete")
