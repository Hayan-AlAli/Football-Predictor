import json

from backend import teams, utils


def test_every_registered_team_is_complete():
    raw = json.load(open(teams.REGISTRY_PATH, encoding="utf-8"))
    slugs, espn_ids = set(), set()
    for name, info in raw["teams"].items():
        for key in ("slug", "full_name", "short_name", "espn_id", "pl_id", "color"):
            assert info.get(key), (name, key)
        assert len(info["short_name"]) == 3
        assert info["color"].startswith("#") and len(info["color"]) == 7
        assert info["slug"] not in slugs and info["espn_id"] not in espn_ids
        slugs.add(info["slug"])
        espn_ids.add(info["espn_id"])


def test_aliases_resolve_to_canonical_names():
    assert utils.normalize_team_name("Man Utd") == "Manchester United"
    assert utils.normalize_team_name("Wolves") == "Wolverhampton"
    assert utils.normalize_team_name("Newcastle United") == "Newcastle"
    assert utils.normalize_team_name("Leeds") == "Leeds United"
    assert utils.normalize_team_name("Brighton & Hove Albion") == "Brighton"
    assert utils.normalize_team_name("AFC Bournemouth") == "Bournemouth"
    assert utils.normalize_team_name("Hull City") == "Hull"
    # historic clubs from the Elo replay keep their old mapping
    assert utils.normalize_team_name("Stoke City") == "Stoke"
    # unknown names pass through untouched
    assert utils.normalize_team_name("Nowhere Rovers") == "Nowhere Rovers"
    assert utils.normalize_team_name(None) is None


def test_no_alias_points_at_two_clubs():
    raw = json.load(open(teams.REGISTRY_PATH, encoding="utf-8"))
    seen = {}
    for canon, info in raw["teams"].items():
        for alias in info["aliases"]:
            assert seen.setdefault(alias, canon) == canon, alias


def test_slug_and_espn_lookups():
    assert teams.slug("Wolves") == "wolverhampton-wanderers"
    assert teams.from_slug("wolverhampton-wanderers") == "Wolverhampton"
    assert teams.from_slug("Wolves") == "Wolverhampton"
    assert teams.from_espn_id(359) == "Arsenal"
    assert teams.from_espn_id("0") is None
    assert teams.slug("Nowhere Rovers") == "nowhere-rovers"


def test_info_shapes_badges_and_overrides():
    info = teams.info("Man City")
    assert info["name"] == "Manchester City"
    assert info["badge_url"] == "https://a.espncdn.com/i/teamlogos/soccer/500/382.png"
    assert info["badge_fallback_url"].endswith("/t43.png")
    assert info["short_name"] == "MCI"
    synced = teams.info("Man City", {"badge_url": "https://x/new.png", "color": "#000000"})
    assert synced["badge_url"] == "https://x/new.png"
    assert synced["color"] == info["color"]  # the curated colour wins
    assert teams.info("Man City", {"badge_url": None})["badge_url"] == info["badge_url"]
    assert teams.info("Nowhere Rovers", {"color": "#ABCDEF"})["color"] == "#ABCDEF"
    unknown = teams.info("Nowhere Rovers")
    assert unknown["badge_url"] is None and unknown["short_name"] == "NOW"
