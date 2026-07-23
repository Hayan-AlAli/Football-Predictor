from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import os
from typing import Optional

from backend.predictor import predict_match
from backend import data_manager
from backend import utils
from backend import utils_data
from backend import database as db

app = FastAPI(
    title="Football Predictor API",
    description="API for Premier League match predictions",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEAMS_DATA_PATH = os.path.join("data", "teams.json")

DB_AVAILABLE = db.DATABASE_URL is not None
PREMIER_LEAGUE_TEAMS = utils_data.load_json(TEAMS_DATA_PATH) or {}

if DB_AVAILABLE:
    db.init_db()
    db.save_teams(PREMIER_LEAGUE_TEAMS)


def get_team_info(team_name: str) -> dict:
    if team_name in PREMIER_LEAGUE_TEAMS:
        return PREMIER_LEAGUE_TEAMS[team_name]
    normalized = utils.normalize_team_name(team_name)
    for key, value in PREMIER_LEAGUE_TEAMS.items():
        if utils.normalize_team_name(key) == normalized:
            return value
    return {
        "name": team_name,
        "short_name": team_name[:3].upper(),
        "badge_url": None
    }


@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "Football Predictor API",
        "version": "1.0.0"
    }


@app.get("/api/health")
async def health():
    return {
        "status": "online",
        "message": "Football Predictor API",
        "version": "1.0.0"
    }


@app.get("/api/teams")
async def get_teams():
    return {"teams": list(PREMIER_LEAGUE_TEAMS.values())}


@app.get("/api/matches/upcoming")
async def get_upcoming_matches():
    try:
        upcoming_df = data_manager.fetch_upcoming_matches()

        if upcoming_df.empty:
            return {"matches": [], "message": "No upcoming matches found"}

        matches = []
        for _, row in upcoming_df.iterrows():
            home_team = utils.normalize_team_name(row['home_team'])
            away_team = utils.normalize_team_name(row['away_team'])

            time_str = row['date'].strftime('%H:%M') if 'date' in row else 'TBD'
            date_str = row['date'].strftime('%Y-%m-%d')

            match_data = {
                "id": utils_data.generate_match_id(row['date'], home_team, away_team),
                "date": date_str,
                "time": time_str,
                "gameweek": row.get('gameweek', None),
                "home_elo": row.get('home_elo', None),
                "away_elo": row.get('away_elo', None),
                "home_team": {
                    **get_team_info(home_team),
                    "name": home_team
                },
                "away_team": {
                    **get_team_info(away_team),
                    "name": away_team
                }
            }
            matches.append(match_data)

        return {"matches": matches}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching matches: {str(e)}")


@app.get("/api/matches/predictions")
async def get_predictions(date: Optional[str] = None):
    try:
        if date is None:
            date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        target_date = date

        if DB_AVAILABLE:
            predictions = db.load_predictions(target_date)
        else:
            predictions = _generate_predictions_for_date(target_date)

        if not predictions:
            pred_path = utils_data.get_prediction_file_path(target_date)
            if os.path.exists(pred_path):
                predictions = utils_data.load_json(pred_path) or []

        if not predictions:
            predictions = _generate_predictions_for_date(target_date)
            if not predictions:
                upcoming_df = data_manager.fetch_upcoming_matches()
                if upcoming_df is not None and not upcoming_df.empty:
                    upcoming_df['date_str'] = upcoming_df['date'].dt.strftime('%Y-%m-%d')
                    for nd in sorted(upcoming_df['date_str'].unique()):
                        predictions = utils_data.generate_predictions_for_date(nd, upcoming_df)
                        if predictions:
                            target_date = nd
                            break
            if predictions and DB_AVAILABLE:
                db.save_predictions(predictions)

        enriched = []
        for pred in predictions:
            enriched_pred = {
                **pred,
                "home_team_info": get_team_info(pred['home_team']),
                "away_team_info": get_team_info(pred['away_team'])
            }
            enriched.append(enriched_pred)

        return {"date": target_date, "predictions": enriched}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching predictions: {str(e)}")


