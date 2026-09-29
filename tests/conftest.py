import os

import pytest
from sqlalchemy import create_engine, text

from backend import db, elo, predictor

# Set TEST_DATABASE_URL to a throwaway Postgres to run the suite against the
# production dialect; its public schema is wiped before every test.
PG_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    """Every test gets its own empty database - never a real one."""
    if PG_URL:
        monkeypatch.setenv("DATABASE_URL", PG_URL)
        wipe = create_engine(db.database_url())
        with wipe.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
        wipe.dispose()
        db.reset_for_tests(PG_URL)
    else:
        db.reset_for_tests(f"sqlite:///{tmp_path / 'test.db'}")
    db._team_overrides_cached.cache_clear()
    yield
    db.engine().dispose()


@pytest.fixture(autouse=True)
def _offline_elo(monkeypatch):
    """Seed Elo and training-only form: never read stored results."""
    monkeypatch.setattr(elo, "stored_results_since", lambda as_of: [])
    monkeypatch.setattr(predictor, "_form_cache", None)
    monkeypatch.setattr(elo, "_cache", None)
    monkeypatch.setattr(elo, "_cache_ts", 0.0)


def match(home, away, date, status="scheduled", score=None, prediction=None, season=None):
    """A match row shaped like db.load_matches output."""
    return {
        "id": db.match_id(season or db.season_of(date), home, away),
        "season": season or db.season_of(date), "date": date, "time": "15:00",
        "kickoff": f"{date}T15:00:00Z", "home_team": home, "away_team": away,
        "status": status,
        "home_goals": score[0] if score else None, "away_goals": score[1] if score else None,
        "prediction": prediction,
    }
