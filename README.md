# Football Match Predictor

A full-stack application that predicts Premier League match outcomes using Machine Learning (Random Forest) and advanced metrics. Features a FastAPI backend, React frontend, and automated prediction pipeline.

## Features

- **ML-powered predictions**: Random Forest regressors trained on 5 seasons of historical data
- **Advanced feature engineering**: ELO ratings, rolling form (goals + xG), team encoding
- **Live data pipeline**: Fetches fixtures and results from ESPN/Understat/ClubElo via `soccerdata`
- **Automated daily jobs**: Morning prediction generation + evening result comparison
- **PostgreSQL persistence**: Optional database for teams, predictions, and historical tracking
- **World Cup 2026 simulator**: Full tournament prediction with group stage + knockout bracket
- **REST API**: FastAPI backend consumed by the React frontend
- **Vercel-ready**: Serverless-friendly `api/index.py` entry point

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Train models**
   ```bash
   python -m backend.train_model
   ```
   Fetches 5 seasons of Premier League data, engineers features, and saves model artifacts (`model_home.pkl`, `model_away.pkl`, `team_encoder.pkl`, `training_data.pkl`).

3. **Run the development server**
   ```bash
   python -m backend.server
   ```
   Starts the FastAPI server on port 8000. Frontend available at `http://localhost:5173`.

## Automation

Run the morning job to generate predictions:
```bash
python -m backend.automation morning
```

Run the evening job to compare predictions with actual results:
```bash
python -m backend.automation evening
```

## Project Structure

```
├── api/
│   └── index.py              # Vercel serverless entry point
├── backend/
│   ├── server.py              # FastAPI app (REST API endpoints)
│   ├── predictor.py           # ML prediction engine (Random Forest + Poisson)
│   ├── data_manager.py        # Fetches fixtures/results from soccerdata
│   ├── database.py            # PostgreSQL persistence layer
│   ├── features.py            # Rolling stats feature engineering
│   ├── utils.py               # Team name normalization
│   ├── utils_data.py          # JSON file I/O + prediction file management
│   ├── config.py              # Environment configuration
│   ├── train_model.py         # Model training pipeline
│   ├── automation.py          # Cron-style daily jobs (morning/evening)
│   ├── predict_worldcup.py    # World Cup 2026 tournament simulator
│   └── scripts/               # CLI utility scripts
│       ├── predict_matchweek.py
│       ├── fetch_and_save_matches.py
│       ├── migrate_to_db.py
│       ├── regenerate_predictions.py
│       └── debug_soccerdata.py
├── data/
│   ├── teams.json             # Premier League team metadata + badge URLs
│   ├── predictions/           # Generated predictions (JSON)
│   ├── results/               # Comparison results (JSON)
│   └── worldcup_predictions.json
├── frontend/                  # React + Vite + Tailwind CSS frontend
├── requirements.txt
├── vercel.json
└── .env                       # POSTGRES_URL (optional)
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Health check |
| `GET /api/teams` | Premier League teams with badge URLs |
| `GET /api/matches/upcoming` | Upcoming fixtures with ELO ratings |
| `GET /api/matches/predictions?date=` | Predictions for a specific date |
| `POST /api/matches/predictions/generate` | Generate predictions on-demand |
| `GET /api/matches/all` | All matches with predictions + gameweeks |
| `GET /api/matches/results?date=` | Result comparisons |
| `POST /api/predict?home_team=&away_team=` | Predict a single match |
| `GET /api/dates/available` | Available prediction dates |
| `GET /api/worldcup/predictions` | World Cup 2026 predictions |

## Configuration

- `POSTGRES_URL` env var enables PostgreSQL persistence (optional, falls back to JSON files)
- Models are stored as `.pkl` files in the project root (re-trained via `backend.train_model`)
