"""Time-weighted Dixon-Coles model on an xG / goals blend.

Each club gets an attack and a defence strength; a match's expected goals are

    home: exp(attack_home + defence_away + home_advantage)
    away: exp(attack_away + defence_home)

fitted by maximum likelihood over past results (Dixon & Coles, 1997), with
older matches down-weighted by exp(-XI * days ago) and the low-score
correction rho applied to 0-0, 1-0, 0-1 and 1-1. The count each side is fitted
to is XG_WEIGHT * xG + (1 - XG_WEIGHT) * goals where xG is known, plain goals
otherwise: xG measures chance quality, so it carries more signal about
strength than the goals a few lucky or unlucky finishes produced.

Chosen by a walk-forward backtest over 1,010 Premier League matches
(Aug 2023 - Feb 2026, `python -m backend.backtest`): RPS 0.1967 against
0.2051 for the random forest it replaced, 0.1995 for goals-only Dixon-Coles
and 0.2006 for Elo alone. The xG weight is flat between 0.65 and 0.85.
"""
import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln
from scipy.stats import poisson

from backend import utils

# Daily decay: a match five months old (154 days) counts half as much as one
# played today. Best of 0.001-0.011 in the backtest, on both 2023-on and
# 2024-on windows.
XI = 0.0045
XG_WEIGHT = 0.75
MAX_GOALS = 10
# A club with no history (newly promoted, before its first match) starts as
# a weaker-than-average side: promoted clubs mostly are.
UNSEEN_PENALTY = 0.25


class Model:
    def __init__(self, teams, params):
        n = len(teams)
        self.index = {t: i for i, t in enumerate(teams)}
        self.attack, self.defence = params[:n], params[n:2 * n]
        self.home, self.rho = float(params[2 * n]), float(params[2 * n + 1])

    def strengths(self, team):
        i = self.index.get(utils.normalize_team_name(team))
        if i is None:
            return self.attack.mean() - UNSEEN_PENALTY, self.defence.mean() + UNSEEN_PENALTY
        return self.attack[i], self.defence[i]

    def expected_goals(self, home_team, away_team):
        ha, hd = self.strengths(home_team)
        aa, ad = self.strengths(away_team)
        return float(np.exp(ha + ad + self.home)), float(np.exp(aa + hd))

    def score_matrix(self, home_goals, away_goals):
        """P(home scores i, away scores j), Dixon-Coles corrected, normalised."""
        g = np.arange(MAX_GOALS + 1)
        m = np.outer(poisson.pmf(g, home_goals), poisson.pmf(g, away_goals))
        m[0, 0] *= 1 - home_goals * away_goals * self.rho
        m[0, 1] *= 1 + home_goals * self.rho
        m[1, 0] *= 1 + away_goals * self.rho
        m[1, 1] *= 1 - self.rho
        return m / m.sum()


def _counts(results, xg_weight):
    goals = results[['home_goals', 'away_goals']].to_numpy(float)
    if 'home_xg' not in results:
        return goals
    xg = results[['home_xg', 'away_xg']].to_numpy(float)
    blended = xg_weight * xg + (1 - xg_weight) * goals
    return np.where(np.isnan(xg), goals, blended)


def fit(results, as_of, xi=XI, xg_weight=XG_WEIGHT):
    """Fit on results played before `as_of`.

    results: DataFrame with date, home_team, away_team, home_goals,
    away_goals and optionally home_xg / away_xg (NaN where unknown).
    """
    results = results[results['date'] < as_of].dropna(subset=['home_goals', 'away_goals'])
    if len(results) < 50:
        raise ValueError(f'too few results to fit ({len(results)})')
    home_names = utils.normalize_column(results['home_team'])
    away_names = utils.normalize_column(results['away_team'])
    teams = sorted(set(home_names) | set(away_names))
    index = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    h = home_names.map(index).to_numpy()
    a = away_names.map(index).to_numpy()
    x, y = _counts(results, xg_weight).T
    hg, ag = results['home_goals'].to_numpy(int), results['away_goals'].to_numpy(int)
    days = (as_of - results['date']).dt.total_seconds().to_numpy() / 86400
    w = np.exp(-xi * days)
    const = gammaln(x + 1) + gammaln(y + 1)
    m00, m01, m10, m11 = (hg == 0) & (ag == 0), (hg == 0) & (ag == 1), (hg == 1) & (ag == 0), (hg == 1) & (ag == 1)

    def nll_and_grad(p):
        att, dfn, home, rho = p[:n], p[n:2 * n], p[2 * n], p[2 * n + 1]
        lh = np.exp(att[h] + dfn[a] + home)
        la = np.exp(att[a] + dfn[h])
        ll = x * np.log(lh) - lh + y * np.log(la) - la - const
        g_lh, g_la = x - lh, y - la   # d ll / d log(lambda)
        tau = np.ones_like(lh)
        g_rho = np.zeros_like(lh)
        tau[m00] = 1 - lh[m00] * la[m00] * rho
        tau[m01] = 1 + lh[m01] * rho
        tau[m10] = 1 + la[m10] * rho
        tau[m11] = 1 - rho
        tau = np.clip(tau, 1e-10, None)
        ll = ll + np.log(tau)
        g_lh[m00] -= lh[m00] * la[m00] * rho / tau[m00]
        g_la[m00] -= lh[m00] * la[m00] * rho / tau[m00]
        g_rho[m00] = -lh[m00] * la[m00] / tau[m00]
        g_lh[m01] += lh[m01] * rho / tau[m01]
        g_rho[m01] = lh[m01] / tau[m01]
        g_la[m10] += la[m10] * rho / tau[m10]
        g_rho[m10] = la[m10] / tau[m10]
        g_rho[m11] = -1 / tau[m11]

        wh, wa = w * g_lh, w * g_la
        grad = np.zeros_like(p)
        grad[:n] = np.bincount(h, wh, n) + np.bincount(a, wa, n)
        grad[n:2 * n] = np.bincount(a, wh, n) + np.bincount(h, wa, n)
        grad[2 * n] = wh.sum()
        grad[2 * n + 1] = (w * g_rho).sum()
        # Attacks sum to zero (identifiability), as a soft penalty.
        penalty = 1e3 * att.sum() ** 2
        grad = -grad
        grad[:n] += 2e3 * att.sum()
        return -(w * ll).sum() + penalty, grad

    x0 = np.concatenate([np.zeros(2 * n), [0.25, -0.05]])
    bounds = [(None, None)] * (2 * n + 1) + [(-0.2, 0.2)]
    res = minimize(nll_and_grad, x0, jac=True, method='L-BFGS-B', bounds=bounds)
    return Model(teams, res.x)
