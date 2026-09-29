"""Persistence: one schema, one code path, Postgres in production and SQLite
everywhere else.

The schema is built around the match, not the day:

- ``matches``: one row per fixture, keyed by season + home + away. In a
  double round-robin each ordered pairing meets exactly once a season, so
  the key survives reschedules and feed renames - no stale twins, no fuzzy
  name matching to pair a result with its prediction. Fixtures and results
  are the same row; a result just fills in the score and the status.
- ``match_predictions``: the model's call for a match (one per match,
  refreshed until kickoff, then frozen - that frozen call is the record).
- ``teams``: badge/colour values synced from the fixtures feed, layered
  over the static registry in data/teams.json.
- ``forecasts``: season Monte Carlo payloads, newest wins.
- ``job_runs``: what each sync did and when, for /api/health.
"""
import os
from datetime import date, datetime, timezone
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import (JSON, Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer,
                        MetaData, String, Table, create_engine, inspect, select, text)
from sqlalchemy.dialects.postgresql import JSONB

from backend import teams as registry

load_dotenv()

metadata = MetaData()
_JSON = JSON().with_variant(JSONB(), 'postgresql')

teams = Table(
    'teams', metadata,
    Column('name', String, primary_key=True),
    Column('short_name', String),
    Column('badge_url', String),
    Column('espn_id', String),
    Column('color', String),
    Column('alt_color', String),
)

matches = Table(
    'matches', metadata,
    Column('id', String, primary_key=True),
    Column('season', Integer, nullable=False),
    Column('match_date', Date, nullable=False),
    Column('kickoff', DateTime),            # naive UTC; NULL when the time is unknown
    Column('home_team', String, nullable=False),
    Column('away_team', String, nullable=False),
    Column('status', String, nullable=False, default='scheduled'),
    Column('home_goals', Integer),
    Column('away_goals', Integer),
    Column('espn_id', String),
    Column('updated_at', DateTime),
    Index('ix_matches_season_date', 'season', 'match_date'),
)

match_predictions = Table(
    'match_predictions', metadata,
    Column('match_id', String, ForeignKey('matches.id', ondelete='CASCADE'), primary_key=True),
    Column('model_version', String),
    Column('created_at', DateTime),
    Column('prob_home', Float),
    Column('prob_draw', Float),
    Column('prob_away', Float),
    Column('exp_home_goals', Float),
    Column('exp_away_goals', Float),
    Column('score', String),
    Column('winner', String),
    Column('home_elo', Float),
    Column('away_elo', Float),
    Column('features', _JSON),
)

forecasts = Table(
    'forecasts', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('season', Integer, nullable=False),
    Column('generated_at', DateTime, nullable=False),
    Column('payload', _JSON, nullable=False),
)

job_runs = Table(
    'job_runs', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('job', String, nullable=False),
    Column('finished_at', DateTime, nullable=False),
    Column('ok', Boolean, nullable=False),
    Column('summary', _JSON),
)

STATUSES = ('scheduled', 'in_progress', 'finished', 'postponed')


# ---------------------------------------------------------------- connection

def database_url():
    url = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')
    if url:
        # Vercel/Heroku hand out postgres://, which SQLAlchemy 2 rejects, and
        # a bare postgresql:// means psycopg 3 to SQLAlchemy 2.1+, while we
        # ship psycopg2: name the driver unless the URL already does.
        for prefix in ('postgres://', 'postgresql://'):
            if url.startswith(prefix):
                url = 'postgresql+psycopg2://' + url[len(prefix):]
        return url
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    if not os.access(data_dir, os.W_OK):
        data_dir = '/tmp'  # read-only deploy without Postgres: ephemeral scratch DB
    return f"sqlite:///{os.path.abspath(os.path.join(data_dir, 'football.db'))}"


def is_postgres():
    return engine().dialect.name == 'postgresql'


@lru_cache(maxsize=1)
def engine():
    """One pooled engine per process.

    Serverless functions stay warm between requests, so a small pool with
    pre-ping reuses connections instead of opening one per query.
    """
    url = database_url()
    if url.startswith('sqlite'):
        return create_engine(url, connect_args={'check_same_thread': False})
    return create_engine(url, pool_size=2, max_overflow=3, pool_pre_ping=True, pool_recycle=300)


_ready = False


def init():
    """Create tables (idempotent) and carry legacy rows over once."""
    global _ready
    if _ready:
        return
    metadata.create_all(engine())
    from backend import legacy_migration
    legacy_migration.upgrade_teams_table(engine())
    legacy_migration.migrate_if_needed(engine())
    _ready = True


