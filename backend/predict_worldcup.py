import math
import random
import json
import os
import sys
import io
from datetime import datetime, date
from collections import defaultdict

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
except AttributeError:
    pass

FIFA_RANKINGS = {
    "Argentina": (1, 1877.27), "Spain": (2, 1874.71), "France": (3, 1870.70),
    "England": (4, 1828.02), "Portugal": (5, 1767.85), "Brazil": (6, 1765.86),
    "Morocco": (7, 1755.10), "Netherlands": (8, 1753.57), "Belgium": (9, 1742.24),
    "Germany": (10, 1735.77), "Croatia": (11, 1714.87), "Colombia": (13, 1698.35),
    "Mexico": (14, 1687.48), "Senegal": (15, 1684.07), "Uruguay": (16, 1673.07),
    "United States": (17, 1671.23), "Japan": (18, 1661.58), "Switzerland": (19, 1650.06),
    "Iran": (20, 1619.58), "Ecuador": (22, 1600.00), "Turkiye": (24, 1585.00),
    "Australia": (25, 1580.00), "South Korea": (26, 1575.00), "Egypt": (28, 1560.00),
    "Algeria": (30, 1545.00), "Norway": (32, 1530.00), "Austria": (33, 1525.00),
    "Paraguay": (35, 1510.00), "Ivory Coast": (36, 1505.00), "Sweden": (37, 1500.00),
    "Czechia": (38, 1495.00), "Tunisia": (39, 1490.00), "Scotland": (40, 1485.00),
    "Uzbekistan": (42, 1470.00), "Qatar": (43, 1465.00), "Saudi Arabia": (45, 1455.00),
    "Ghana": (47, 1445.00), "Bosnia and Herzegovina": (48, 1440.00), "Iraq": (50, 1430.00),
    "Jordan": (52, 1420.00), "Panama": (53, 1415.00), "South Africa": (55, 1405.00),
    "DR Congo": (56, 1400.00), "Cape Verde": (60, 1380.00), "Bolivia": (65, 1355.00),
    "Curacao": (82, 1280.00), "Haiti": (83, 1275.00), "New Zealand": (85, 1265.00),
}

SQUAD_STRENGTH = {
    "Argentina": 95, "Spain": 94, "France": 96, "England": 93, "Portugal": 92,
    "Brazil": 91, "Morocco": 82, "Netherlands": 88, "Belgium": 85, "Germany": 90,
    "Croatia": 84, "Colombia": 81, "Mexico": 76, "Senegal": 78, "Uruguay": 83,
    "United States": 77, "Japan": 80, "Switzerland": 79, "Iran": 72, "Ecuador": 75,
    "Turkiye": 78, "Australia": 73, "South Korea": 76, "Egypt": 74, "Algeria": 73,
    "Norway": 77, "Austria": 76, "Paraguay": 70, "Ivory Coast": 75, "Sweden": 76,
    "Czechia": 74, "Tunisia": 70, "Scotland": 72, "Uzbekistan": 62, "Qatar": 65,
    "Saudi Arabia": 68, "Ghana": 72, "Bosnia and Herzegovina": 73, "Iraq": 64,
    "Jordan": 60, "Panama": 63, "South Africa": 66, "DR Congo": 68,
    "Cape Verde": 58, "Bolivia": 55, "Curacao": 48, "Haiti": 45, "New Zealand": 52,
}

