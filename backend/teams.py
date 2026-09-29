"""The team registry: one canonical name per club, and everything about it.

data/teams.json is the single source for team identity. Each club has a
canonical name (the key every table, model and rating uses), a URL slug,
the spellings other feeds use for it, its ESPN id (so ESPN fixtures resolve
by id instead of by name) and its colour. Badges come from ESPN's logo CDN
at 500px, with the Premier League's own crest kept as a fallback.

Names nobody has registered pass through unchanged, so an unexpected club
never crashes the pipeline: it just has no badge until it is added.
"""
import json
import os
import re
from functools import lru_cache

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'teams.json')

ESPN_BADGE_URL = "https://a.espncdn.com/i/teamlogos/soccer/500/{id}.png"
PL_BADGE_URL = "https://resources.premierleague.com/premierleague/badges/100/t{id}.png"


@lru_cache(maxsize=1)
def _registry():
    with open(REGISTRY_PATH, encoding='utf-8') as f:
        raw = json.load(f)
    teams = raw.get('teams', {})
    alias_index = {}
    for canon, info in teams.items():
        alias_index[canon] = canon
        for alias in info.get('aliases', []):
            alias_index[alias] = canon
    for canon, aliases in raw.get('aliases_only', {}).items():
        for alias in aliases:
            alias_index[alias] = canon
    by_espn = {str(info['espn_id']): canon for canon, info in teams.items() if info.get('espn_id')}
    by_slug = {info['slug']: canon for canon, info in teams.items() if info.get('slug')}
    return teams, alias_index, by_espn, by_slug


def normalize(name):
    """Canonical name for any known spelling; unknown names unchanged."""
    if name is None:
        return name
    _, alias_index, _, _ = _registry()
    return alias_index.get(name, alias_index.get(str(name).strip(), name))


def from_espn_id(espn_id):
    """Canonical name for an ESPN team id, or None if unregistered."""
    return _registry()[2].get(str(espn_id))


def slugify(name):
    return re.sub(r'[^a-z0-9]+', '-', str(name).lower()).strip('-')


def slug(name):
    info = _registry()[0].get(normalize(name))
    return info['slug'] if info else slugify(name)


def from_slug(value):
    """Canonical name for a slug, canonical name or alias (URLs accept all)."""
    by_slug = _registry()[3]
    if value in by_slug:
        return by_slug[value]
    return normalize(value)


def registered():
    return list(_registry()[0])


def info(name, overrides=None):
    """The public description of a team, as every API response prints it.

    overrides: values synced from the fixtures feed. A fresher badge URL
    wins; a colour only fills a gap, since the registry's palette is curated
    and feed colours are often a kit's secondary shade.
    """
    canon = normalize(name)
    reg = _registry()[0].get(canon, {})
    espn_id = reg.get('espn_id')
    out = {
        'name': canon,
        'slug': reg.get('slug') or slugify(canon),
        'full_name': reg.get('full_name', canon),
        'short_name': reg.get('short_name') or canon[:3].upper(),
        'badge_url': ESPN_BADGE_URL.format(id=espn_id) if espn_id else None,
        'badge_fallback_url': PL_BADGE_URL.format(id=reg['pl_id']) if reg.get('pl_id') else None,
        'color': reg.get('color'),
    }
    for key, value in (overrides or {}).items():
        if not value or key not in out or (key == 'color' and out['color']):
            continue
        out[key] = value
    return out