def reset_for_tests(url):
    """Point the module at a fresh database (tests only)."""
    global _ready
    os.environ['DATABASE_URL'] = url
    os.environ.pop('POSTGRES_URL', None)
    engine.cache_clear()
    _ready = False
    init()


def _connect():
    init()
    return engine().begin()


def _upsert(conn, table, rows, keys):
    """Insert-or-update rows; only the columns a row carries are updated."""
    if not rows:
        return
    if conn.dialect.name == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    by_shape = {}
    for row in rows:
        by_shape.setdefault(tuple(sorted(row)), []).append(row)
    for shape, group in by_shape.items():
        stmt = insert(table).values(group)
        update = {c: stmt.excluded[c] for c in shape if c not in keys}
        stmt = (stmt.on_conflict_do_update(index_elements=keys, set_=update)
                if update else stmt.on_conflict_do_nothing(index_elements=keys))
        conn.execute(stmt)


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------- identity

def season_of(d):
    """Season start year: August onwards belongs to the new season."""
    if isinstance(d, str):
        d = date.fromisoformat(d[:10])
    return d.year if d.month >= 8 else d.year - 1


def match_id(season, home_team, away_team):
    return f"{season}-{registry.slug(home_team)}-{registry.slug(away_team)}"


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _as_naive_utc(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if hasattr(value, 'to_pydatetime'):
        value = value.to_pydatetime()
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


# ---------------------------------------------------------------- teams

def upsert_teams(rows):
    """rows: [{name, short_name?, badge_url?, espn_id?, color?, alt_color?}]"""
    with _connect() as conn:
        _upsert(conn, teams, [{k: v for k, v in r.items() if v is not None} for r in rows], ['name'])


@lru_cache(maxsize=1)
def _team_overrides_cached(_bucket):
    with _connect() as conn:
        rows = conn.execute(select(teams)).mappings().all()
    return {r['name']: {'badge_url': r['badge_url'], 'color': r['color']} for r in rows}


def team_overrides():
    """{name: {badge_url, color}} synced from the feed (cached ~10 min)."""
    import time
    try:
        return _team_overrides_cached(int(time.time() // 600))
    except Exception:
        return {}


def team_info(name):
    canon = registry.normalize(name)
    return registry.info(canon, team_overrides().get(canon))


# ---------------------------------------------------------------- matches

def upsert_matches(rows):
    """rows: [{home_team, away_team, match_date, ...}] - id and season are
    derived when missing. Only the columns present are written, so a
    results-only row never erases a kickoff time and vice versa."""
    out = []
    now = _now()
    for r in rows:
        row = dict(r)
        row['home_team'] = registry.normalize(row['home_team'])
        row['away_team'] = registry.normalize(row['away_team'])
        row['match_date'] = _as_date(row['match_date'])
        if 'kickoff' in row:
            row['kickoff'] = _as_naive_utc(row['kickoff'])
        row.setdefault('season', season_of(row['match_date']))
        row.setdefault('id', match_id(row['season'], row['home_team'], row['away_team']))
        row['updated_at'] = now
        out.append(row)
    with _connect() as conn:
        _upsert(conn, matches, out, ['id'])
    return [r['id'] for r in out]


def _match_row(r):
    kickoff = r['kickoff']
    out = {
        'id': r['id'],
        'season': r['season'],
        'date': r['match_date'].isoformat(),
        'time': kickoff.strftime('%H:%M') if kickoff else None,
        'kickoff': kickoff.isoformat() + 'Z' if kickoff else None,
        'home_team': r['home_team'],
        'away_team': r['away_team'],
        'status': r['status'],
        'home_goals': r['home_goals'],
        'away_goals': r['away_goals'],
        'prediction': None,
    }
    if r.get('prob_home') is not None:
        out['prediction'] = {
            'prob_home': r['prob_home'],
            'prob_draw': r['prob_draw'],
            'prob_away': r['prob_away'],
            'home_goals': r['exp_home_goals'],
            'away_goals': r['exp_away_goals'],
            'score': r['score'],
            'winner': r['winner'],
            'home_elo': r['home_elo'],
            'away_elo': r['away_elo'],
            'features': r['features'],
            'model_version': r['model_version'],
            'created_at': r['created_at'].isoformat() + 'Z' if r['created_at'] else None,
        }
    return out


def load_matches(season=None, team=None, since=None, status=None, with_predictions=True):
    """Matches (oldest first) joined to their prediction when one exists."""
    p = match_predictions
    cols = [matches]
    if with_predictions:
        cols += [p.c.model_version, p.c.created_at, p.c.prob_home, p.c.prob_draw, p.c.prob_away,
                 p.c.exp_home_goals, p.c.exp_away_goals, p.c.score, p.c.winner,
                 p.c.home_elo, p.c.away_elo, p.c.features]
        q = select(*cols).select_from(matches.outerjoin(p, p.c.match_id == matches.c.id))
    else:
        q = select(matches)
    if season is not None:
        q = q.where(matches.c.season == season)
    if team is not None:
        canon = registry.normalize(team)
        q = q.where((matches.c.home_team == canon) | (matches.c.away_team == canon))
    if since is not None:
        q = q.where(matches.c.match_date >= _as_date(since))
    if status is not None:
        statuses = [status] if isinstance(status, str) else list(status)
        q = q.where(matches.c.status.in_(statuses))
    q = q.order_by(matches.c.match_date, matches.c.kickoff, matches.c.id)
    with _connect() as conn:
        rows = conn.execute(q).mappings().all()
    return [_match_row(dict(r)) if with_predictions else _match_row({**r, 'prob_home': None})
            for r in rows]


def results_since(since):
    """Finished matches strictly after `since` (YYYY-MM-DD), oldest first,
    in the flat shape the Elo and form code consume."""
    q = (select(matches.c.match_date, matches.c.home_team, matches.c.away_team,
                matches.c.home_goals, matches.c.away_goals, matches.c.season)
         .where(matches.c.status == 'finished')
         .where(matches.c.match_date > _as_date(since))
         .order_by(matches.c.match_date, matches.c.kickoff))
    with _connect() as conn:
        rows = conn.execute(q).mappings().all()
    return [{'date': r['match_date'].isoformat(), 'home_team': r['home_team'],
             'away_team': r['away_team'], 'home_goals': r['home_goals'],
             'away_goals': r['away_goals'], 'season': r['season']} for r in rows]


def latest_season():
    with _connect() as conn:
        return conn.execute(select(matches.c.season).order_by(matches.c.season.desc()).limit(1)).scalar()


def delete_scheduled_except(season, keep_ids):
    """Drop unplayed fixtures of a season the feed no longer lists (e.g. a
    fixture ESPN removed). Finished matches are never touched."""
    keep = set(keep_ids)
    with _connect() as conn:
        ids = conn.execute(select(matches.c.id).where(matches.c.season == season)
                           .where(matches.c.status != 'finished')).scalars().all()
        stale = [i for i in ids if i not in keep]
        if stale:
            conn.execute(match_predictions.delete().where(match_predictions.c.match_id.in_(stale)))
            conn.execute(matches.delete().where(matches.c.id.in_(stale)))
    return len(stale)


# ---------------------------------------------------------------- predictions

def upsert_predictions(rows):
    """rows: [{match_id, prob_home, prob_draw, prob_away, exp_home_goals,
    exp_away_goals, score, winner, home_elo, away_elo, features, model_version}]"""
    now = _now()
    with _connect() as conn:
        _upsert(conn, match_predictions, [{**r, 'created_at': now} for r in rows], ['match_id'])


# ---------------------------------------------------------------- forecasts

def save_forecast(season, payload):
    with _connect() as conn:
        conn.execute(forecasts.insert().values(season=season, generated_at=_now(), payload=payload))
        # Keep a short history; the page only ever reads the newest.
        old = conn.execute(select(forecasts.c.id).order_by(forecasts.c.id.desc()).offset(20)).scalars().all()
        if old:
            conn.execute(forecasts.delete().where(forecasts.c.id.in_(old)))


def latest_forecast():
    with _connect() as conn:
        row = conn.execute(select(forecasts.c.payload, forecasts.c.generated_at)
                           .order_by(forecasts.c.id.desc()).limit(1)).first()
    return dict(row.payload) if row else None


# ---------------------------------------------------------------- job log

def log_run(job, ok, summary):
    with _connect() as conn:
        conn.execute(job_runs.insert().values(job=job, finished_at=_now(), ok=ok, summary=summary))


def last_runs():
    """Most recent run per job: {job: {finished_at, ok}}."""
    with _connect() as conn:
        rows = conn.execute(select(job_runs.c.job, job_runs.c.finished_at, job_runs.c.ok)
                            .order_by(job_runs.c.id.desc()).limit(50)).mappings().all()
    out = {}
    for r in rows:
        out.setdefault(r['job'], {'finished_at': r['finished_at'].isoformat() + 'Z', 'ok': r['ok']})
    return out


def ping():
    with engine().connect() as conn:
        conn.execute(text('SELECT 1'))
    return True


def has_legacy_tables(bind):
    names = set(inspect(bind).get_table_names())
    return 'predictions' in names or 'results' in names or 'fixtures' in names
