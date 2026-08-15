import os

from backend import insights


def test_write_forecast_file_writes_cache(tmp_path):
    payload = {
        "generated": "2026-08-15", "season_year": 2026, "n_sims": 10000,
        "season_complete": False, "standings": [], "projected": [],
        "fixtures_remaining": 380,
    }
    out_dir = str(tmp_path / "forecast")
    path = insights.write_forecast_file(forecast=payload, out_dir=out_dir)
    assert path is not None
    assert os.path.exists(path)