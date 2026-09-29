"""One-time carry-over from the old day-keyed tables.

The old schema kept fixtures, predictions and results in three tables keyed
by date + team names, so a rescheduled or renamed match left a stale twin
behind. Here every row is re-keyed by season + pairing (see db.match_id), so
twins collapse onto one match: the latest-dated prediction wins, as the old
read-time dedupe did, and a result always lands on the prediction it
settles. The legacy tables are left untouched.
"""
from datetime import datetime

from sqlalchemy import func, inspect, select, text

from backend import teams as registry


def _time(date_value, time_str):
    if not time_str or time_str == 'TBD':
        return None
    try:
        hh, mm = str(time_str).split(':')[:2]
        return datetime(date_value.year, date_value.month, date_value.day, int(hh), int(mm))
    except (ValueError, TypeError):
        return None


def _rows(conn, table):
    from backend import db
    rows = [dict(r) for r in conn.execute(text(f'SELECT * FROM {table}')).mappings().all()]
    for r in rows:
        if r.get('match_date') is not None:
            r['match_date'] = db._as_date(r['match_date'])
    return rows


def upgrade_teams_table(engine):
    """Bring a pre-2.0 `teams` table up to the current columns.

    create_all never alters an existing table, and the old one (name,
    short_name, badge_url) only ever held a copy of the old teams.json - its
    50px crest URLs would otherwise override the registry's hi-res badges.
    So add the new columns and clear those rows; the next sync refills them.
    """
    if 'teams' not in inspect(engine).get_table_names():
        return False
    have = {c['name'] for c in inspect(engine).get_columns('teams')}
    missing = [c for c in ('espn_id', 'color', 'alt_color') if c not in have]
    if not missing:
        return False
    with engine.begin() as conn:
        for col in missing:
            conn.execute(text(f'ALTER TABLE teams ADD COLUMN {col} VARCHAR'))
        conn.execute(text('DELETE FROM teams'))
    return True


def migrate_if_needed(engine):
    from backend import db
    if not db.has_legacy_tables(engine):
        return None
    with engine.begin() as conn:
        if conn.execute(select(func.count()).select_from(db.matches)).scalar():
            return None
        names = set(inspect(conn).get_table_names())
        return migrate(conn, names)


def migrate(conn, legacy_tables):
    from backend import db
    norm = registry.normalize
    match_rows, pred_rows = {}, {}

    def base(date_value, home, away):
        home, away = norm(home), norm(away)
        season = db.season_of(date_value)
        mid = db.match_id(season, home, away)
        row = match_rows.setdefault(mid, {'id': mid, 'season': season, 'home_team': home,
                                          'away_team': away, 'status': 'scheduled'})
        return mid, row

    if 'predictions' in legacy_tables:
        preds = _rows(conn, 'predictions')
        # Latest date last so it wins; on a tie the canonically named row wins.
        preds.sort(key=lambda p: (p['match_date'],
                                  norm(p['home_team']) == p['home_team'] and norm(p['away_team']) == p['away_team']))
        for p in preds:
            mid, row = base(p['match_date'], p['home_team'], p['away_team'])
            row['match_date'] = p['match_date']
            row['kickoff'] = _time(p['match_date'], p.get('match_time'))
            winner = p.get('winner')
            if winner and winner != 'Draw':
                winner = norm(winner)
            pred_rows[mid] = {
                'match_id': mid, 'model_version': 'legacy-rf',
                'prob_home': p.get('prob_home'), 'prob_draw': p.get('prob_draw'),
                'prob_away': p.get('prob_away'), 'exp_home_goals': p.get('home_goals'),
                'exp_away_goals': p.get('away_goals'), 'score': p.get('score'), 'winner': winner,
                'home_elo': p.get('home_elo'), 'away_elo': p.get('away_elo'),
            }

    if 'fixtures' in legacy_tables:
        for f in _rows(conn, 'fixtures'):
            _, row = base(f['match_date'], f['home_team'], f['away_team'])
            row['match_date'] = f['match_date']
            row['kickoff'] = _time(f['match_date'], f.get('match_time'))

    if 'results' in legacy_tables:
        for r in _rows(conn, 'results'):
            if r.get('home_goals') is None or r.get('away_goals') is None:
                continue
            _, row = base(r['match_date'], r['home_team'], r['away_team'])
            if row.get('match_date') != r['match_date']:
                row['kickoff'] = None  # played on another day than predicted: time unknown
            row['match_date'] = r['match_date']
            row['status'] = 'finished'
            row['home_goals'] = int(r['home_goals'])
            row['away_goals'] = int(r['away_goals'])

    now = datetime.utcnow()
    for row in match_rows.values():
        row.setdefault('kickoff', None)
        row.setdefault('home_goals', None)
        row.setdefault('away_goals', None)
        row['updated_at'] = now
    if match_rows:
        conn.execute(db.matches.insert(), list(match_rows.values()))
    if pred_rows:
        for p in pred_rows.values():
            p['created_at'] = now
        conn.execute(db.match_predictions.insert(), list(pred_rows.values()))

    forecasts = 0
    if 'forecast_cache' in legacy_tables:
        for f in sorted(_rows(conn, 'forecast_cache'), key=lambda f: f['match_date'])[-5:]:
            payload = f['payload']
            if isinstance(payload, str):
                import json
                payload = json.loads(payload)
            conn.execute(db.forecasts.insert().values(
                season=payload.get('season_year') or db.season_of(f['match_date']),
                generated_at=datetime.combine(f['match_date'], datetime.min.time()),
                payload=payload))
            forecasts += 1

    summary = {'matches': len(match_rows), 'predictions': len(pred_rows), 'forecasts': forecasts}
    print(f"Legacy migration: {summary}")
    return summary
