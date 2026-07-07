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

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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
        import data_manager
        from utils_data import generate_predictions_for_date
        df = data_manager.fetch_upcoming_matches()
        predictions = generate_predictions_for_date(date, df)
        enriched = [{**pred, "home_team_info": _team_info(pred['home_team']), "away_team_info": _team_info(pred['away_team'])} for pred in predictions]
        return {"date": date, "predictions": enriched}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/matches/predictions/generate")
async def generate_predictions():
    try:
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        import data_manager
        from utils_data import generate_predictions_for_date
        df = data_manager.fetch_upcoming_matches()
        predictions = generate_predictions_for_date(today, df)
        enriched = [{**pred, "home_team_info": _team_info(pred['home_team']), "away_team_info": _team_info(pred['away_team'])} for pred in predictions]
        return {"date": today, "predictions": enriched, "generated": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/dates/available")
async def available_dates():
    try:
        import data_manager
        df = data_manager.fetch_upcoming_matches()
        if df is not None and not df.empty:
            df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
            dates = sorted(df['date_str'].unique().tolist(), reverse=True)
            return {"dates": dates}
        return {"dates": []}
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