MANAGER_STATS = {
    "Argentina": {"name": "Lionel Scaloni", "score": 97, "major_trophies": 3},
    "Spain": {"name": "Luis de la Fuente", "score": 93, "major_trophies": 2},
    "France": {"name": "Didier Deschamps", "score": 96, "major_trophies": 2},
    "England": {"name": "Thomas Tuchel", "score": 88, "major_trophies": 1},
    "Portugal": {"name": "Roberto Martinez", "score": 82, "major_trophies": 1},
    "Brazil": {"name": "Carlo Ancelotti", "score": 96, "major_trophies": 5},
    "Morocco": {"name": "Walid Regragui", "score": 80, "major_trophies": 0},
    "Netherlands": {"name": "Ronald Koeman", "score": 78, "major_trophies": 0},
    "Belgium": {"name": "Rudi Garcia", "score": 68, "major_trophies": 1},
    "Germany": {"name": "Julian Nagelsmann", "score": 80, "major_trophies": 0},
    "Croatia": {"name": "Zlatko Dalic", "score": 88, "major_trophies": 0},
    "Colombia": {"name": "Nestor Lorenzo", "score": 72, "major_trophies": 0},
    "Mexico": {"name": "Javier Aguirre", "score": 75, "major_trophies": 0},
    "Senegal": {"name": "Aliou Cisse", "score": 76, "major_trophies": 1},
    "Uruguay": {"name": "Marcelo Bielsa", "score": 85, "major_trophies": 0},
    "United States": {"name": "Mauricio Pochettino", "score": 82, "major_trophies": 0},
    "Japan": {"name": "Hajime Moriyasu", "score": 75, "major_trophies": 0},
    "Switzerland": {"name": "Murat Yakin", "score": 74, "major_trophies": 0},
    "Iran": {"name": "Amir Ghalenoei", "score": 68, "major_trophies": 0},
    "Ecuador": {"name": "Sebastian Beccacece", "score": 65, "major_trophies": 0},
    "Turkiye": {"name": "Vincenzo Montella", "score": 70, "major_trophies": 0},
    "Australia": {"name": "Tony Popovic", "score": 60, "major_trophies": 0},
    "South Korea": {"name": "Hong Myung-bo", "score": 72, "major_trophies": 0},
    "Egypt": {"name": "Hossam Hassan", "score": 62, "major_trophies": 0},
    "Algeria": {"name": "Vladimir Petkovic", "score": 70, "major_trophies": 0},
    "Norway": {"name": "Stale Solbakken", "score": 62, "major_trophies": 0},
    "Austria": {"name": "Ralf Rangnick", "score": 72, "major_trophies": 0},
    "Paraguay": {"name": "Alfaro", "score": 58, "major_trophies": 0},
    "Ivory Coast": {"name": "Emerse Fae", "score": 68, "major_trophies": 1},
    "Sweden": {"name": "Jon Dahl Tomasson", "score": 62, "major_trophies": 0},
    "Czechia": {"name": "Ivan Hasek", "score": 60, "major_trophies": 0},
    "Tunisia": {"name": "Faouzi Benzarti", "score": 65, "major_trophies": 0},
    "Scotland": {"name": "Steve Clarke", "score": 64, "major_trophies": 0},
    "Uzbekistan": {"name": "Srecko Katanec", "score": 55, "major_trophies": 0},
    "Qatar": {"name": "Luis Garcia", "score": 60, "major_trophies": 0},
    "Saudi Arabia": {"name": "Georgios Donis", "score": 55, "major_trophies": 0},
    "Ghana": {"name": "Carlos Queiroz", "score": 74, "major_trophies": 0},
    "Bosnia and Herzegovina": {"name": "Sergej Barbarez", "score": 55, "major_trophies": 0},
    "Iraq": {"name": "Jesus Casas", "score": 55, "major_trophies": 0},
    "Jordan": {"name": "Hussein Ammouta", "score": 52, "major_trophies": 0},
    "Panama": {"name": "Thomas Christiansen", "score": 58, "major_trophies": 0},
    "South Africa": {"name": "Hugo Broos", "score": 65, "major_trophies": 0},
    "DR Congo": {"name": "Sebastien Desabre", "score": 58, "major_trophies": 0},
    "Cape Verde": {"name": "Bubista", "score": 52, "major_trophies": 0},
    "Bolivia": {"name": "Oscar Villegas", "score": 45, "major_trophies": 0},
    "Curacao": {"name": "Dick Advocaat", "score": 72, "major_trophies": 0},
    "Haiti": {"name": "Marc Collat", "score": 40, "major_trophies": 0},
    "New Zealand": {"name": "Darren Bazeley", "score": 48, "major_trophies": 0},
}

RECENT_FORM = {
    "Argentina": {"w": 8, "d": 1, "l": 1, "gf": 22, "ga": 6},
    "Spain": {"w": 8, "d": 2, "l": 0, "gf": 20, "ga": 4},
    "France": {"w": 7, "d": 2, "l": 1, "gf": 21, "ga": 8},
    "England": {"w": 7, "d": 1, "l": 2, "gf": 18, "ga": 7},
    "Portugal": {"w": 7, "d": 2, "l": 1, "gf": 19, "ga": 5},
    "Brazil": {"w": 6, "d": 2, "l": 2, "gf": 16, "ga": 8},
    "Morocco": {"w": 6, "d": 3, "l": 1, "gf": 14, "ga": 5},
    "Netherlands": {"w": 6, "d": 2, "l": 2, "gf": 17, "ga": 9},
    "Belgium": {"w": 5, "d": 3, "l": 2, "gf": 15, "ga": 10},
    "Germany": {"w": 7, "d": 1, "l": 2, "gf": 24, "ga": 10},
    "Croatia": {"w": 5, "d": 3, "l": 2, "gf": 14, "ga": 8},
    "Colombia": {"w": 6, "d": 2, "l": 2, "gf": 15, "ga": 7},
    "Mexico": {"w": 6, "d": 2, "l": 2, "gf": 14, "ga": 8},
    "Senegal": {"w": 6, "d": 2, "l": 2, "gf": 13, "ga": 6},
    "Uruguay": {"w": 5, "d": 3, "l": 2, "gf": 14, "ga": 8},
    "United States": {"w": 6, "d": 1, "l": 3, "gf": 16, "ga": 9},
    "Japan": {"w": 7, "d": 1, "l": 2, "gf": 18, "ga": 7},
    "Switzerland": {"w": 5, "d": 3, "l": 2, "gf": 12, "ga": 7},
    "Iran": {"w": 5, "d": 2, "l": 3, "gf": 13, "ga": 9},
    "Ecuador": {"w": 5, "d": 2, "l": 3, "gf": 12, "ga": 9},
    "Turkiye": {"w": 5, "d": 2, "l": 3, "gf": 14, "ga": 10},
    "Australia": {"w": 5, "d": 2, "l": 3, "gf": 14, "ga": 10},
    "South Korea": {"w": 5, "d": 3, "l": 2, "gf": 14, "ga": 7},
    "Egypt": {"w": 5, "d": 3, "l": 2, "gf": 11, "ga": 6},
    "Algeria": {"w": 5, "d": 2, "l": 3, "gf": 12, "ga": 8},
    "Norway": {"w": 5, "d": 2, "l": 3, "gf": 15, "ga": 10},
    "Austria": {"w": 5, "d": 2, "l": 3, "gf": 14, "ga": 9},
    "Paraguay": {"w": 4, "d": 3, "l": 3, "gf": 10, "ga": 9},
    "Ivory Coast": {"w": 5, "d": 2, "l": 3, "gf": 12, "ga": 8},
    "Sweden": {"w": 5, "d": 2, "l": 3, "gf": 14, "ga": 9},
    "Czechia": {"w": 4, "d": 3, "l": 3, "gf": 11, "ga": 10},
    "Tunisia": {"w": 4, "d": 3, "l": 3, "gf": 9, "ga": 7},
    "Scotland": {"w": 4, "d": 2, "l": 4, "gf": 10, "ga": 11},
    "Uzbekistan": {"w": 5, "d": 2, "l": 3, "gf": 13, "ga": 9},
    "Qatar": {"w": 4, "d": 2, "l": 4, "gf": 10, "ga": 12},
    "Saudi Arabia": {"w": 4, "d": 3, "l": 3, "gf": 10, "ga": 8},
    "Ghana": {"w": 4, "d": 2, "l": 4, "gf": 10, "ga": 11},
    "Bosnia and Herzegovina": {"w": 4, "d": 3, "l": 3, "gf": 11, "ga": 9},
    "Iraq": {"w": 5, "d": 2, "l": 3, "gf": 12, "ga": 9},
    "Jordan": {"w": 4, "d": 2, "l": 4, "gf": 9, "ga": 10},
    "Panama": {"w": 4, "d": 2, "l": 4, "gf": 8, "ga": 10},
    "South Africa": {"w": 4, "d": 3, "l": 3, "gf": 9, "ga": 7},
    "DR Congo": {"w": 4, "d": 2, "l": 4, "gf": 10, "ga": 11},
    "Cape Verde": {"w": 3, "d": 3, "l": 4, "gf": 8, "ga": 10},
    "Curacao": {"w": 3, "d": 1, "l": 6, "gf": 8, "ga": 16},
    "Haiti": {"w": 2, "d": 2, "l": 6, "gf": 6, "ga": 14},
    "New Zealand": {"w": 3, "d": 2, "l": 5, "gf": 8, "ga": 13},
}

