# Prediction Accuracy Improvement — Design

**Date:** 2026-08-18
**Status:** Approved (design), pending implementation
**Goal:** Make predictions measurably more accurate, provable against the model's own history, with no new runtime dependencies and no frontend changes.

## Problem

The current prediction pipeline (`backend/train_model.py`, `backend/predictor.py`) is:

1. **Unmeasured** — `data/results/` is empty, so Brier/accuracy are never computed against real outcomes.
2. **Frozen** — models are retrained only by manual invocation; rolling stats and league averages come from the pickle snapshot at train time.
3. **Simplistic** — RandomForest regressors on raw team codes, elo, and 5-game uniform rolling goals/xG. No time decay, no elo gap, no league-relative form, no probability calibration.

## Approach: Champion/Challenger with backtest gate

Build `backend/evaluate.py`: a deterministic, fully offline temporal holdout over `training_data.pkl` (Understat, ~5 seasons). Train on seasons 1–4, score on the last season. Every candidate change is measured independently against the current pipeline (baseline) on Brier, log-loss, and accuracy. Only changes that beat the baseline are shipped. Losing variants are removed.

## Components

### 1. Backtest harness — `backend/evaluate.py`

- CLI: `python -m backend.evaluate [--all]` prints a comparison table: `spec | brier | log_loss | accuracy | n_matches`, seed 42.
- Split: `season_year_of(date)`; train = all seasons < last, test = last season.
- Shared scorer: given per-match home/away expected goals → `predictor.calculate_probabilities` → compare home/draw/away probabilities to actual outcome (1/0.5/0).
- Specs run through identical feature-building + scoring code; only model class and feature columns differ.
- Deterministic: fixed seed, stable sorts, no network.
- Baseline spec must reproduce today's production pipeline exactly (RF, current 8 features, same `calculate_rolling_stats`).

### 2. Challenger candidates (measured independently)

- **Features v2**: existing 8 features + `elo_gap` (home−away), time-decayed rolling goals/xG (exponential weights), league-relative form (rolling minus current-season league average).
- **Model**: `HistGradientBoostingRegressor(loss="poisson")` ×2 (home/away), `random_state=42`; fallback `squared_error` if poisson unsupported. Must beat RF baseline to ship.
- **Calibration**: isotropic mapping of predicted P(home/draw/away) → actual outcomes on the second half of the test season, evaluated on the first half; clamp to [0.01, 0.99]. Ships only if it beats uncalibrated.

### 3. Champion integration (baked in, not runtime-switched)

- `evaluate.py --all` produces the score table; the champion (baseline or challenger) is hard-coded into production after user approval of results.
- `model_meta.json` (beside `model_home.pkl` etc.) records the feature spec name; `predict_match` builds features per the meta at predict time, preventing silent train/predict mismatch.
- `simulate_season` needs no change — it takes lambdas from `predict_match`, so the forecast inherits the champion automatically.

### 4. Retraining workflow

- `train_model.py` retrains models + encoder + `training_data.pkl` + `model_meta.json` from fresh Understat data.
- Morning automation: retrain if model older than 7 days (graceful fallback to current models on network failure, like the forecast cache).
- CI: weekly retrain step committing only when the test-season score beats the committed model's recorded score (recorded in `model_meta.json`).

## Files

- New: `backend/evaluate.py`, `tests/test_evaluate.py`
- Modified: `backend/features.py` (decayed + league-relative builders), `backend/train_model.py` (shared feature/model build), `backend/predictor.py` (meta-driven feature build), `backend/automation.py` (stale-model retrain), `.github/workflows/morning_prediction.yml` (weekly retrain step)
- Kept: `backend/insights.py` sim (inherits champion), frontend (no changes)

## Constraints

- No new runtime Python dependencies (sklearn only; test-only additions allowed).
- No frontend changes; `predict_match` response shape unchanged (additive keys only if needed).
- All scoring offline and deterministic (seed 42).
- Honest data only: no fabricated results; empty calibration stays honest.

## Verification

- New tests: split correctness (test season = last), harness determinism (same seed → identical scores), train/predict feature consistency, calibration clamping, `model_meta` roundtrip, automation retrain staleness guard.
- Full suite stays green; manual `python -m backend.evaluate` shows the score table; champion result reported to user for approval before integration.