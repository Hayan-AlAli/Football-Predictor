import pytest

from backend import elo, predictor


@pytest.fixture(autouse=True)
def _offline_elo(monkeypatch):
    """Seed Elo and training-only form: never read the real results DB."""
    monkeypatch.setattr(elo, "stored_results_since", lambda as_of: [])
    monkeypatch.setattr(predictor, "_form_cache", None)
    monkeypatch.setattr(elo, "_cache", None)
    monkeypatch.setattr(elo, "_cache_ts", 0.0)