@app.post("/api/matches/predictions/generate")
async def generate_predictions():
    try:
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        target_date = today
        predictions = _generate_predictions_for_date(target_date)

        if not predictions:
            upcoming_df = data_manager.fetch_upcoming_matches()
            if upcoming_df is not None and not upcoming_df.empty:
                upcoming_df['date_str'] = upcoming_df['date'].dt.strftime('%Y-%m-%d')
                next_dates = sorted(upcoming_df['date_str'].unique())
                for nd in next_dates:
                    predictions = utils_data.generate_predictions_for_date(nd, upcoming_df)
                    if predictions:
                        target_date = nd
                        break

        if predictions:
            utils_data.save_json(predictions, utils_data.get_prediction_file_path(target_date))
            if DB_AVAILABLE:
                db.save_predictions(predictions)

        enriched = []
        for pred in predictions:
            enriched_pred = {
                **pred,
                "home_team_info": get_team_info(pred['home_team']),
                "away_team_info": get_team_info(pred['away_team'])
            }
            enriched.append(enriched_pred)

        return {"date": target_date, "predictions": enriched, "generated": True}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating predictions: {str(e)}")


def _generate_predictions_for_date(date_str):
    try:
        upcoming_df = data_manager.fetch_upcoming_matches()
        return utils_data.generate_predictions_for_date(date_str, upcoming_df)
    except Exception:
        return []


def _season_year(d):
    return d.year if d.month >= 8 else d.year - 1


def compute_gameweeks(dates):
    if not dates:
        return {}

    parsed = {d: datetime.strptime(d, '%Y-%m-%d') for d in dates}
    seasons = {}
    for d, dt in parsed.items():
        sy = _season_year(dt)
        seasons.setdefault(sy, []).append(d)

    latest_season = max(seasons.keys())
    season_dates = sorted(seasons[latest_season])

    result = {}
    gw = 0
    prev = None
    for d in season_dates:
        dt = parsed[d]
        if prev is None or (dt - prev).days > 4:
            gw += 1
        result[d] = gw
        prev = dt
    return result


@app.get("/api/matches/all")
async def get_all_matches_with_predictions():
    try:
        matches = []
        gameweeks = set()

        if DB_AVAILABLE:
            dates = db.get_available_dates()
            gw_map = compute_gameweeks(dates)
            for date_str in dates:
                if date_str not in gw_map:
                    continue
                predictions = db.load_predictions(date_str)
                if not predictions:
                    continue
                gw = gw_map[date_str]
                gameweeks.add(gw)
                for pred in predictions:
                    matches.append({
                        **pred,
                        "gameweek": gw,
                        "home_team_info": get_team_info(pred['home_team']),
                        "away_team_info": get_team_info(pred['away_team'])
                    })

        return {"matches": matches, "gameweeks": sorted(gameweeks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/matches/results")
async def get_results(date: Optional[str] = None):
    try:
        if date is None:
            date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        result_path = utils_data.get_result_file_path(date)

        if not os.path.exists(result_path):
            return {"date": date, "results": [], "message": "No results for this date"}

        results = utils_data.load_json(result_path)
        return {"date": date, "results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching results: {str(e)}")


@app.post("/api/predict")
async def predict_single_match(home_team: str, away_team: str):
    try:
        match_data = {
            'home_team': home_team,
            'away_team': away_team
        }

        prediction = predict_match(match_data)

        return {
            "home_team": {
                **get_team_info(home_team),
                "name": home_team
            },
            "away_team": {
                **get_team_info(away_team),
                "name": away_team
            },
            "prediction": prediction
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating prediction: {str(e)}")


@app.get("/api/dates/available")
async def get_available_dates():
    try:
        if DB_AVAILABLE:
            dates = db.get_available_dates()
        else:
            pred_dir = os.path.join("data", "predictions")
            dates = []
            if os.path.exists(pred_dir):
                for filename in os.listdir(pred_dir):
                    if filename.endswith('.json'):
                        date_str = filename.replace('.json', '')
                        dates.append(date_str)

        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        if today not in dates:
            dates.append(today)

        dates.sort(reverse=True)
        return {"dates": dates}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing dates: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run("backend.server:app", host="0.0.0.0", port=port, reload=True)
