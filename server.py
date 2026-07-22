"""
FastAPI backend for the Football Predictor Web Application.
Exposes API endpoints for matches, predictions, and team data.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import os
from typing import Optional

from predictor import predict_match
import data_manager
import utils
import utils_data
import database as db

app = FastAPI(
    title="Football Predictor API",
    description="API for Premier League match predictions",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Premier League team data with badge URLs and full official names
TEAMS_DATA_PATH = os.path.join("data", "teams.json")

DB_AVAILABLE = db.DATABASE_URL is not None
if DB_AVAILABLE:
    db.init_db()
    PREMIER_LEAGUE_TEAMS = db.get_teams()
    if not PREMIER_LEAGUE_TEAMS:
        PREMIER_LEAGUE_TEAMS = utils_data.load_json(TEAMS_DATA_PATH) or {}
        db.save_teams(PREMIER_LEAGUE_TEAMS)
else:
    PREMIER_LEAGUE_TEAMS = utils_data.load_json(TEAMS_DATA_PATH) or {}



def get_team_info(team_name: str) -> dict:
    """Get team info with badge URL, with fallback for unknown teams."""
    # Try exact match first
    if team_name in PREMIER_LEAGUE_TEAMS:
        return PREMIER_LEAGUE_TEAMS[team_name]
    
    # Try normalized match
    normalized = utils.normalize_team_name(team_name)
    for key, value in PREMIER_LEAGUE_TEAMS.items():
        if utils.normalize_team_name(key) == normalized:
            return value
    
    # Fallback for unknown teams
    return {
        "name": team_name,
        "short_name": team_name[:3].upper(),
        "badge_url": None
    }


@app.get("/")
async def root():
    """API health check."""
    return {
        "status": "online",
        "message": "Football Predictor API",
        "version": "1.0.0"
    }


@app.get("/api/teams")
async def get_teams():
    """Get all Premier League teams with badge URLs."""
    return {
        "teams": list(PREMIER_LEAGUE_TEAMS.values())
    }


@app.get("/api/matches/upcoming")
async def get_upcoming_matches():
    """Get upcoming matches from data manager."""
    try:
        upcoming_df = data_manager.fetch_upcoming_matches()
        
        if upcoming_df.empty:
            return {"matches": [], "message": "No upcoming matches found"}
        
        matches = []
        for _, row in upcoming_df.iterrows():
            home_team = utils.normalize_team_name(row['home_team'])
            away_team = utils.normalize_team_name(row['away_team'])
            
            # Format time if present in datetime, otherwise TBD
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
    """Get predictions for a specific date. Generates live predictions when possible."""
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
    """Generate predictions for all upcoming matches and return them."""
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
    """Fetch upcoming matches for a date and run predictions. Returns list of predictions."""
    try:
        upcoming_df = data_manager.fetch_upcoming_matches()
        return utils_data.generate_predictions_for_date(date_str, upcoming_df)
    except Exception:
        return []


def compute_gameweek(date_val) -> int:
    """Compute Premier League gameweek (1-38) from a date."""
    if isinstance(date_val, str):
        date_val = datetime.strptime(date_val, '%Y-%m-%d')
    year = date_val.year
    season_start = datetime(year, 8, 1) if date_val.month >= 8 else datetime(year - 1, 8, 1)
    days = (date_val - season_start).days
    return max(1, min(38, (days // 7) + 1))


@app.get("/api/matches/all")
async def get_all_matches_with_predictions():
    """Get all upcoming matches with predictions and computed gameweeks."""
    try:
        matches = []
        gameweeks = set()

        if DB_AVAILABLE:
            dates = db.get_available_dates()
            for date_str in dates:
                predictions = db.load_predictions(date_str)
                if not predictions:
                    continue
                gw = compute_gameweek(date_str)
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
    """Get results comparison for a specific date."""
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
    """Generate prediction for a single match on-demand."""
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
    """Get list of dates that have prediction data, plus today."""
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


@app.get("/api/worldcup/predictions")
async def get_worldcup_predictions():
    """Get predictions for the World Cup 2026."""
    try:
        wc_path = os.path.join("data", "worldcup_predictions.json")
        
        # If predictions file doesn't exist, generate it
        if not os.path.exists(wc_path):
            import predict_worldcup
            predict_worldcup.generate_and_save_predictions(wc_path)
            
        data = utils_data.load_json(wc_path)
        if not data:
            raise HTTPException(status_code=404, detail="World Cup predictions could not be loaded")
            
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading World Cup predictions: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)

