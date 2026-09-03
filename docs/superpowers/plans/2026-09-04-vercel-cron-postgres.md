# Vercel Cron + Postgres Jobs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move morning/evening jobs from file-committing GitHub Actions to Vercel Cron endpoints backed by Postgres, then delete data files from git.

**Architecture:** Two secret-guarded POST endpoints call the existing automation functions (extended with a `use_db` flag); reads go DB-first with file fallback; `vercel.json` schedules the crons.

**Tech Stack:** FastAPI, psycopg2 (existing `backend/database.py` patterns), Vercel Cron, pytest + FastAPI TestClient.

## Global Constraints

- API response shapes do not change; the frontend needs no edits.
- Every write is a date-keyed upsert (cron overlap safe).
- File fallback stays for local dev; prod never writes files.
- TDD: failing test first for every behavior change; commit per task.

---

### Task 1: `results` and `forecast_cache` tables + accessors

**Files:**
- Modify: `backend/database.py`
- Test: `tests/test_db_jobs.py` (create)

**Interfaces:**
- Consumes: existing `get_db()` context manager, `_to_native()`.
- Produces: `save_results(rows)`, `load_results(date_str)`, `load_result_dates()`, `save_forecast(date_str, payload)`, `load_forecast(date_str)`, `load_latest_forecast()` — used by Tasks 2, 4, 5.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from backend import database as db

needs_db = pytest.mark.skipif(db.DATABASE_URL is None, reason="POSTGRES_URL not set")


@needs_db
def test_save_and_load_results_roundtrip():
    db.init_db()
    rows = [{"date": "2026-01-03", "home_team": "Arsenal", "away_team": "Chelsea",
             "home_goals": 2, "away_goals": 1}]
    db.save_results(rows)
    loaded = db.load_results("2026-01-03")
    assert {"home_team": "Arsenal", "away_team": "Chelsea",
            "home_goals": 2, "away_goals": 1} in loaded


@needs_db
def test_save_results_upsert_is_idempotent():
    rows = [{"date": "2026-01-03", "home_team": "Arsenal", "away_team": "Chelsea",
             "home_goals": 2, "away_goals": 1}]
    db.save_results(rows)
    db.save_results(rows)
    assert len(db.load_results("2026-01-03")) == 1


@needs_db
def test_save_and_load_forecast_roundtrip():
    db.init_db()
    payload = {"generated": "2026-01-03", "entries": 1}
    db.save_forecast("2026-01-03", payload)
    assert db.load_forecast("2026-01-03") == payload
    assert db.load_latest_forecast()["generated"] == "2026-01-03"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_db_jobs.py -v`
Expected: FAIL with `AttributeError` (`save_results` not defined). If skipped instead (no `POSTGRES_URL`), set it from `.env` first — these tests require the dev database.

- [ ] **Step 3: Write minimal implementation**

In `backend/database.py`, extend `init_db()` with:

```python
cur.execute("""
    CREATE TABLE IF NOT EXISTS results (
        match_date DATE NOT NULL,
        home_team TEXT NOT NULL,
        away_team TEXT NOT NULL,
        home_goals DOUBLE PRECISION,
        away_goals DOUBLE PRECISION,
        PRIMARY KEY (match_date, home_team, away_team)
    );
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS forecast_cache (
        match_date DATE PRIMARY KEY,
        payload JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
""")
```

Add (place after `get_available_dates`):

```python
def save_results(rows):
    with get_db() as conn:
        cur = conn.cursor()
        for r in rows:
            cur.execute("""
                INSERT INTO results (match_date, home_team, away_team, home_goals, away_goals)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (match_date, home_team, away_team) DO UPDATE SET
                    home_goals = EXCLUDED.home_goals,
                    away_goals = EXCLUDED.away_goals
            """, (r['date'], r['home_team'], r['away_team'],
                  _to_native(r.get('home_goals')), _to_native(r.get('away_goals'))))


def load_results(date_str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT home_team, away_team, home_goals, away_goals FROM results WHERE match_date = %s",
            (date_str,)
        )
        return [dict(r) for r in cur.fetchall()]


def load_result_dates():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT match_date FROM results ORDER BY match_date DESC")
        rows = cur.fetchall()
        return [row['match_date'].isoformat() for row in rows]


