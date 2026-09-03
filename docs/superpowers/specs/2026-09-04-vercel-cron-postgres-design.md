# Design: Vercel Cron + Postgres jobs, data files leave the repo

## Goal
Replace file-committing GitHub automation with Vercel Cron jobs that write to
Postgres, so `data/predictions/`, `data/results/`, and `data/forecast/` can be
deleted from git. The site's purpose is unchanged: visitors see results and
compare them against predictions (Records, Calibration, Forecast pages).

## Decisions (user-approved)
- Scheduler: Vercel Cron (fallback: point GitHub Actions at the same endpoints).
- Forecast: cron precomputes the 10k sim once into the DB; the API serves the row.
- Cleanup: delete all data files from git; local dev keeps working via file fallback.

## Architecture
- `vercel.json` gains two cron entries (06:00 and 22:30 UTC) POSTing to
  `/api/jobs/morning` and `/api/jobs/evening` with
  `Authorization: Bearer $CRON_SECRET`.
- The endpoints call the existing automation logic in `backend/automation.py`,
  refactored so the same functions serve CLI, cron, and tests with the store
  injected (Postgres in prod, files locally).
- Read endpoints keep their response shapes; their source flips to DB-first.
  The frontend needs no edits.

## Data model
- `results` table: `match_date DATE`, `home_team`, `away_team`, `home_goals`,
  `away_goals`; primary key on `(match_date, home_team, away_team)`.
- `forecast_cache` table: `match_date DATE PRIMARY KEY`, `payload JSONB`,
  `created_at TIMESTAMPTZ DEFAULT NOW()`.
- `database.py` gains `save/load_results` and `save/load_forecast`;
  `init_db` creates both tables. The `predictions` table is unchanged.

## Job behavior
- Morning endpoint: ESPN fixture scrape, training-data Elo fallback,
  predictions for today upserted into `predictions`, one 10k simulation
  stored in `forecast_cache`. Must fit the 60s hobby limit: on timeout it
  returns partial success (predictions saved, forecast flagged stale)
  instead of failing silently.
- Evening endpoint: Understat results fetch with 3-day backfill into
  `results`, skipping already-recorded dates.
- Both endpoints verify `CRON_SECRET` first (401 otherwise) and log counts.

## Reads and cleanup
- `get_results`, `compute_calibration`, `get_result_dates`, and the forecast
  endpoint read DB first, files second.
- `git rm` the three data dirs, gitignore them, delete the
  morning/evening workflows (the soccerdata test workflow stays).

## Error handling
- Scraper failure: HTTP 500 naming the failed source (visible in Vercel logs).
- DB outage: HTTP 503; jobs never fall back to writing files in prod.
- Cron overlap is safe: every write is a date-keyed upsert.

## Testing
- Unit tests for the new DB functions (save/load round-trip, upsert idempotence).
- Endpoint tests for both jobs plus the 401 path, using a temp DB or fakes.
- Existing file-fallback tests stay green (local-dev contract).

## Open risks
- Vercel hobby cron frequency limits and the 60s function cap must be verified
  during implementation; if either bites, the fallback is GitHub Actions
  triggering the same endpoints.
- Postgres becomes load-bearing in prod; a DB outage offlines data pages
  instead of serving stale files.
