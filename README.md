# Football Match Predictor

Premier League match predictions: a FastAPI backend, a React frontend, and one
scheduled sync job that keeps everything current.

## How it fits together

```
ESPN scoreboard API ──┐                         ┌── GET /api/matches   (one call per page)
football-data.co.uk ──┤→ backend/sync.py → DB ──┼── GET /api/teams, /api/forecast, ...
 (fallback results)   │  (cron, idempotent)     └── React frontend
data/teams.json ──────┘
```

- **One source of match truth.** `backend/sources/espn.py` reads ESPN's public
  scoreboard JSON: a season's fixtures, kickoffs, statuses, scores and club
  crests in one pass, no scraping library. If ESPN is down, results still come
  in from football-data.co.uk.
- **Matches, not days.** The `matches` table has one row per fixture, keyed
  `season-home-away` (e.g. `2026-arsenal-chelsea`). In a double round-robin
  each ordered pairing meets once a season, so the key survives reschedules
  and feed renames. The fixture, the model's call and the result all live on
  the same row, so there are no stale duplicates and no name matching to pair
  a result with its prediction.
- **Frozen calls.** Predictions refresh daily until kickoff, then never
  change. That frozen call is what the Records page judges. The one
  exception: a played match whose stored call is a flat 33/34/33 placeholder
  (a bug before 24 Sep 2026 froze those onto matchweeks 4 and 5) is rebuilt
  by the sync from pre-match Elo and form only, tagged `+rebuilt` and marked
  on its card.
- **One team registry.** `data/teams.json` holds every club's canonical name,
  aliases, URL slug, ESPN id, Premier League id and colour. Badges are 500px
  ESPN crests with the Premier League crest as fallback, then initials. Crest
  URLs synced from the feed are stored in the `teams` table. A newly promoted
  club gets its crest automatically, even before it is added to the registry.
- **One storage layer.** `backend/db.py` (SQLAlchemy Core) runs on Postgres in
  production and SQLite everywhere else. No parallel JSON-file mode.

## Setup

```bash
pip install -r requirements-dev.txt        # runtime + pytest
python -m backend.sync                     # pull the season, predict, forecast
python -m backend.server                   # API on :8000
cd frontend && npm install && npm run dev  # UI on :5173
```

Without `POSTGRES_URL` the app uses SQLite at `data/football.db`.

## Configuration

| Variable | Purpose |
|---|---|
| `POSTGRES_URL` / `DATABASE_URL` | Postgres connection (Vercel sets `POSTGRES_URL`). Unset → SQLite. |
| `CRON_SECRET` | Bearer token required by `/api/jobs/sync` (Vercel Cron sends it). |
| `CORS_ORIGINS` | Comma-separated origins for local cross-origin dev (default: localhost:5173, :3000). |

## Security

- The only write path is `/api/jobs/sync`, guarded by `CRON_SECRET`
  (constant-time compare; no secret configured means no access).
- Every other endpoint is a public, read-only view of public match data.
  SQL goes through SQLAlchemy Core with bound parameters.
- `vercel.json` sends a strict Content-Security-Policy (scripts from the
  site only), HSTS, `nosniff`, no framing and a restrictive Permissions-Policy.
- The bundled `*.pkl` models are loaded with joblib (pickle): only ever
  replace them with files you trained yourself.

## API

All reads are served from the database and cached at the edge
(`s-maxage=300, stale-while-revalidate`); data only changes when the sync runs.

| Endpoint | Description |
|---|---|
| `GET /api/health` | Status, database dialect, last sync run |
| `GET /api/matches?season=&team=` | Every match of a season: fixture, prediction, result, verdict, matchweek, team info |
| `GET /api/teams?season=` | The season's clubs with slug, crest and colour |
| `GET /api/teams/{slug-or-name}` | Club profile, form, Elo history, upcoming fixtures |
| `GET /api/teams/{team}/h2h?vs=` | Head-to-head record |
| `GET /api/forecast` | Latest Monte Carlo season forecast |
| `GET /api/calibration` | Accuracy, Brier score and calibration bins over settled calls |
| `GET /api/predict?home=&away=` | Ad-hoc prediction for any pairing (not stored) |
| `GET/POST /api/jobs/sync?forecast=true` | Run the sync (cron secret required) |

## The sync job

`python -m backend.sync` (or the cron hitting `/api/jobs/sync` at 06:00 and
22:30 UTC):

1. pulls the current season from ESPN and upserts clubs and matches;
2. drops unplayed fixtures the feed no longer lists (only after a complete pull);
3. predicts every unplayed match kicking off in the next 28 days;
4. rebuilds the season forecast on Mondays, when new results arrived, or on `?forecast=true`.

It is idempotent: a missed run is caught up by the next one. Each run is
logged in `job_runs` and reported by `/api/health`.

## Model

Random Forest goal regressors (Elo, Elo gap, multi-window form and xG) feed a
Poisson scoreline model. If the model files are missing or fail, predictions
fall back to an Elo-only Poisson model, tagged `model_version = "elo-poisson"`.
Elo is computed in-house (`backend/elo.py`) from every result since 1995/96.

Retraining is offline and needs the extra training dependencies:

```bash
pip install -r requirements-train.txt
python -m backend.train_model
```

`scikit-learn` is pinned to the version the bundled pickles were saved with.
Retrain before bumping it.

## Upgrading from the pre-2.0 schema

Nothing to run by hand. On first start against a database holding the old
`predictions` / `results` / `fixtures` / `forecast_cache` tables, the app copies
them into the new schema: stale twins collapse, and each result attaches to
the prediction it settles. The old `teams` table gets its new columns. The old
tables are otherwise left in place and can be dropped once you are happy.

## Tests

```bash
python -m pytest                                           # SQLite
TEST_DATABASE_URL=postgresql://... python -m pytest        # against a throwaway Postgres (schema is wiped!)
cd frontend && npm test
```