def save_forecast(date_str, payload):
    from psycopg2.extras import Json
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO forecast_cache (match_date, payload)
            VALUES (%s, %s)
            ON CONFLICT (match_date) DO UPDATE SET
                payload = EXCLUDED.payload,
                created_at = NOW()
        """, (date_str, Json(payload)))


def _row_to_forecast(row):
    return dict(row['payload'])


def load_forecast(date_str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT payload FROM forecast_cache WHERE match_date = %s", (date_str,))
        row = cur.fetchone()
        return _row_to_forecast(row) if row else None


def load_latest_forecast():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT payload FROM forecast_cache ORDER BY match_date DESC LIMIT 1")
        row = cur.fetchone()
        return _row_to_forecast(row) if row else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_db_jobs.py -v`
Expected: PASS (4 passed, or remaining tests pass alongside).

- [ ] **Step 5: Commit**

```bash
git add backend/database.py tests/test_db_jobs.py
git commit -m "feat: results and forecast_cache tables with accessors"
```

---

### Task 2: Automation jobs gain a `use_db` store flag

**Files:**
- Modify: `backend/automation.py`
- Test: `tests/test_automation.py` (append)

**Interfaces:**
- Consumes: `db.save_predictions`, `db.save_results`, `db.save_forecast` (Task 1), existing `utils_data`/`data_manager`/`insights` calls.
- Produces: `run_morning_job(use_db=False)`, `run_evening_job(use_db=False, lookback_days=3)` returning summary dicts — used by Task 3.

- [ ] **Step 1: Write the failing test**

```python
import pandas as pd


def test_morning_job_db_returns_summary(monkeypatch):
    from backend import automation
    monkeypatch.setattr(automation.data_manager, "fetch_upcoming_matches", lambda: pd.DataFrame())
    summary = automation.run_morning_job(use_db=False)
    assert summary == {"date": summary["date"], "predictions": 0, "forecast": None}
```

(Returning a summary dict is the new contract; current functions return `None`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_automation.py::test_morning_job_db_returns_summary -v`
Expected: FAIL (`TypeError` unpacking `None`, or `assert None == ...`).

- [ ] **Step 3: Write minimal implementation**

Change signatures to `def run_morning_job(use_db=False):` and
`def run_evening_job(use_db=False, lookback_days=3):`, returning
`{"date": ..., "predictions": n, "forecast": ...}` /
`{"saved": [(date, n), ...]}`.

Morning DB branch (after `predictions` is built, replacing the file write when `use_db` is true):

```python
if use_db:
    from backend import database as db
    if not db.DATABASE_URL:
        raise RuntimeError("POSTGRES_URL not set")
    db.init_db()
    db.save_predictions(predictions)
else:
    output_path = utils_data.get_prediction_file_path(current_date_str)
    utils_data.save_json(predictions, output_path)
```

Forecast: replace `forecast_path = insights.write_forecast_file()` with:

```python
if use_db:
    from backend import database as db
    forecast = insights.generate_forecast()
    if forecast:
        db.save_forecast(current_date_str, forecast)
        print(f"Forecast cached in DB for {current_date_str}")
    summary_forecast = bool(forecast)
else:
    forecast_path = insights.write_forecast_file()
```

Order matters for the spec's partial-success rule: predictions are saved
before the forecast sim runs, so a 60s timeout still leaves predictions
behind (the next morning run regenerates the forecast).

Evening DB branch: inside the date loop, replace the `os.path.exists` check with a DB check when `use_db`:

```python
if use_db:
    from backend import database as db
    if db.load_results(date_str):
        print(f"Results already recorded for {date_str}, skipping.")
        continue
```

and replace `utils_data.save_json(completed_matches, output_path)` with:

```python
if use_db:
    db.save_results([{"date": date_str, **r} for r in completed_matches])
else:
    utils_data.save_json(completed_matches, output_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_automation.py -v`
Expected: PASS (all 4 existing + new tests).

- [ ] **Step 5: Commit**

```bash
git add backend/automation.py tests/test_automation.py
git commit -m "feat: automation jobs support Postgres store via use_db"
```

---

### Task 3: Secret-guarded job endpoints

**Files:**
- Modify: `backend/server.py`
- Test: `tests/test_endpoints.py` (append)

**Interfaces:**
- Consumes: `automation.run_morning_job(use_db=...)` (Task 2), `db.DATABASE_URL`.
- Produces: `POST /api/jobs/morning`, `POST /api/jobs/evening` — used by Task 6 crons.

- [ ] **Step 1: Write the failing test**

```python
def test_jobs_require_secret():
    r = _client().post("/api/jobs/morning")
    assert r.status_code == 401


def test_morning_job_ok(monkeypatch):
    import os
    from backend import automation
    monkeypatch.setenv("CRON_SECRET", "test-secret")
    monkeypatch.setattr(automation, "run_morning_job",
                        lambda use_db: {"date": "2026-01-03", "predictions": 5, "forecast": True})
    r = _client().post("/api/jobs/morning", headers={"Authorization": "Bearer test-secret"})
    assert r.status_code == 200
    assert r.json()["predictions"] == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_endpoints.py::test_jobs_require_secret -v`
Expected: FAIL with 404 (no such route).

- [ ] **Step 3: Write minimal implementation**

```python
import os
from fastapi import Request


def _require_cron_secret(request: Request):
    expected = os.environ.get("CRON_SECRET")
    if not expected or request.headers.get("authorization") != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.post("/api/jobs/morning")
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


@app.post("/api/jobs/evening")
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_endpoints.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/server.py tests/test_endpoints.py
git commit -m "feat: secret-guarded job endpoints for cron"
```

---

### Task 4: Reads go DB-first (results + calibration)

**Files:**
- Modify: `backend/insights.py`, `backend/server.py`
- Test: `tests/test_insights.py` (append; uses existing `_write_cal_fixture` style via new core fn)

**Interfaces:**
- Consumes: `db.load_results`, `db.load_result_dates`, `db.load_all_predictions` (Task 1).
- Produces: unchanged response shapes for `/api/matches/results`, `/api/dates/results`, `/api/calibration`.

- [ ] **Step 1: Write the failing test**

```python
def test_calibration_from_records_pairs_db_rows():
    from backend.insights import compute_calibration_from_records
    predictions = [
        {"date": "2026-01-03", "home_team": "Arsenal", "away_team": "Chelsea",
         "prediction": {"prob_home": 0.8, "prob_draw": 0.1, "prob_away": 0.1, "winner": "Arsenal"}},
    ]
    results_by_date = {
        "2026-01-03": [{"home_team": "Wolves", "away_team": "Chelsea",
                        "home_goals": 0, "away_goals": 2}],
    }
    # Wolves != Arsenal: no pair -> zero entries, but must not crash
    res = compute_calibration_from_records(predictions, results_by_date)
    assert res["entries"] == 0
    results_by_date["2026-01-03"][0]["home_team"] = "Arsenal"
    res = compute_calibration_from_records(predictions, results_by_date)
    assert res["entries"] == 1 and res["accuracy"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_insights.py::test_calibration_from_records_pairs_db_rows -v`
Expected: FAIL (`compute_calibration_from_records` not defined).

- [ ] **Step 3: Write minimal implementation**

In `backend/insights.py`, extract the per-date pairing loop of
`compute_calibration` into:

```python
def compute_calibration_from_records(predictions, results_by_date):
    """Core pairing over in-memory records.

    predictions: list of prediction dicts (each with date/home_team/away_team/prediction).
    results_by_date: {date_str: [raw result dicts]}.
    Returns the same CalibrationData dict as compute_calibration.
    """
```

Move the existing `results_map` / `find_result` / entry-building / binning
code into it operating on the passed lists (keep `_norm_pair` and wrapped-format
handling verbatim), and make `compute_calibration(predictions_dir=None,
results_dir=None)` load files per date then delegate:

```python
    by_date = {}
    for date_str, preds, raw in _iter_date_files(res_dir, pred_dir):
        ...
    return compute_calibration_from_records(all_preds, by_date)
```

(Keep it mechanical: collect `(preds, raw)` per date from the existing loop,
then delegate. Existing calibration tests must keep passing unmodified.)

In `backend/server.py`:
- `get_results`: when `DB_AVAILABLE`, `raw_results = db.load_results(date)`
  (dicts already in raw schema) instead of file load; keep file fallback.
- `get_result_dates`: return sorted union of `db.load_result_dates()` and
  file dates when `DB_AVAILABLE`.
- `get_calibration`: when `DB_AVAILABLE`, build
  `results_by_date = {d: db.load_results(d) for d in db.load_result_dates()}`
  and return `compute_calibration_from_records(db.load_all_predictions(), results_by_date)`;
  else `compute_calibration()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_insights.py tests/test_endpoints.py -q`
Expected: PASS, including the two pre-existing calibration tests unmodified.

- [ ] **Step 5: Commit**

```bash
git add backend/insights.py backend/server.py tests/test_insights.py
git commit -m "feat: results and calibration read Postgres first"
```

---

### Task 5: Forecast endpoint serves the DB cache

**Files:**
- Modify: `backend/server.py`
- Test: `tests/test_endpoints.py` (append)

**Interfaces:**
- Consumes: `db.load_forecast`, `db.load_latest_forecast` (Task 1), existing `_forecast_with_team_info`.
- Produces: unchanged forecast response shape.

- [ ] **Step 1: Write the failing test**

```python
def test_season_forecast_serves_db_cache(monkeypatch):
    from backend import database as db
    payload = {"generated": "2026-01-03", "season_year": 2026, "n_sims": 10,
               "season_complete": False, "standings": [], "projected": [],
               "fixtures_remaining": 0}
    monkeypatch.setattr(db, "load_forecast", lambda d: payload)
    monkeypatch.setattr(db, "load_latest_forecast", lambda: payload)
    monkeypatch.setattr(server, "DB_AVAILABLE", True)
    monkeypatch.setattr(insights, "_today_forecast", lambda: None)
    monkeypatch.setattr(insights, "generate_forecast",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not recompute")))
    r = _client().get("/api/season/forecast")
    assert r.status_code == 200
    assert r.json()["generated"] == "2026-01-03"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_endpoints.py::test_season_forecast_serves_db_cache -v`
Expected: FAIL (endpoint never calls `db.load_forecast`).

- [ ] **Step 3: Write minimal implementation**

```python
@app.get("/api/season/forecast")
def get_season_forecast():
    if DB_AVAILABLE:
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        db_forecast = db.load_forecast(today) or db.load_latest_forecast()
        if db_forecast is not None:
            return _forecast_with_team_info(db_forecast)
    cached = insights._today_forecast()
    if cached is not None:
        return _forecast_with_team_info(cached)
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_endpoints.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/server.py tests/test_endpoints.py
git commit -m "feat: forecast endpoint serves Postgres cache first"
```

---

### Task 6: Crons, secrets, workflow + file cleanup

**Files:**
- Modify: `vercel.json`, `.gitignore`
- Delete: `.github/workflows/morning_prediction.yml`, `.github/workflows/evening_results.yml`, `data/predictions/`, `data/results/`, `data/forecast/`

**Interfaces:**
- Consumes: Task 3 endpoints.
- Produces: scheduled prod jobs; a repo with no data blobs.

- [ ] **Step 1: Verify hobby cron limits (no code)**

In the Vercel dashboard for `football-predictor`, check Settings → Cron Jobs:
concurrent crons allowed and minimum interval on the hobby plan. If two
daily crons are not allowed, stop and fall back to GitHub Actions calling
the Task 3 endpoints (10-line workflow, endpoints unchanged).

- [ ] **Step 2: Add crons to `vercel.json`**

```json
{
  "crons": [
    {"path": "/api/jobs/morning", "schedule": "0 6 * * *"},
    {"path": "/api/jobs/evening", "schedule": "30 22 * * *"}
  ]
}
```

Vercel signs cron requests with `Authorization: Bearer $CRON_SECRET` automatically
when `CRON_SECRET` is set in project env — no extra wiring. Add `CRON_SECRET`
(a fresh random value) in the Vercel dashboard; it is read by
`_require_cron_secret` (Task 3).

- [ ] **Step 3: Delete workflows and data from git**

```bash
git rm -r data/predictions data/results data/forecast
git rm .github/workflows/morning_prediction.yml .github/workflows/evening_results.yml
```

Append to `.gitignore`:

```
# Runtime data (Postgres in prod, local files in dev)
data/predictions/
data/results/
data/forecast/
```

Keep `data/teams.json` and the model `.pkl`s tracked.

- [ ] **Step 4: Deploy and trigger manually**

```bash
vercel --prod --yes
```

Then trigger both jobs once with the secret and confirm rows land:

```bash
curl -X POST https://football-predictor-rho.vercel.app/api/jobs/evening -H "Authorization: Bearer $CRON_SECRET"
```

Check `/api/dates/results` and `/api/calibration` afterward.

- [ ] **Step 5: Commit**

```bash
git add vercel.json .gitignore .github/workflows
git commit -m "chore: Vercel Cron jobs replace file-committing workflows"
```

Note: the `git rm` deletions are committed in this same step (stage everything first, single commit).

---

### Task 7: Full verification

- [ ] **Step 1: Run the backend suite**

Run: `pytest tests/test_db_jobs.py tests/test_automation.py tests/test_endpoints.py tests/test_insights.py -q`
Expected: all PASS (except the known pre-existing `test_generate_forecast_handles_nan_elo` failure, which is out of scope).

- [ ] **Step 2: Typecheck the frontend (no frontend edits expected)**

Run from `frontend/`: `.\node_modules\.bin\tsc --noEmit`
Expected: exit 0.

- [ ] **Step 3: Confirm prod reads**

`GET /api/matches/results?date=<today>`, `/api/calibration`, `/api/season/forecast`
return DB-backed payloads with no shape changes.
