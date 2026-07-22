import sys
import os
os.environ.setdefault("SOCCERDATA_DIR", "/tmp/soccerdata")

import json
from datetime import datetime, timezone
from typing import Optional

_root = os.path.join(os.path.dirname(__file__), '..')
if _root not in sys.path:
    sys.path.insert(0, _root)

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import database as db

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

DB_AVAILABLE = db.DATABASE_URL is not None
if DB_AVAILABLE:
    db.init_db()

_team_list = [
    "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton",
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Ipswich",
    "Leicester", "Liverpool", "Man City", "Man United", "Newcastle",
    "Nott'm Forest", "Southampton", "Spurs", "West Ham", "Wolves"
]
_team_info = lambda n: {"id": n, "name": n, "short_name": n[:3].upper(), "badge_url": ""}

@app.get("/api/health")
async def health():
    return {"status": "online", "message": "Football Predictor API", "version": "1.0.0"}

@app.get("/api/teams")
async def teams():
    return {"teams": [_team_info(n) for n in _team_list]}

@app.get("/api/matches/upcoming")
async def upcoming_matches():
    try:
        import data_manager
        import utils as ut
        import utils_data
        df = data_manager.fetch_upcoming_matches()
        if df is None or df.empty:
            return {"matches": []}
        matches = []
        for _, r in df.iterrows():
            ht = ut.normalize_team_name(r['home_team'])
            at = ut.normalize_team_name(r['away_team'])
            mid = utils_data.generate_match_id(r['date'], ht, at)
            matches.append({
                'id': mid, 'date': r['date'].strftime('%Y-%m-%d'), 'time': r['date'].strftime('%H:%M'),
                'gameweek': r.get('gameweek', ''), 'home_elo': r.get('home_elo', 1500), 'away_elo': r.get('away_elo', 1500),
                'home_team': _team_info(ht), 'away_team': _team_info(at)
            })
        return {"matches": matches}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/matches/predictions")
async def get_predictions(date: Optional[str] = None):
    try:
        if date is None:
            date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        target_date = date
        if DB_AVAILABLE:
            predictions = db.load_predictions(target_date)
        else:
            import data_manager
            from utils_data import generate_predictions_for_date
            df = data_manager.fetch_upcoming_matches()
            predictions = generate_predictions_for_date(target_date, df)
        if not predictions:
            import os as _os
            import utils_data
            p = utils_data.get_prediction_file_path(target_date)
            if _os.path.exists(p):
                predictions = utils_data.load_json(p) or []
        if not predictions:
            import data_manager
            from utils_data import generate_predictions_for_date
            df = data_manager.fetch_upcoming_matches()
            predictions = generate_predictions_for_date(target_date, df)
            if not predictions and df is not None and not df.empty:
                df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
                for nd in sorted(df['date_str'].unique()):
                    predictions = generate_predictions_for_date(nd, df)
                    if predictions:
                        target_date = nd
                        break
            if predictions and DB_AVAILABLE:
                db.save_predictions(predictions)
        enriched = [{**pred, "home_team_info": _team_info(pred['home_team']), "away_team_info": _team_info(pred['away_team'])} for pred in predictions]
        return {"date": target_date, "predictions": enriched}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

def _generate_predictions_for_date_api(date_str):
    try:
        import data_manager
        from utils_data import generate_predictions_for_date
        df = data_manager.fetch_upcoming_matches()
        return generate_predictions_for_date(date_str, df)
    except Exception:
        return []

def compute_gameweek(date_val) -> int:
    if isinstance(date_val, str):
        date_val = datetime.strptime(date_val, '%Y-%m-%d')
    year = date_val.year
    season_start = datetime(year, 8, 1) if date_val.month >= 8 else datetime(year - 1, 8, 1)
    days = (date_val - season_start).days
    return max(1, min(38, (days // 7) + 1))

@app.get("/api/matches/all")
async def get_all_matches_with_predictions():
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
                        "home_team_info": _team_info(pred['home_team']),
                        "away_team_info": _team_info(pred['away_team'])
                    })
        return {"matches": matches, "gameweeks": sorted(gameweeks)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/matches/predictions/generate")
async def generate_predictions():
    try:
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        target_date = today
        import data_manager
        from utils_data import generate_predictions_for_date
        df = data_manager.fetch_upcoming_matches()
        predictions = generate_predictions_for_date(target_date, df)
        if not predictions and df is not None and not df.empty:
            df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
            for nd in sorted(df['date_str'].unique()):
                predictions = generate_predictions_for_date(nd, df)
                if predictions:
                    target_date = nd
                    break
        if predictions and DB_AVAILABLE:
            db.save_predictions(predictions)
        enriched = [{**pred, "home_team_info": _team_info(pred['home_team']), "away_team_info": _team_info(pred['away_team'])} for pred in predictions]
        return {"date": target_date, "predictions": enriched, "generated": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/dates/available")
async def available_dates():
    try:
        if DB_AVAILABLE:
            dates = db.get_available_dates()
        else:
            import data_manager
            df = data_manager.fetch_upcoming_matches()
            if df is not None and not df.empty:
                df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
                dates = sorted(df['date_str'].unique().tolist(), reverse=True)
            else:
                dates = []
        return {"dates": dates}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/worldcup/predictions")
async def worldcup_predictions():
    wc_path = os.path.join(_root, "data", "worldcup_predictions.json")
    if os.path.exists(wc_path):
        try:
            with open(wc_path) as f:
                return JSONResponse(content=json.load(f))
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})
    try:
        import predict_worldcup
        wc_tmp = "/tmp/worldcup_predictions.json"
        predict_worldcup.generate_and_save_predictions(wc_tmp)
        if os.path.exists(wc_tmp):
            with open(wc_tmp) as f:
                return JSONResponse(content=json.load(f))
    except Exception:
        pass
    return JSONResponse(content=[])
