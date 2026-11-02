"""Stochastic with-profits sketch with a company-level bonus rule (dependency class C2).

Each month the insurer compares total asset shares with total guaranteed benefits across
the whole portfolio (per scenario) and declares a bonus rate from that cover ratio. The
bonus increases every policy's guaranteed benefit, which changes next month's cover ratio:
cross-policy feedback that cannot be computed policy by policy — the reason Prophet has
its ALS "dynamic loop" and Meridian has the C2 lockstep engine (spec sections 4.1b, 19.4).

Simplifications (illustration only): premiums buy guaranteed benefit 1:1, exits are paid
max(asset share, guarantee), the cost of guarantee is the shortfall on exit, and returns
are a single equity-like asset.
"""

from __future__ import annotations

import numpy as np

from ..dsl import Model, clip, maximum, sum_policies, t, where

#: Indices into the `wp_params` table.
EXIT_RATE, CHARGE, MAX_BONUS, BONUS_SENSITIVITY, RISK_FREE = range(5)


def build(n_years: int = 20) -> Model:
    m = Model("with_profits_c2", n_steps=n_years * 12)
    v, mp, tb, scen = m.v, m.mp, m.tables, m.scen

    @m.var
    def fund_return():
        """Monthly fund return in this scenario."""
        return scen.equity_return_m

    @m.var
    def exit_month():
        return 1 - (1 - tb.wp_params[EXIT_RATE]) ** (1 / 12)

    @m.var(init=0.0)
    def pols_if():
        return where(t == 0, mp.policy_count, v.pols_if.lag(1) - v.exits.lag(1))

    @m.var(total=True)
    def exits():
        return v.pols_if * v.exit_month

    @m.var
    def prem_pp():
        return mp.annual_premium / 12

    @m.var
    def asset_share_pp():
        """Asset share per policy: accumulated premiums net of charges at the fund return."""
        return where(t == 0, mp.asset_share_pp,
                     (v.asset_share_pp.lag(1) + v.prem_pp.lag(1) * (1 - tb.wp_params[CHARGE]))
                     * (1 + v.fund_return.lag(1)))

    @m.var
    def guaranteed_pp():
        """Guaranteed benefit per policy, increased by last month's declared bonus."""
        return where(t == 0, mp.guaranteed_pp,
                     v.guaranteed_pp.lag(1) * (1 + v.bonus_rate.lag(1) / 12) + v.prem_pp.lag(1))

    @m.var
    def total_assets():
        """Company level: sum over all policies in the scenario (C2)."""
        return sum_policies(v.asset_share_pp * v.pols_if)

    @m.var
    def total_guarantees():
        return sum_policies(v.guaranteed_pp * v.pols_if)

    @m.var
    def cover_ratio():
        return v.total_assets / v.total_guarantees

    @m.var
    def bonus_rate():
        """Annual bonus rate declared this month from the company cover ratio."""
        return clip((v.cover_ratio - 1) * tb.wp_params[BONUS_SENSITIVITY], 0.0, tb.wp_params[MAX_BONUS])

    @m.var(total=True)
    def payouts():
        return v.exits * maximum(v.asset_share_pp, v.guaranteed_pp)

    @m.var(total=True)
    def guarantee_cost():
        return v.exits * maximum(v.guaranteed_pp - v.asset_share_pp, 0.0)

    @m.var
    def disc():
        return (1 + tb.wp_params[RISK_FREE]) ** (-(t + 1) / 12)

    @m.var(total=True, policy_sum=True)
    def pv_guarantee_cost():
        return v.guarantee_cost * v.disc

    return m


def default_tables() -> dict[str, np.ndarray]:
    return {"wp_params": np.array([0.06, 0.01, 0.06, 0.5, 0.03])}


def synthetic_portfolio(n: int, seed: int = 1) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    guaranteed = np.round(rng.lognormal(np.log(30_000), 0.5, size=n), 0)
    return {
        "policy_count": np.ones(n),
        "guaranteed_pp": guaranteed,
        "asset_share_pp": np.round(guaranteed * rng.uniform(0.85, 1.25, size=n), 0),
        "annual_premium": np.round(rng.uniform(600, 3_000, size=n), 0),
    }


def scenarios(n_scenarios: int, n_steps: int, seed: int = 2,
              mu: float = 0.05, sigma: float = 0.15) -> dict[str, np.ndarray]:
    """Lognormal monthly equity returns, shape (n_scenarios, n_steps)."""
    rng = np.random.default_rng(seed)
    dt = 1 / 12
    z = rng.standard_normal((n_scenarios, n_steps))
    r = np.exp((mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * z) - 1
    return {"equity_return_m": r}
