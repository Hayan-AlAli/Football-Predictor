import os
from dotenv import load_dotenv

load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from datetime import datetime, timezone

DATABASE_URL = os.environ.get("POSTGRES_URL")

_initialized = False

@contextmanager
def get_db():
    if not DATABASE_URL:
        raise RuntimeError("POSTGRES_URL environment variable not set")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    global _initialized
    if _initialized:
        return
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                name TEXT PRIMARY KEY,
                short_name TEXT,
                badge_url TEXT
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id TEXT PRIMARY KEY,
                match_date DATE NOT NULL,
                match_time TEXT,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                prob_home DOUBLE PRECISION,
                prob_draw DOUBLE PRECISION,
                prob_away DOUBLE PRECISION,
                score TEXT,
                winner TEXT,
                home_goals DOUBLE PRECISION,
                away_goals DOUBLE PRECISION,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_predictions_date
            ON predictions(match_date);
        """)
        conn.commit()
    _initialized = True


def get_teams():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT name, short_name, badge_url FROM teams ORDER BY name")
        rows = cur.fetchall()
        return {row['name']: dict(row) for row in rows}


def save_teams(teams_dict):
    with get_db() as conn:
        cur = conn.cursor()
        for name, info in teams_dict.items():
            cur.execute("""
                INSERT INTO teams (name, short_name, badge_url)
                VALUES (%s, %s, %s)
                ON CONFLICT (name) DO UPDATE
                SET short_name = EXCLUDED.short_name,
                    badge_url = EXCLUDED.badge_url
            """, (name, info.get('short_name', name[:3].upper()), info.get('badge_url')))


def save_predictions(predictions):
    with get_db() as conn:
        cur = conn.cursor()
        for pred in predictions:
            p = pred.get('prediction', {})
            cur.execute("""
                INSERT INTO predictions (
                    id, match_date, match_time,
                    home_team, away_team,
                    prob_home, prob_draw, prob_away,
                    score, winner, home_goals, away_goals
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    match_time = EXCLUDED.match_time,
                    prob_home = EXCLUDED.prob_home,
                    prob_draw = EXCLUDED.prob_draw,
                    prob_away = EXCLUDED.prob_away,
                    score = EXCLUDED.score,
                    winner = EXCLUDED.winner,
                    home_goals = EXCLUDED.home_goals,
                    away_goals = EXCLUDED.away_goals
            """, (
                pred['id'],
                pred['date'],
                pred.get('time'),
                pred['home_team'],
                pred['away_team'],
                p.get('prob_home'),
                p.get('prob_draw'),
                p.get('prob_away'),
                p.get('score'),
                p.get('winner'),
                p.get('home_goals'),
                p.get('away_goals'),
            ))


def load_predictions(date_str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM predictions WHERE match_date = %s ORDER BY match_time",
            (date_str,)
        )
        rows = cur.fetchall()
        return [_row_to_prediction(r) for r in rows]


def _row_to_prediction(row):
    return {
        'id': row['id'],
        'date': row['match_date'].isoformat() if hasattr(row['match_date'], 'isoformat') else str(row['match_date']),
        'time': row.get('match_time') or 'TBD',
        'home_team': row['home_team'],
        'away_team': row['away_team'],
        'prediction': {
            'prob_home': row.get('prob_home'),
            'prob_draw': row.get('prob_draw'),
            'prob_away': row.get('prob_away'),
            'score': row.get('score'),
            'winner': row.get('winner'),
            'home_goals': row.get('home_goals'),
            'away_goals': row.get('away_goals'),
        }
    }


def get_available_dates():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT match_date FROM predictions ORDER BY match_date DESC"
        )
        rows = cur.fetchall()
        return [row['match_date'].isoformat() for row in rows]


def prediction_exists(date_str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) as cnt FROM predictions WHERE match_date = %s",
            (date_str,)
        )
        row = cur.fetchone()
        return row['cnt'] > 0
