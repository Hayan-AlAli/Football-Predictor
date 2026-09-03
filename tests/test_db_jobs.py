import pytest
from backend import database as db

needs_db = pytest.mark.skipif(db.DATABASE_URL is None, reason="POSTGRES_URL not set")

TEST_DATE = "2099-01-01"
TEST_HOME = "Testside Rovers"
TEST_AWAY = "Mock United"
TEST_RESULT_KEYS = [(TEST_DATE, TEST_HOME, TEST_AWAY)]


def _snapshot_test_rows():
    """Capture pre-existing rows for the test date so teardown restores DB exactly."""
    prior_results = list(db.load_results(TEST_DATE)) if db.DATABASE_URL else []
    prior_forecast = db.load_forecast(TEST_DATE) if db.DATABASE_URL else None
    return prior_results, prior_forecast


def _delete_test_rows():
    """Delete exactly the rows these tests wrote (by primary key), nothing else."""
    if not db.DATABASE_URL:
        return
    with db.get_db() as conn:
        cur = conn.cursor()
        for match_date, home, away in TEST_RESULT_KEYS:
            cur.execute(
                "DELETE FROM results WHERE match_date = %s AND home_team = %s AND away_team = %s",
                (match_date, home, away),
            )
        cur.execute("DELETE FROM forecast_cache WHERE match_date = %s", (TEST_DATE,))


@pytest.fixture
def clean_test_rows():
    prior_results, prior_forecast = _snapshot_test_rows()
    try:
        yield
    finally:
        _delete_test_rows()
        # Restore any pre-existing rows this date's UPSERTs may have overwritten.
        if prior_results:
            db.save_results([{"date": TEST_DATE, **r} for r in prior_results])
        if prior_forecast is not None:
            db.save_forecast(TEST_DATE, prior_forecast)


@needs_db
def test_save_and_load_results_roundtrip(clean_test_rows):
    db.init_db()
    rows = [{"date": TEST_DATE, "home_team": TEST_HOME, "away_team": TEST_AWAY,
             "home_goals": 2, "away_goals": 1}]
    db.save_results(rows)
    loaded = db.load_results(TEST_DATE)
    assert {"home_team": TEST_HOME, "away_team": TEST_AWAY,
            "home_goals": 2, "away_goals": 1} in loaded


@needs_db
def test_save_results_upsert_is_idempotent(clean_test_rows):
    rows = [{"date": TEST_DATE, "home_team": TEST_HOME, "away_team": TEST_AWAY,
             "home_goals": 2, "away_goals": 1}]
    db.save_results(rows)
    db.save_results(rows)
    loaded = db.load_results(TEST_DATE)
    matching = [r for r in loaded
                if r["home_team"] == TEST_HOME and r["away_team"] == TEST_AWAY]
    assert len(matching) == 1


@needs_db
def test_save_and_load_forecast_roundtrip(clean_test_rows):
    db.init_db()
    payload = {"generated": TEST_DATE, "entries": 1}
    db.save_forecast(TEST_DATE, payload)
    assert db.load_forecast(TEST_DATE) == payload
    assert db.load_latest_forecast()["generated"] == TEST_DATE
