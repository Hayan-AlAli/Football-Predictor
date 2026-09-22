import pytest
from backend import database as db

needs_db = pytest.mark.skipif(db.DATABASE_URL is None, reason="POSTGRES_URL not set")

TEST_DATE = "2099-06-01"
FIX_A = {"id": f"{TEST_DATE}_testside-rovers_mock-united", "date": TEST_DATE,
         "time": "15:00", "home_team": "Testside Rovers", "away_team": "Mock United",
         "gameweek": 99, "home_elo": 1600.0, "away_elo": 1500.0}
FIX_B = {"id": f"{TEST_DATE}_mock-united_testside-rovers", "date": TEST_DATE,
         "time": "17:30", "home_team": "Mock United", "away_team": "Testside Rovers",
         "gameweek": 99, "home_elo": 1500.0, "away_elo": 1600.0}


@pytest.fixture
def clean_fixture_rows():
    try:
        yield
    finally:
        if db.DATABASE_URL:
            with db.get_db() as conn:
                cur = conn.cursor()
                for f in (FIX_A, FIX_B):
                    cur.execute("DELETE FROM fixtures WHERE id = %s", (f["id"],))


@needs_db
def test_save_and_load_fixtures_roundtrip(clean_fixture_rows):
    db.init_db()
    db.save_fixtures([FIX_A, FIX_B])
    loaded = db.load_fixtures(TEST_DATE)
    assert [r["id"] for r in loaded] == [FIX_A["id"], FIX_B["id"]]
    assert loaded[0]["home_team"] == "Testside Rovers"
    assert loaded[0]["gameweek"] == 99


@needs_db
def test_save_fixtures_upsert_updates_kickoff(clean_fixture_rows):
    db.init_db()
    db.save_fixtures([FIX_A])
    moved = dict(FIX_A, time="18:00")
    db.save_fixtures([moved])
    loaded = db.load_fixtures(TEST_DATE)
    assert len(loaded) == 1
    assert loaded[0]["time"] == "18:00"


@needs_db
def test_load_fixtures_filters_by_team(clean_fixture_rows):
    db.init_db()
    db.save_fixtures([FIX_A, FIX_B])
    only_home = db.load_fixtures(TEST_DATE, team="Mock United")
    assert {r["id"] for r in only_home} == {FIX_A["id"], FIX_B["id"]}
    assert db.load_fixtures(TEST_DATE, team="No Such Club") == []
    assert db.load_fixtures("2099-06-02") == []


@needs_db
def test_prune_fixtures_removes_stale_rows(clean_fixture_rows):
    db.init_db()
    db.save_fixtures([FIX_A, FIX_B])
    ghost = dict(FIX_A, id=f"{TEST_DATE}_ghost_home_ghost-away",
                 home_team="Ghost Home", away_team="Ghost Away")
    db.save_fixtures([ghost])
    try:
        db.prune_fixtures([FIX_A["id"], FIX_B["id"]], TEST_DATE)
        remaining = {r["id"] for r in db.load_fixtures(TEST_DATE)}
        assert remaining == {FIX_A["id"], FIX_B["id"]}
    finally:
        if db.DATABASE_URL:
            with db.get_db() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM fixtures WHERE id = %s", (ghost["id"],))
