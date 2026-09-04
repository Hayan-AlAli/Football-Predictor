from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import os
from typing import Optional

from backend.predictor import predict_match
from backend import data_manager
from backend import utils
from backend import utils_data
from backend import database as db
from backend import insights

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


def predictor_module_training_df():
    try:
        from backend import predictor
        return predictor.training_df
    except Exception:
        return None


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
def get_upcoming_matches():
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
def get_predictions(date: Optional[str] = None):
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
def generate_predictions():
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


def _latest_season_year(all_preds):
    return max(_season_year(datetime.strptime(p['date'], '%Y-%m-%d')) for p in all_preds)


@app.get("/api/matches/all")
async def get_all_matches_with_predictions():
    try:
        matches = []
        gameweeks = set()

        if DB_AVAILABLE:
            all_preds = db.load_all_predictions()
            latest_year = _latest_season_year(all_preds)
            ordered = [
                p for p in all_preds
                if _season_year(datetime.strptime(p['date'], '%Y-%m-%d')) == latest_year
            ]
            ordered.sort(key=lambda p: (p['date'], p.get('time') or ''))

            for idx, pred in enumerate(ordered):
                gw = (idx // 10) + 1
                gameweeks.add(gw)
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
        raw_results = []
        if DB_AVAILABLE:
            try:
                raw_results = db.load_results(date) or []
            except Exception:
                raw_results = []
        if not raw_results:
            raw_results = utils_data.load_json(result_path) or []

        predictions = []
        if DB_AVAILABLE:
            try:
                predictions = db.load_predictions(date) or []
            except Exception:
                predictions = []
        if not predictions:
            pred_path = utils_data.get_prediction_file_path(date)
            predictions = utils_data.load_json(pred_path) or []

        results_map = {}
        for res in raw_results:
            key = (utils.normalize_team_name(res['home_team']),
                   utils.normalize_team_name(res['away_team']))
            results_map[key] = {
                'home_goals': int(res['home_goals']),
                'away_goals': int(res['away_goals']),
                'score': f"{int(res['home_goals'])}-{int(res['away_goals'])}"
            }

        def find_result(pred_home, pred_away):
            key = (utils.normalize_team_name(pred_home),
                   utils.normalize_team_name(pred_away))
            if key in results_map:
                return results_map[key]
            for (r_home, r_away), val in results_map.items():
                if (pred_home in r_home or r_home in pred_home) and (pred_away in r_away or r_away in pred_away):
                    return val
            return None

        comparison_results = []
        matched_result_keys = set()

        for pred in predictions:
            result_entry = {
                'match': pred,
                'actual': None,
                'status': 'PENDING'
            }

            actual = find_result(pred['home_team'], pred['away_team'])
            if actual is not None:
                result_entry['actual'] = actual
                matched_result_keys.add((
                    utils.normalize_team_name(pred['home_team']),
                    utils.normalize_team_name(pred['away_team']),
                ))

                hg = actual['home_goals']
                ag = actual['away_goals']
                if hg > ag:
                    actual_winner = pred['home_team']
                elif ag > hg:
                    actual_winner = pred['away_team']
                else:
                    actual_winner = "Draw"

                result_entry['actual']['winner'] = actual_winner

                predicted_winner = pred.get('prediction', {}).get('winner')
                if predicted_winner == actual_winner:
                    result_entry['status'] = 'CORRECT'
                else:
                    result_entry['status'] = 'INCORRECT'

            comparison_results.append(result_entry)

        for res in raw_results:
            key = (utils.normalize_team_name(res['home_team']),
                   utils.normalize_team_name(res['away_team']))
            if key not in matched_result_keys:
                comparison_results.append({
                    'match': {
                        'id': utils_data.generate_match_id(date, res['home_team'], res['away_team']),
                        'date': date,
                        'home_team': res['home_team'],
                        'away_team': res['away_team'],
                        'home_team_info': get_team_info(res['home_team']),
                        'away_team_info': get_team_info(res['away_team']),
                    },
                    'actual': {
                        'home_goals': int(res['home_goals']),
                        'away_goals': int(res['away_goals']),
                        'score': f"{int(res['home_goals'])}-{int(res['away_goals'])}",
                    },
                    'status': 'PENDING'
                })

        return {"date": date, "results": comparison_results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching results: {str(e)}")


@app.get("/api/dates/results")
async def get_result_dates():
    try:
        results_dir = utils_data.RESULTS_DIR
        dates = []
        if os.path.exists(results_dir):
            for filename in os.listdir(results_dir):
                if filename.endswith('.json'):
                    date_str = filename.replace('.json', '')
                    dates.append(date_str)
        if DB_AVAILABLE:
            try:
                dates = sorted(set(dates) | set(db.load_result_dates() or []))
            except Exception:
                pass
        dates.sort(reverse=True)
        return {"dates": dates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing result dates: {str(e)}")


@app.post("/api/predict")
def predict_single_match(home_team: str, away_team: str):
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


@app.get("/api/season/forecast")
def get_season_forecast():
    if DB_AVAILABLE:
        try:
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            db_forecast = db.load_forecast(today) or db.load_latest_forecast()
        except Exception:
            db_forecast = None
        if db_forecast is not None:
            return _forecast_with_team_info(db_forecast)
    cached = insights._today_forecast()
    if cached is not None:
        return _forecast_with_team_info(cached)
    forecast = insights.generate_forecast()
    if forecast is None:
        raise HTTPException(status_code=503, detail="Forecast unavailable")
    forecast = _forecast_with_team_info(forecast)
    insights.write_forecast_file(forecast)
    return forecast


def _forecast_with_team_info(forecast):
    """Attach badge/name info to every standings + projected row.

    Covers fresh payloads and cached files predating this field, so the
    forecast page can print real crests instead of initials.
    """
    for key in ("standings", "projected"):
        for row in forecast.get(key, []) or []:
            team = row.get("team")
            if team:
                row["team_info"] = {**get_team_info(team), "name": team}
    return forecast


@app.get("/api/calibration")
async def get_calibration():
    if DB_AVAILABLE:
        try:
            results_by_date = {d: (db.load_results(d) or []) for d in (db.load_result_dates() or [])}
            return insights.compute_calibration_from_records(db.load_all_predictions(), results_by_date)
        except Exception:
            pass
    return insights.compute_calibration()


@app.get("/api/teams/{team_name}")
def get_team_profile(team_name: str):
    profile = insights.team_profile(predictor_module_training_df(), team_name)
    if profile is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return {
        **profile,
        "upcoming": insights.upcoming_fixtures(profile["team"]),
        "team_info": {**get_team_info(profile["team"]), "name": profile["team"]},
    }


@app.get("/api/teams/{team_name}/h2h")
async def get_head_to_head(team_name: str, vs: Optional[str] = None):
    if not vs:
        raise HTTPException(status_code=400, detail="Missing vs parameter")
    h2h = insights.head_to_head(predictor_module_training_df(), team_name, vs)
    if h2h is None:
        raise HTTPException(status_code=404, detail="Head-to-head not found")
    return {
        **h2h,
        "team_a_info": get_team_info(h2h["team_a"]),
        "team_b_info": get_team_info(h2h["team_b"]),
    }


def _require_cron_secret(request: Request):
    expected = os.environ.get("CRON_SECRET")
    if not expected or request.headers.get("authorization") != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.api_route("/api/jobs/morning", methods=["GET", "POST"])
def run_morning_job_endpoint(request: Request):
    _require_cron_secret(request)
    from backend import automation
    try:
        summary = automation.run_morning_job(use_db=DB_AVAILABLE)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Morning job failed: {e}")
    return summary


@app.api_route("/api/jobs/evening", methods=["GET", "POST"])
def run_evening_job_endpoint(request: Request):
    _require_cron_secret(request)
    from backend import automation
    try:
        summary = automation.run_evening_job(use_db=DB_AVAILABLE)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evening job failed: {e}")
    return summary


if __name__ == "__main__":
    import uvicorn
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run("backend.server:app", host="0.0.0.0", port=port, reload=True)