WC_PEDIGREE = {
    "Brazil": 100, "Germany": 95, "Argentina": 95, "France": 90, "Spain": 85,
    "England": 80, "Uruguay": 85, "Netherlands": 82, "Croatia": 75, "Portugal": 72,
    "Belgium": 65, "Mexico": 60, "Switzerland": 55, "South Korea": 58, "Japan": 52,
    "United States": 50, "Morocco": 60, "Colombia": 55, "Senegal": 48, "Ghana": 52,
    "Australia": 40, "Iran": 38, "Ecuador": 42, "Tunisia": 38, "Saudi Arabia": 40,
    "Algeria": 38, "Ivory Coast": 35, "Turkiye": 55, "Sweden": 65, "Scotland": 42,
    "Austria": 45, "Paraguay": 45, "Czechia": 50, "Norway": 35, "Egypt": 30,
    "Panama": 25, "New Zealand": 20, "Qatar": 20, "Iraq": 25, "Jordan": 15,
    "Bosnia and Herzegovina": 22, "Bolivia": 20, "Cape Verde": 10, "Haiti": 15,
    "South Africa": 35, "Curacao": 5, "DR Congo": 20, "Uzbekistan": 18,
}

HOST_NATIONS = {"United States", "Mexico", "Canada"}

COMPLETED_RESULTS = [
    {"date": "June 11", "group": "A", "home": "Mexico", "away": "South Africa", "home_goals": 2, "away_goals": 0},
    {"date": "June 12", "group": "A", "home": "South Korea", "away": "Czechia", "home_goals": 2, "away_goals": 1},
    {"date": "June 12", "group": "B", "home": "Canada", "away": "Bosnia and Herzegovina", "home_goals": 1, "away_goals": 1},
    {"date": "June 13", "group": "D", "home": "United States", "away": "Paraguay", "home_goals": 4, "away_goals": 1},
    {"date": "June 13", "group": "B", "home": "Qatar", "away": "Switzerland", "home_goals": 1, "away_goals": 1},
    {"date": "June 13", "group": "C", "home": "Brazil", "away": "Morocco", "home_goals": 1, "away_goals": 1},
    {"date": "June 14", "group": "C", "home": "Haiti", "away": "Scotland", "home_goals": 0, "away_goals": 1},
    {"date": "June 14", "group": "D", "home": "Australia", "away": "Turkiye", "home_goals": 2, "away_goals": 0},
    {"date": "June 14", "group": "E", "home": "Germany", "away": "Curacao", "home_goals": 7, "away_goals": 1},
    {"date": "June 14", "group": "F", "home": "Netherlands", "away": "Japan", "home_goals": 2, "away_goals": 2},
    {"date": "June 15", "group": "E", "home": "Ivory Coast", "away": "Ecuador", "home_goals": 1, "away_goals": 0},
    {"date": "June 15", "group": "F", "home": "Sweden", "away": "Tunisia", "home_goals": 5, "away_goals": 1},
    {"date": "June 15", "group": "H", "home": "Spain", "away": "Cape Verde", "home_goals": 0, "away_goals": 0},
    {"date": "June 15", "group": "G", "home": "Egypt", "away": "Belgium", "home_goals": 1, "away_goals": 1},
    {"date": "June 15", "group": "H", "home": "Saudi Arabia", "away": "Uruguay", "home_goals": 1, "away_goals": 1},
    {"date": "June 16", "group": "G", "home": "Iran", "away": "New Zealand", "home_goals": 2, "away_goals": 2},
    {"date": "June 16", "group": "I", "home": "France", "away": "Senegal", "home_goals": 3, "away_goals": 1},
    {"date": "June 16", "group": "I", "home": "Iraq", "away": "Norway", "home_goals": 1, "away_goals": 4},
    {"date": "June 17", "group": "J", "home": "Argentina", "away": "Algeria", "home_goals": 3, "away_goals": 0},
    {"date": "June 17", "group": "J", "home": "Austria", "away": "Jordan", "home_goals": 3, "away_goals": 1},
    {"date": "June 17", "group": "K", "home": "Portugal", "away": "DR Congo", "home_goals": 1, "away_goals": 1},
    {"date": "June 17", "group": "L", "home": "England", "away": "Croatia", "home_goals": 4, "away_goals": 2},
    {"date": "June 17", "group": "L", "home": "Ghana", "away": "Panama", "home_goals": 1, "away_goals": 0},
    {"date": "June 17", "group": "K", "home": "Colombia", "away": "Uzbekistan", "home_goals": 3, "away_goals": 1},
    {"date": "June 18", "group": "A", "home": "Czechia", "away": "South Africa", "home_goals": 1, "away_goals": 1},
]

