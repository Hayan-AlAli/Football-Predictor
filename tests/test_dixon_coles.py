import numpy as np
import pandas as pd

from backend import dixon_coles, predictor


def _season(strengths, rounds=4, start='2025-08-16', xg=None, seed=0):
    """Double round-robins between clubs with known attack strengths."""
    rng = np.random.default_rng(seed)
    teams = list(strengths)
    rows, day = [], pd.Timestamp(start)
    for _ in range(rounds):
        for h in teams:
            for a in teams:
                if h == a:
                    continue
                lh = np.exp(strengths[h] - strengths[a] / 2 + 0.25)
                la = np.exp(strengths[a] - strengths[h] / 2)
                hg, ag = rng.poisson(lh), rng.poisson(la)
                row = {'date': day, 'home_team': h, 'away_team': a, 'home_goals': hg, 'away_goals': ag}
                if xg == 'true':
                    row.update(home_xg=lh, away_xg=la)
                rows.append(row)
                day += pd.Timedelta(days=1)
    return pd.DataFrame(rows)


CLUBS = {'Arsenal': 0.5, 'Chelsea': 0.2, 'Everton': -0.1, 'Fulham': -0.3, 'Brentford': 0.0, 'Burnley': -0.4}


def test_fit_recovers_the_order_of_strength_and_home_advantage():
    df = _season(CLUBS, rounds=10)
    model = dixon_coles.fit(df, df['date'].max() + pd.Timedelta(days=1), xi=0.0)
    attack = np.array([model.strengths(t)[0] for t in CLUBS])
    assert np.corrcoef(attack, list(CLUBS.values()))[0, 1] > 0.9
    assert max(CLUBS, key=lambda t: model.strengths(t)[0]) == 'Arsenal'
    assert 0.1 < model.home < 0.4
    hg, ag = model.expected_goals('Arsenal', 'Burnley')
    assert hg > 2 * ag


def test_probabilities_sum_to_one():
    df = _season(CLUBS)
    model = dixon_coles.fit(df, df['date'].max() + pd.Timedelta(days=1))
    grid = model.score_matrix(*model.expected_goals('Chelsea', 'Everton'))
    assert abs(grid.sum() - 1) < 1e-9 and (grid >= 0).all()


def test_xg_is_weighted_above_goals():
    """Same goals, but xG says Fulham were the better side: the blend listens."""
    df = _season(CLUBS, rounds=3)
    df['home_xg'] = df['home_goals'].astype(float)
    df['away_xg'] = df['away_goals'].astype(float)
    fulham = (df['home_team'] == 'Fulham') | (df['away_team'] == 'Fulham')
    df.loc[fulham & (df['home_team'] == 'Fulham'), 'home_xg'] += 1.5
    df.loc[fulham & (df['away_team'] == 'Fulham'), 'away_xg'] += 1.5
    as_of = df['date'].max() + pd.Timedelta(days=1)
    goals_only = dixon_coles.fit(df, as_of, xg_weight=0.0).strengths('Fulham')[0]
    blended = dixon_coles.fit(df, as_of).strengths('Fulham')[0]
    assert blended > goals_only + 0.2


def test_missing_xg_falls_back_to_goals():
    df = _season(CLUBS, rounds=3)
    as_of = df['date'].max() + pd.Timedelta(days=1)
    plain = dixon_coles.fit(df, as_of)
    with_nan = dixon_coles.fit(df.assign(home_xg=np.nan, away_xg=np.nan), as_of)
    assert np.allclose(plain.attack, with_nan.attack, atol=1e-4)


def test_unseen_club_is_rated_below_average():
    df = _season(CLUBS)
    model = dixon_coles.fit(df, df['date'].max() + pd.Timedelta(days=1))
    attack, defence = model.strengths('Coventry City')
    assert attack < model.attack.mean() and defence > model.defence.mean()


def test_fit_ignores_results_on_or_after_the_cutoff():
    df = _season(CLUBS, rounds=4)
    cut = df['date'].iloc[len(df) // 2]
    before = dixon_coles.fit(df, cut)
    tampered = df.copy()
    tampered.loc[tampered['date'] >= cut, 'home_goals'] = 9
    assert np.allclose(before.attack, dixon_coles.fit(tampered, cut).attack)


def test_rebuilt_call_for_a_played_match_cannot_see_its_result(monkeypatch):
    """A past fixture is called with the fit as of its own day."""
    from backend import elo
    day = '2026-09-12'
    result = {'date': day, 'home_team': 'Hull', 'away_team': 'Arsenal', 'home_goals': 7, 'away_goals': 0}
    fixture = {'home_team': 'Hull', 'away_team': 'Arsenal', 'date': pd.Timestamp(day),
               'home_elo': 1450, 'away_elo': 1700}
    monkeypatch.setattr(elo, 'stored_results_since', lambda as_of: [])
    predictor.reset_caches()
    without = predictor.predict_match(fixture)
    monkeypatch.setattr(elo, 'stored_results_since', lambda as_of: [result])
    predictor.reset_caches()
    with_result = predictor.predict_match(fixture)
    assert with_result['prob_home'] == without['prob_home']
    # ...while a call for after that day does learn from it.
    later = predictor.predict_match({**fixture, 'date': pd.Timestamp('2026-09-20')})
    assert later['prob_home'] > without['prob_home']


def test_backtest_scores_every_candidate_on_the_same_matches():
    from backend import backtest
    df = _season(CLUBS, rounds=6).assign(home_elo=1500.0, away_elo=1500.0)
    start = df['date'].iloc[len(df) * 2 // 3]
    n, scores = backtest.run(df, start, {
        'dc': backtest.dixon_coles_candidate(0.0045, 0.75),
        'base': backtest.base_rate_candidate,
    })
    assert n == (df['date'] >= start).sum()
    assert set(scores) == {'dc', 'base'}
    assert scores['dc']['rps'] < scores['base']['rps']  # strengths beat base rates
