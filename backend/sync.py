"""The one scheduled job: bring the database in line with the real world.

Each run pulls the whole current season from ESPN (fixtures, kickoffs,
statuses, scores and club metadata in one pass), upserts it, predicts the
matches coming up, and refreshes the season forecast when it is due. It is
idempotent, so the cron can run it as often as it likes; missed runs simply
catch up on the next one. It replaces the old morning (fixtures and
predictions) and evening (results) jobs.
"""
import argparse
import logging
from datetime import datetime, timedelta, timezone

from backend import db, elo, insights, predictor
from backend.sources import espn, football_data

logger = logging.getLogger(__name__)

# How far ahead to predict. Form and ratings move every week, so a call made
# months out says little; the forecast simulates the rest of the season anyway.
PREDICTION_HORIZON_DAYS = 28


def current_season(now=None):
    now = now or datetime.now(timezone.utc)
    return db.season_of(now.date())


def forecast_due(has_forecast, results_changed, weekday=None):
    """Mondays, whenever results came in, or when nothing is stored yet."""
    if weekday is None:
        weekday = datetime.now(timezone.utc).weekday()
    return not has_forecast or results_changed or weekday == 0


def _invalidate_caches():
    elo._cache = None
    predictor._form_cache = None


def pull_matches(season):
    """(match rows, team rows, complete, source). ESPN first; when it is down,
    football-data.co.uk still gives results (but no fixtures)."""
    try:
        rows, team_rows, complete = espn.fetch_season(season)
        return rows, team_rows, complete, 'espn'
    except espn.FeedError as e:
        logger.warning(f"{e}; falling back to football-data.co.uk results")
    rows = [{**r, 'status': 'finished'} for r in football_data.season_results(season)]
    return rows, [], False, 'football-data'


def _prediction_row(match, pred, version_suffix=''):
    return {
        'match_id': match['id'],
        'model_version': (pred.get('model_version') or '') + version_suffix,
        'prob_home': float(pred['prob_home']),
        'prob_draw': float(pred['prob_draw']),
        'prob_away': float(pred['prob_away']),
        'exp_home_goals': float(pred['home_goals']),
        'exp_away_goals': float(pred['away_goals']),
        'score': pred.get('score'),
        'winner': pred.get('winner'),
        'home_elo': float(pred['home_elo']) if pred.get('home_elo') is not None else None,
        'away_elo': float(pred['away_elo']) if pred.get('away_elo') is not None else None,
        'features': pred.get('features'),
    }


def predict_upcoming(season, now=None):
    """(Re)predict every unplayed match kicking off within the horizon.

    Matches already under way or played keep the call they had at kickoff:
    that frozen call is what the record judges.
    """
    now = (now or datetime.now(timezone.utc)).replace(tzinfo=None)
    horizon = now + timedelta(days=PREDICTION_HORIZON_DAYS)
    ratings = elo.current_ratings()
    due, inputs = [], []
    for m in db.load_matches(season=season, since=now.date(), status='scheduled', with_predictions=False):
        kickoff = datetime.fromisoformat(m['kickoff'][:-1]) if m['kickoff'] else \
            datetime.fromisoformat(m['date'] + 'T23:59')
        if kickoff <= now or kickoff > horizon:
            continue
        due.append(m)
        inputs.append({
            'home_team': m['home_team'],
            'away_team': m['away_team'],
            'date': kickoff,
            'home_elo': elo.rating(m['home_team'], ratings),
            'away_elo': elo.rating(m['away_team'], ratings),
        })
    rows = [_prediction_row(m, pred) for m, pred in zip(due, predictor.predict_matches(inputs))]
    db.upsert_predictions(rows)
    return len(rows)


# Tag for calls rebuilt after kickoff (see repair_placeholder_calls).
REBUILT_SUFFIX = '+rebuilt'