GROUPS = {
    "A": ["Mexico", "South Africa", "South Korea", "Czechia"],
    "B": ["Canada", "Switzerland", "Qatar", "Bosnia and Herzegovina"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["United States", "Paraguay", "Australia", "Turkiye"],
    "E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

REMAINING_GROUP_MATCHES = [
    {"date": "June 18", "group": "A", "home": "Mexico", "away": "South Korea"},
    {"date": "June 18", "group": "B", "home": "Switzerland", "away": "Canada"},
    {"date": "June 18", "group": "B", "home": "Bosnia and Herzegovina", "away": "Qatar"},
    {"date": "June 19", "group": "C", "home": "Morocco", "away": "Haiti"},
    {"date": "June 19", "group": "C", "home": "Scotland", "away": "Brazil"},
    {"date": "June 19", "group": "D", "home": "Paraguay", "away": "Australia"},
    {"date": "June 19", "group": "D", "home": "Turkiye", "away": "United States"},
    {"date": "June 20", "group": "E", "home": "Curacao", "away": "Ivory Coast"},
    {"date": "June 20", "group": "E", "home": "Ecuador", "away": "Germany"},
    {"date": "June 20", "group": "F", "home": "Japan", "away": "Sweden"},
    {"date": "June 20", "group": "F", "home": "Tunisia", "away": "Netherlands"},
    {"date": "June 21", "group": "G", "home": "Belgium", "away": "Iran"},
    {"date": "June 21", "group": "G", "home": "New Zealand", "away": "Egypt"},
    {"date": "June 21", "group": "H", "home": "Uruguay", "away": "Spain"},
    {"date": "June 21", "group": "H", "home": "Cape Verde", "away": "Saudi Arabia"},
    {"date": "June 22", "group": "I", "home": "Senegal", "away": "Iraq"},
    {"date": "June 22", "group": "I", "home": "Norway", "away": "France"},
    {"date": "June 22", "group": "J", "home": "Algeria", "away": "Austria"},
    {"date": "June 22", "group": "J", "home": "Jordan", "away": "Argentina"},
    {"date": "June 23", "group": "K", "home": "DR Congo", "away": "Colombia"},
    {"date": "June 23", "group": "K", "home": "Uzbekistan", "away": "Portugal"},
    {"date": "June 23", "group": "L", "home": "Croatia", "away": "Ghana"},
    {"date": "June 23", "group": "L", "home": "Panama", "away": "England"},
    {"date": "June 25", "group": "A", "home": "South Africa", "away": "South Korea"},
    {"date": "June 25", "group": "A", "home": "Czechia", "away": "Mexico"},
    {"date": "June 25", "group": "B", "home": "Bosnia and Herzegovina", "away": "Switzerland"},
    {"date": "June 25", "group": "B", "home": "Qatar", "away": "Canada"},
    {"date": "June 25", "group": "C", "home": "Scotland", "away": "Morocco"},
    {"date": "June 25", "group": "C", "home": "Haiti", "away": "Brazil"},
    {"date": "June 25", "group": "D", "home": "Turkiye", "away": "Paraguay"},
    {"date": "June 25", "group": "D", "home": "Australia", "away": "United States"},
    {"date": "June 26", "group": "E", "home": "Ecuador", "away": "Curacao"},
    {"date": "June 26", "group": "E", "home": "Ivory Coast", "away": "Germany"},
    {"date": "June 26", "group": "F", "home": "Tunisia", "away": "Japan"},
    {"date": "June 26", "group": "F", "home": "Sweden", "away": "Netherlands"},
    {"date": "June 26", "group": "G", "home": "New Zealand", "away": "Belgium"},
    {"date": "June 26", "group": "G", "home": "Iran", "away": "Egypt"},
    {"date": "June 26", "group": "H", "home": "Cape Verde", "away": "Uruguay"},
    {"date": "June 26", "group": "H", "home": "Saudi Arabia", "away": "Spain"},
    {"date": "June 27", "group": "I", "home": "Iraq", "away": "France"},
    {"date": "June 27", "group": "I", "home": "Norway", "away": "Senegal"},
    {"date": "June 27", "group": "J", "home": "Jordan", "away": "Algeria"},
    {"date": "June 27", "group": "J", "home": "Austria", "away": "Argentina"},
    {"date": "June 27", "group": "K", "home": "Uzbekistan", "away": "DR Congo"},
    {"date": "June 27", "group": "K", "home": "Colombia", "away": "Portugal"},
    {"date": "June 27", "group": "L", "home": "Panama", "away": "Croatia"},
    {"date": "June 27", "group": "L", "home": "Ghana", "away": "England"},
]


def get_team_rating(team):
    rank, elo = FIFA_RANKINGS.get(team, (60, 1350))
    squad = SQUAD_STRENGTH.get(team, 50)
    mgr = MANAGER_STATS.get(team, {"score": 50})["score"]
    pedigree = WC_PEDIGREE.get(team, 20)
    form = RECENT_FORM.get(team, {"w": 3, "d": 3, "l": 4, "gf": 8, "ga": 10})

    form_pts = (form["w"] * 3 + form["d"]) / 30.0
    gd_ratio = (form["gf"] - form["ga"]) / max(form["gf"] + form["ga"], 1)

    rating = (
        elo * 0.30 +
        squad * 5.0 * 0.25 +
        mgr * 3.0 * 0.10 +
        pedigree * 3.0 * 0.10 +
        form_pts * 500 * 0.15 +
        gd_ratio * 200 * 0.10
    )

    return rating


def poisson_prob(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam ** k * math.exp(-lam)) / math.factorial(k)


def _make_rng(home_team, away_team, match_date=None):
    if match_date is None:
        match_date = date.today().isoformat()
    seed_str = f"{home_team}|{away_team}|{match_date}"
    seed = abs(hash(seed_str)) % (2 ** 31)
    return random.Random(seed)


def _sample_poisson_goals(lam, rng, max_goals=10):
    if lam <= 0:
        return 0
    p = rng.random()
    k = 0
    cdf = math.exp(-lam)
    while p > cdf and k < max_goals:
        k += 1
        cdf += (lam ** k * math.exp(-lam)) / math.factorial(k)
    return k


def predict_wc_match(home_team, away_team, neutral=True, match_date=None):
    home_rating = get_team_rating(home_team)
    away_rating = get_team_rating(away_team)

    home_boost = 0.0
    if not neutral:
        home_boost = 50
    if home_team in HOST_NATIONS:
        home_boost = 35

    home_rating += home_boost

    rating_diff = (home_rating - away_rating) / 400.0

    home_form = RECENT_FORM.get(home_team, {"gf": 10, "ga": 10, "w": 4, "d": 3, "l": 3})
    away_form = RECENT_FORM.get(away_team, {"gf": 10, "ga": 10, "w": 4, "d": 3, "l": 3})

    home_attack = home_form["gf"] / 10.0
    away_attack = away_form["gf"] / 10.0
    home_defense = away_form["ga"] / 10.0
    away_defense = home_form["ga"] / 10.0

    base_home = 1.35 * (1 + 0.7 * math.tanh(rating_diff))
    base_away = 1.35 * (1 - 0.7 * math.tanh(rating_diff))

    exp_home = base_home * (0.4 + 0.35 * home_attack + 0.25 * home_defense)
    exp_away = base_away * (0.4 + 0.35 * away_attack + 0.25 * away_defense)

    exp_home = max(0.1, min(6.0, exp_home))
    exp_away = max(0.1, min(6.0, exp_away))

    prob_home_win = 0.0
    prob_draw = 0.0
    prob_away_win = 0.0
    max_p = -1
    best_score = (0, 0)

    for h in range(12):
        for a in range(12):
            p = poisson_prob(h, exp_home) * poisson_prob(a, exp_away)
            if p > max_p:
                max_p = p
                best_score = (h, a)
            if h > a:
                prob_home_win += p
            elif h < a:
                prob_away_win += p
            else:
                prob_draw += p

    total = prob_home_win + prob_draw + prob_away_win
    if total > 0:
        prob_home_win /= total
        prob_draw /= total
        prob_away_win /= total

    home_goals, away_goals = best_score

    if home_goals > away_goals:
        winner = home_team
    elif away_goals > home_goals:
        winner = away_team
    else:
        winner = "Draw"

    return {
        "home": home_team,
        "away": away_team,
        "score": f"{home_goals}-{away_goals}",
        "home_goals": home_goals,
        "away_goals": away_goals,
        "exp_home_goals": round(exp_home, 2),
        "exp_away_goals": round(exp_away, 2),
        "prob_home": round(prob_home_win, 4),
        "prob_draw": round(prob_draw, 4),
        "prob_away": round(prob_away_win, 4),
        "winner": winner,
        "confidence": round(max(prob_home_win, prob_draw, prob_away_win) * 100, 1),
    }


def _incorporate_wc_results_into_form():
    for match in COMPLETED_RESULTS:
        for team, gf, ga in [(match["home"], match["home_goals"], match["away_goals"]),
                              (match["away"], match["away_goals"], match["home_goals"])]:
            if team not in RECENT_FORM:
                RECENT_FORM[team] = {"w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0}
            prev = RECENT_FORM[team]
            prev["gf"] += gf
            prev["ga"] += ga
            if gf > ga:
                prev["w"] += 1
            elif gf < ga:
                prev["l"] += 1
            else:
                prev["d"] += 1


def simulate_group_stage():
    _incorporate_wc_results_into_form()

    standings = {}
    for group, teams in GROUPS.items():
        for team in teams:
            standings[team] = {
                "group": group, "pts": 0, "w": 0, "d": 0, "l": 0,
                "gf": 0, "ga": 0, "gd": 0, "played": 0
            }

    all_match_results = []

    for match in COMPLETED_RESULTS:
        h, a = match["home"], match["away"]
        hg, ag = match["home_goals"], match["away_goals"]

        standings[h]["played"] += 1
        standings[a]["played"] += 1
        standings[h]["gf"] += hg
        standings[h]["ga"] += ag
        standings[a]["gf"] += ag
        standings[a]["ga"] += hg
        standings[h]["gd"] = standings[h]["gf"] - standings[h]["ga"]
        standings[a]["gd"] = standings[a]["gf"] - standings[a]["ga"]

        if hg > ag:
            standings[h]["pts"] += 3
            standings[h]["w"] += 1
            standings[a]["l"] += 1
            winner = h
        elif hg < ag:
            standings[a]["pts"] += 3
            standings[a]["w"] += 1
            standings[h]["l"] += 1
            winner = a
        else:
            standings[h]["pts"] += 1
            standings[a]["pts"] += 1
            standings[h]["d"] += 1
            standings[a]["d"] += 1
            winner = "Draw"

        all_match_results.append({
            "date": match["date"], "group": match["group"],
            "home": h, "away": a, "score": f"{hg}-{ag}",
            "winner": winner, "status": "COMPLETED",
            "prob_home": "-", "prob_draw": "-", "prob_away": "-",
        })

    for match in REMAINING_GROUP_MATCHES:
        pred = predict_wc_match(match["home"], match["away"], neutral=True, match_date=match["date"])
        h, a = match["home"], match["away"]
        hg, ag = pred["home_goals"], pred["away_goals"]

        standings[h]["played"] += 1
        standings[a]["played"] += 1
        standings[h]["gf"] += hg
        standings[h]["ga"] += ag
        standings[a]["gf"] += ag
        standings[a]["ga"] += hg
        standings[h]["gd"] = standings[h]["gf"] - standings[h]["ga"]
        standings[a]["gd"] = standings[a]["gf"] - standings[a]["ga"]

        if hg > ag:
            standings[h]["pts"] += 3
            standings[h]["w"] += 1
            standings[a]["l"] += 1
        elif hg < ag:
            standings[a]["pts"] += 3
            standings[a]["w"] += 1
            standings[h]["l"] += 1
        else:
            standings[h]["pts"] += 1
            standings[a]["pts"] += 1
            standings[h]["d"] += 1
            standings[a]["d"] += 1

        all_match_results.append({
            "date": match["date"], "group": match["group"],
            "home": h, "away": a, "score": pred["score"],
            "winner": pred["winner"], "status": "PREDICTED",
            "prob_home": f"{pred['prob_home'] * 100:.0f}%",
            "prob_draw": f"{pred['prob_draw'] * 100:.0f}%",
            "prob_away": f"{pred['prob_away'] * 100:.0f}%",
            "confidence": pred["confidence"],
        })

    return standings, all_match_results


def get_group_standings(standings):
    group_tables = defaultdict(list)
    for team, stats in standings.items():
        group_tables[stats["group"]].append((team, stats))

    for group in group_tables:
        group_tables[group].sort(key=lambda x: (-x[1]["pts"], -x[1]["gd"], -x[1]["gf"]))

    return dict(group_tables)


def get_qualified_teams(group_tables):
    auto_qualified = []
    third_placed = []

    for group in sorted(group_tables.keys()):
        teams = group_tables[group]
        if len(teams) >= 1:
            auto_qualified.append((teams[0][0], group, 1))
        if len(teams) >= 2:
            auto_qualified.append((teams[1][0], group, 2))
        if len(teams) >= 3:
            third_placed.append((teams[2][0], group, teams[2][1]))

    third_placed.sort(key=lambda x: (-x[2]["pts"], -x[2]["gd"], -x[2]["gf"]))
    best_thirds = [(t[0], t[1], 3) for t in third_placed[:8]]

    return auto_qualified, best_thirds


def predict_knockout_match(team_a, team_b, stage="KO"):
    pred = predict_wc_match(team_a, team_b, neutral=True, match_date=stage)

    if pred["winner"] == "Draw":
        r_a = get_team_rating(team_a)
        r_b = get_team_rating(team_b)
        if r_a >= r_b:
            pred["winner"] = team_a
            pred["home_goals"] = 1
            pred["away_goals"] = 0
        else:
            pred["winner"] = team_b
            pred["home_goals"] = 0
            pred["away_goals"] = 1
        pred["score"] = f"{pred['home_goals']}-{pred['away_goals']}"
        pred["extra_time"] = True
    else:
        pred["extra_time"] = False

    return pred


def simulate_knockout_stage(group_tables):
    auto, thirds = get_qualified_teams(group_tables)

    group_winners = {pos[1]: pos[0] for pos in auto if pos[2] == 1}
    group_runners = {pos[1]: pos[0] for pos in auto if pos[2] == 2}
    third_teams = [t[0] for t in thirds]

    r32_matchups = [
        (group_winners.get("A", "TBD"), group_runners.get("C", "TBD")),
        (group_winners.get("B", "TBD"), third_teams[0] if len(third_teams) > 0 else "TBD"),
        (group_winners.get("C", "TBD"), group_runners.get("A", "TBD")),
        (group_winners.get("D", "TBD"), third_teams[1] if len(third_teams) > 1 else "TBD"),
        (group_winners.get("E", "TBD"), group_runners.get("G", "TBD")),
        (group_winners.get("F", "TBD"), third_teams[2] if len(third_teams) > 2 else "TBD"),
        (group_winners.get("G", "TBD"), group_runners.get("E", "TBD")),
        (group_winners.get("H", "TBD"), third_teams[3] if len(third_teams) > 3 else "TBD"),
        (group_winners.get("I", "TBD"), group_runners.get("K", "TBD")),
        (group_winners.get("J", "TBD"), third_teams[4] if len(third_teams) > 4 else "TBD"),
        (group_winners.get("K", "TBD"), group_runners.get("I", "TBD")),
        (group_winners.get("L", "TBD"), third_teams[5] if len(third_teams) > 5 else "TBD"),
        (group_runners.get("B", "TBD"), third_teams[6] if len(third_teams) > 6 else "TBD"),
        (group_runners.get("D", "TBD"), group_runners.get("F", "TBD")),
        (group_runners.get("H", "TBD"), group_runners.get("J", "TBD")),
        (group_runners.get("L", "TBD"), third_teams[7] if len(third_teams) > 7 else "TBD"),
    ]

    knockout_results = {"R32": [], "R16": [], "QF": [], "SF": [], "3rd": None, "Final": None}

    r16_winners = []
    for team_a, team_b in r32_matchups:
        if "TBD" in (team_a, team_b):
            r16_winners.append(team_a if team_b == "TBD" else team_b)
            continue
        pred = predict_knockout_match(team_a, team_b, "R32")
        knockout_results["R32"].append(pred)
        r16_winners.append(pred["winner"])

    qf_winners = []
    for i in range(0, len(r16_winners), 2):
        if i + 1 < len(r16_winners):
            pred = predict_knockout_match(r16_winners[i], r16_winners[i + 1], "R16")
            knockout_results["R16"].append(pred)
            qf_winners.append(pred["winner"])

    sf_winners = []
    sf_losers = []
    for i in range(0, len(qf_winners), 2):
        if i + 1 < len(qf_winners):
            pred = predict_knockout_match(qf_winners[i], qf_winners[i + 1], "QF")
            knockout_results["QF"].append(pred)
            sf_winners.append(pred["winner"])
            loser = qf_winners[i] if pred["winner"] == qf_winners[i + 1] else qf_winners[i + 1]
            sf_losers.append(loser)

    final_teams = []
    third_place_teams = []
    for i in range(0, len(sf_winners), 2):
        if i + 1 < len(sf_winners):
            pred = predict_knockout_match(sf_winners[i], sf_winners[i + 1], "SF")
            knockout_results["SF"].append(pred)
            final_teams.append(pred["winner"])
            loser = sf_winners[i] if pred["winner"] == sf_winners[i + 1] else sf_winners[i + 1]
            third_place_teams.append(loser)

    if len(third_place_teams) >= 2:
        pred = predict_knockout_match(third_place_teams[0], third_place_teams[1], "3rd")
        knockout_results["3rd"] = pred

    if len(final_teams) >= 2:
        pred = predict_knockout_match(final_teams[0], final_teams[1], "Final")
        knockout_results["Final"] = pred

    return knockout_results


def generate_and_save_predictions(output_path="data/worldcup_predictions.json"):
    ratings = [(team, get_team_rating(team)) for team in FIFA_RANKINGS.keys()]
    ratings.sort(key=lambda x: -x[1])

    favorites_list = []
    for team, rating in ratings:
        rank, elo = FIFA_RANKINGS[team]
        squad = SQUAD_STRENGTH.get(team, 50)
        mgr = MANAGER_STATS.get(team, {"score": 50})
        form = RECENT_FORM.get(team, {"w": 0, "d": 0, "l": 0})
        ped = WC_PEDIGREE.get(team, 20)
        favorites_list.append({
            "team": team,
            "rating": round(rating, 1),
            "fifa_rank": rank,
            "elo": elo,
            "squad_strength": squad,
            "manager": mgr.get("name", "Unknown"),
            "manager_score": mgr.get("score", 50),
            "form": f"{form['w']}W-{form['d']}D-{form['l']}L",
            "pedigree": ped
        })

    standings, all_matches = simulate_group_stage()

    group_tables = get_group_standings(standings)

    standings_json = {}
    for group, teams in group_tables.items():
        standings_json[group] = []
        for team, stats in teams:
            standings_json[group].append({
                "team": team,
                "played": stats["played"],
                "w": stats["w"],
                "d": stats["d"],
                "l": stats["l"],
                "gf": stats["gf"],
                "ga": stats["ga"],
                "gd": stats["gd"],
                "pts": stats["pts"]
            })

    knockout_results = simulate_knockout_stage(group_tables)

    final = knockout_results.get("Final")
    third = knockout_results.get("3rd")

    summary = {}
    if final:
        champion = final["winner"]
        runner = final["home"] if final["winner"] == final["away"] else final["away"]
        summary["champion"] = champion
        summary["runner_up"] = runner
    if third:
        summary["third_place"] = third["winner"]

    data = {
        "favorites": favorites_list,
        "group_stage": {
            "matches": all_matches,
            "standings": standings_json
        },
        "knockout_stage": knockout_results,
        "summary": summary,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"World Cup predictions written to {output_path}")
    return data


def main():
    print("\n" + "=" * 40)
    print("  FIFA WORLD CUP 2026 - COMPLETE TOURNAMENT PREDICTION")
    print("  Canada \u2022 Mexico \u2022 United States  |  June 11 - July 19, 2026")
    print("  48 Teams \u2022 104 Matches \u2022 16 Host Cities")
    print("=" * 40)

    data = generate_and_save_predictions()

    all_matches = data["group_stage"]["matches"]

    group_tables = {}
    for group, teams_list in data["group_stage"]["standings"].items():
        group_tables[group] = [(t["team"], t) for t in teams_list]

    knockout_results = data["knockout_stage"]

    print_group_matches(all_matches)
    print_group_standings(group_tables)

    print("\n" + "=" * 40)
    print("  KNOCKOUT STAGE PREDICTIONS")
    print("  Top 2 from each group + 8 best 3rd-placed teams advance to Round of 32")
    print("=" * 40)
    print_knockout_stage(knockout_results)

    print("\n" + "=" * 40)
    print("  TOURNAMENT SUMMARY")
    print("=" * 40)

    final = knockout_results.get("Final")
    third = knockout_results.get("3rd")

    if final:
        champion = final["winner"]
        runner = final["home"] if final["winner"] == final["away"] else final["away"]
        print(f"\n  CHAMPION:    {champion}")
        print(f"  RUNNER-UP:   {runner}")
    if third:
        print(f"  THIRD PLACE: {third['winner']}")

    print(f"\n  Predictions generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 40)


def print_group_matches(match_results):
    print("\n" + "=" * 80)
    print("  GROUP STAGE MATCHES")
    print("=" * 80)

    current_group = None
    for m in match_results:
        if m["group"] != current_group:
            current_group = m["group"]
            teams = ", ".join(GROUPS[current_group])
            print(f"\n  GROUP {current_group}: {teams}")
            print(f"  {'Date':<10} {'Status':<10} {'Home':>20} {'Score':^7} {'Away':<20}  Winner")
            print(f"  {'-' * 68}")

        status_text = "RESULT" if m["status"] == "COMPLETED" else "PREDICTED"
        print(f"  {m['date']:<10} {status_text:<10} {m['home']:>20} {m['score']:^7} {m['away']:<20}  {m['winner']}")


def print_group_standings(group_tables):
    print("\n" + "=" * 80)
    print("  GROUP STANDINGS")
    print("=" * 80)

    for group in sorted(group_tables.keys()):
        print(f"\n  GROUP {group}")
        print(f"  {'Pos':<5} {'Team':<22} {'P':>3} {'W':>3} {'D':>3} {'L':>3} {'GF':>4} {'GA':>4} {'GD':>4} {'Pts':>5}")
        print(f"  {'-' * 60}")

        for i, (team, stats) in enumerate(group_tables[group]):
            pos = i + 1
            pts_display = f"[{stats['pts']}]"
            print(f"  {pos:<5} {team:<22} {stats['played']:>3} {stats['w']:>3} {stats['d']:>3} {stats['l']:>3} {stats['gf']:>4} {stats['ga']:>4} {stats['gd']:>+4} {pts_display:>5}")


def print_knockout_stage(knockout_results):
    round_names = {
        "R32": "ROUND OF 32",
        "R16": "ROUND OF 16",
        "QF": "QUARTER FINALS",
        "SF": "SEMI FINALS",
    }

    for stage, name in round_names.items():
        matches = knockout_results.get(stage, [])
        if not matches:
            continue

        print(f"\n  {name}")
        print(f"  {'Match':<5} {'Home':>20} {'Score':^7} {'Away':<20}  Winner")
        print(f"  {'-' * 60}")

        for i, m in enumerate(matches, 1):
            et = " (ET/Pen)" if m.get("extra_time") else ""
            print(f"  M{i:<4} {m['home']:>20} {m['score']:^7} {m['away']:<20}  {m['winner']}{et}")

    if knockout_results.get("3rd"):
        m = knockout_results["3rd"]
        et = " (ET/Pen)" if m.get("extra_time") else ""
        print(f"\n  THIRD PLACE PLAY-OFF")
        print(f"  {m['home']:>20} {m['score']:^7} {m['away']:<20}  ->  {m['winner']}{et}")

    if knockout_results.get("Final"):
        m = knockout_results["Final"]
        et = " (ET/Pen)" if m.get("extra_time") else ""
        print(f"\n  FINAL")
        print(f"  {m['home']:>20} {m['score']:^7} {m['away']:<20}")
        print(f"  CHAMPION: {m['winner']}{et}")


if __name__ == "__main__":
    main()
