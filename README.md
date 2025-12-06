# Football Match Prediction App

A Python application that predicts Premier League football match outcomes using Machine Learning and Advanced Metrics.

## Features
- **Scraper-Only Architecture**: Fetches real-time fixtures and results directly from FBRef, with no external API dependencies.
- **Advanced Feature Engineering**:
  - **Expected Goals (xG)**: Learns from shot quality data, not just goals scored.
  - **ELO Rating System**: Dynamically tracks team strength relative to opponents.
  - **Rolling Form**: Analyzes the last 5 games for trends in scoring and xG.
- **Gameweek Filtering**: Automatically detects and displays matches for the upcoming Gameweek only.
- **Machine Learning**: Uses Random Forest Regressors to predict exact scorelines and match winners.

## Setup

1.  **Install Dependencies**
    ```bash
    pip install pandas scikit-learn requests lxml python-dotenv joblib numpy
    ```

2.  **Train Models**
    The app needs to build its knowledge base before predicting.
    ```bash
    python train_model.py
    ```
    This script will:
    - Scrape completed matches from the current season.
    - Calculate ELO ratings and Rolling Form stats.
    - Train the AI models.
    - Save the models (`model_home.pkl`, `model_away.pkl`) and state artifacts (`elo_state.pkl`, `training_data.pkl`).

3.  **Run Prediction**
    ```bash
    python main.py
    ```
    - The app will fetch the schedule.
    - It will filter to show only the **next Gameweek's** matches.
    - Select a match number to generate a prediction (Winner + Scoreline).

## Configuration
- `config.py`:
    - `SEASON`: Current season year (e.g., 2025).
    - `DEMO_MODE`: Set to `True` to simulate a specific date for testing. Default is `False`.

## Project Structure
- `main.py`: Entry point. Orchestrates data fetching, display, and user interaction.
- `train_model.py`: The "Brain". Scrapes data, engineers features, and trains the AI.
- `fbref_scraper.py`: Handles connection to FBRef to parse HTML tables for Scores and xG.
- `predictor.py`: Loads the trained brain to predict future matchups using the latest accumulated stats.
- `features.py`: Logic for complex metrics like ELO calculation and Rolling Averages.
- `match_manager.py`: Utilities for filtering and formatting match lists.