def is_placeholder(pred):
    """A stored call that says nothing: missing odds or the flat ~33/34/33
    guess an old feature bug produced (fixed 24 Sep 2026). No real call is
    that flat: home advantage alone moves it further."""
    probs = [pred.get('prob_home'), pred.get('prob_draw'), pred.get('prob_away')]
    return any(p is None for p in probs) or max(probs) - min(probs) < 0.02


def repair_placeholder_calls(season):
    """Replace placeholder calls on matches that have kicked off.

    Those calls are frozen, so predict_upcoming never touches them again.
    The rebuilt call only sees what was known before the match day: Elo as
    it stood then and form from earlier matches. It is tagged
    REBUILT_SUFFIX so the record can tell it was made after the fact.
    """
    broken = [m for m in db.load_matches(season=season, status=('finished', 'in_progress'))
              if m['prediction'] and is_placeholder(m['prediction'])]
    if not broken:
        return 0
    first_day = datetime.fromisoformat(min(m['date'] for m in broken)).date()
    results = db.results_since(first_day - timedelta(days=1))
    ratings_on = {}
    inputs = []
    for m in broken:
        if m['date'] not in ratings_on:
            ratings_on[m['date']] = elo.ratings_before(m['date'], results)
        ratings = ratings_on[m['date']]
        inputs.append({
            'home_team': m['home_team'],
            'away_team': m['away_team'],
            # Midnight of match day: form excludes the match itself.
            'date': datetime.fromisoformat(m['date']),
            'home_elo': elo.rating(m['home_team'], ratings),
            'away_elo': elo.rating(m['away_team'], ratings),
        })
    rows = [_prediction_row(m, pred, REBUILT_SUFFIX)
            for m, pred in zip(broken, predictor.predict_matches(inputs))]
    db.upsert_predictions(rows)
    logger.info(f"rebuilt {len(rows)} placeholder calls")
    return len(rows)


def run_sync(force_forecast=False, now=None):
    season = current_season(now)
    started = datetime.now(timezone.utc)
    summary = {'season': season}
    try:
        before = {m['id']: m['status'] for m in db.load_matches(season=season, with_predictions=False)}
        rows, team_rows, complete, source = pull_matches(season)
        summary['source'] = source
        if team_rows:
            db.upsert_teams(team_rows)
        ids = db.upsert_matches(rows)
        summary['matches'] = len(ids)
        summary['removed'] = db.delete_scheduled_except(season, ids) if complete else 0
        newly_finished = sum(1 for r, i in zip(rows, ids)
                             if r.get('status') == 'finished' and before.get(i) != 'finished')
        summary['new_results'] = newly_finished
        _invalidate_caches()

        summary['predictions'] = predict_upcoming(season, now)
        try:
            summary['repaired'] = repair_placeholder_calls(season)
        except Exception as e:  # never let a repair block fresh calls or the forecast
            logger.exception('placeholder repair failed')
            summary['repaired'] = f'failed: {e}'

        forecast_status = 'reused'
        try:
            if force_forecast or forecast_due(db.latest_forecast() is not None, newly_finished > 0):
                forecast = insights.generate_forecast(db.load_matches(season=season, with_predictions=False))
                if forecast:
                    db.save_forecast(season, forecast)
                    forecast_status = 'regenerated'
                else:
                    forecast_status = 'unavailable'
        except Exception as e:  # the fixtures and predictions above are already saved
            logger.exception('forecast step failed')
            forecast_status = f'failed: {e}'
        summary['forecast'] = forecast_status
        summary['seconds'] = round((datetime.now(timezone.utc) - started).total_seconds(), 1)
        db.log_run('sync', True, summary)
        return summary
    except Exception as e:
        summary['error'] = str(e)
        try:
            db.log_run('sync', False, summary)
        finally:
            raise


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='Sync fixtures, results, predictions and forecast')
    parser.add_argument('--forecast', action='store_true', help='rebuild the season forecast now')
    print(run_sync(force_forecast=parser.parse_args().forecast))
