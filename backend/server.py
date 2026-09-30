"""HTTP API. Read endpoints only ever read the database; the sync job
(backend/sync.py) is the only writer, triggered by Vercel cron."""
import hmac
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from backend import db, insights, predictor
from backend import teams as registry
from backend.gameweeks import assign_gameweeks

logger = logging.getLogger(__name__)

VERSION = "2.0.0"

app = FastAPI(title="Football Predictor API",
              description="Premier League match predictions", version=VERSION)

_origins = [o.strip() for o in os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["GET"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1024)

# Data only changes when the sync job runs, so let Vercel's edge serve reads:
# fresh for 5 minutes, then stale-while-revalidate for a day.
_CACHEABLE = ("/api/matches", "/api/teams", "/api/forecast", "/api/calibration")
_CACHE_HEADER = "public, max-age=60, s-maxage=300, stale-while-revalidate=86400"


@app.middleware("http")
async def cache_headers(request: Request, call_next):
    response = await call_next(request)
    if (request.method == "GET" and response.status_code == 200
            and request.url.path.startswith(_CACHEABLE)):
        response.headers.setdefault("Cache-Control", _CACHE_HEADER)
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.exception("unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def _today():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def _present(match, gameweeks=None):
    """A match as the frontend prints it: team objects, score, verdict."""
    out = {
        **match,
        'home_team_info': db.team_info(match['home_team']),
        'away_team_info': db.team_info(match['away_team']),
        'gameweek': (gameweeks or {}).get(match['id']),
        'verdict': insights.verdict(match),
        'actual': None,
    }
    if match['status'] == 'finished' and match['home_goals'] is not None:
        hg, ag = match['home_goals'], match['away_goals']
        out['actual'] = {
            'home_goals': hg, 'away_goals': ag, 'score': f"{hg}-{ag}",
            'winner': match['home_team'] if hg > ag else match['away_team'] if ag > hg else 'Draw',
        }
    return out


def _season_or_latest(season):
    return season if season is not None else (db.latest_season() or db.season_of(_today()))


@app.get("/")
@app.get("/api/health")
def health():
    body = {"status": "online", "version": VERSION}
    try:
        db.ping()
        body["database"] = db.engine().dialect.name
        body["last_runs"] = db.last_runs()
    except Exception as e:
        logger.warning("health: database unavailable: %s", e)
        body["database"] = "unavailable"
    return body


@app.get("/api/teams")
def get_teams(season: Optional[int] = None):
    """Clubs of a season (default: the latest), with badges and colours."""
    season = _season_or_latest(season)
    names = sorted({t for m in db.load_matches(season=season, with_predictions=False)
                    for t in (m['home_team'], m['away_team'])})
    return {"season": season, "teams": [db.team_info(n) for n in names or registry.registered()]}


@app.get("/api/matches")
def get_matches(season: Optional[int] = None, team: Optional[str] = None):
    """Every match of a season: fixture, prediction, result and verdict in
    one row. One request serves the matchday, records and teams pages."""
    season = _season_or_latest(season)
    rows = db.load_matches(season=season)
    gameweeks = assign_gameweeks([m for m in rows if m['status'] != 'postponed'])
    if team:
        canon = registry.from_slug(team)
        rows = [m for m in rows if canon in (m['home_team'], m['away_team'])]
    matches = [_present(m, gameweeks) for m in rows]
    return {"season": season, "matches": matches, "gameweeks": sorted(set(gameweeks.values()))}


@app.get("/api/forecast")
def get_forecast():
    forecast = db.latest_forecast()
    if forecast is None:
        raise HTTPException(status_code=503, detail="Forecast unavailable")
    for key in ("standings", "projected"):
        for row in forecast.get(key) or []:
            if row.get("team"):
                row["team_info"] = db.team_info(row["team"])
    return forecast


@app.get("/api/calibration")
def get_calibration():
    return insights.compute_calibration(db.load_matches(status='finished'))


@app.get("/api/teams/{team}")
def get_team_profile(team: str):
    canon = registry.from_slug(team)
    from backend import elo
    profile = insights.team_profile(predictor.form_frame(), canon,
                                    current_elo=elo.current_ratings().get(canon))
    if profile is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return {
        **profile,
        "upcoming": [_present(m) for m in insights.upcoming_fixtures(profile["team"])],
        "team_info": db.team_info(profile["team"]),
    }


@app.get("/api/teams/{team}/h2h")
def get_head_to_head(team: str, vs: str):
    h2h = insights.head_to_head(predictor.form_frame(), registry.from_slug(team), registry.from_slug(vs))
    if h2h is None:
        raise HTTPException(status_code=404, detail="Head-to-head not found")
    return {**h2h, "team_a_info": db.team_info(h2h["team_a"]), "team_b_info": db.team_info(h2h["team_b"])}


@app.get("/api/predict")
def predict(home: str, away: str):
    """An on-demand prediction for any pairing (nothing is stored)."""
    home, away = registry.from_slug(home), registry.from_slug(away)
    if home == away:
        raise HTTPException(status_code=400, detail="A team cannot play itself")
    return {"home_team_info": db.team_info(home), "away_team_info": db.team_info(away),
            "prediction": predictor.predict_match({"home_team": home, "away_team": away})}


def _require_cron_secret(request: Request):
    expected = os.environ.get("CRON_SECRET")
    supplied = request.headers.get("authorization") or ""
    if not expected or not hmac.compare_digest(supplied.encode(), f"Bearer {expected}".encode()):
        raise HTTPException(status_code=401, detail="Unauthorized")


# morning/evening are the old cron paths, kept so a stale cron config still works.
@app.api_route("/api/jobs/sync", methods=["GET", "POST"])
@app.api_route("/api/jobs/morning", methods=["GET", "POST"], include_in_schema=False)
@app.api_route("/api/jobs/evening", methods=["GET", "POST"], include_in_schema=False)
def run_sync_job(request: Request, forecast: bool = False):
    """forecast=true rebuilds the season forecast even when it is not due."""
    _require_cron_secret(request)
    from backend import sync
    try:
        return sync.run_sync(force_forecast=forecast)
    except Exception as e:
        logger.exception("sync failed")
        raise HTTPException(status_code=502, detail=f"Sync failed: {e}")


if __name__ == "__main__":
    import sys
    import uvicorn
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    # Dev server with auto-reload: keep it on this machine, off the LAN.
    uvicorn.run("backend.server:app", host="127.0.0.1", port=port, reload=True)
