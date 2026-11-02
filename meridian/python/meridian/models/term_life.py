"""Monthly term assurance projection (dependency class C1).

Timing conventions (spec section 26.4 asks these to be explicit):
* ``t`` is the projection month; ``pols_if`` is in force at the *start* of month t.
* Premiums and expenses are paid at the start of the month; deaths are paid at the end;
  lapses happen at the end of the month after deaths (death decrement applied first).
* Annual rates are converted to monthly by ``1 - (1 - q) ** (1/12)``.
* Cash flows are discounted at the valuation rate: start-of-month items by
  ``v ** (t/12)``, end-of-month items by ``v ** ((t+1)/12)``.
"""

from __future__ import annotations

import numpy as np

from ..dsl import Model, floor, t, where

#: Indices into the `assumptions` table (a single assumption set, like a Prophet run number).
EXPENSE_PER_POLICY, EXPENSE_INFLATION, EXPENSE_PCT_PREMIUM, VALUATION_RATE = range(4)


def build(n_years: int = 30) -> Model:
    m = Model("term_life", n_steps=n_years * 12)
    v, mp, tb = m.v, m.mp, m.tables

    @m.var
    def dur_m():
        """Policy duration in months at time t."""
        return mp.duration_m + t

    @m.var
    def age():
        return mp.age_at_entry + floor(v.dur_m / 12)

    @m.var
    def in_term():
        """1 while the policy is within its term, else 0."""
        return v.dur_m < mp.term_m

    @m.var
    def q_month():
        return 1 - (1 - tb.mort_qx[v.age]) ** (1 / 12)

    @m.var
    def w_month():
        return 1 - (1 - tb.lapse_rate[floor(v.dur_m / 12)]) ** (1 / 12)

    @m.var(init=0.0, total=True)
    def pols_if():
        """Policies in force at the start of month t."""
        return where(t == 0, mp.policy_count,
                     v.pols_if.lag(1) - v.deaths.lag(1) - v.lapses.lag(1)) * v.in_term

    @m.var(total=True)
    def deaths():
        return v.pols_if * v.q_month

    @m.var(total=True)
    def lapses():
        return (v.pols_if - v.deaths) * v.w_month

    @m.var(total=True)
    def premiums():
        return v.pols_if * mp.annual_premium / 12

    @m.var(total=True)
    def claims():
        return v.deaths * mp.sum_assured

    @m.var(total=True)
    def expenses():
        per_policy = tb.assumptions[EXPENSE_PER_POLICY] / 12 * (1 + tb.assumptions[EXPENSE_INFLATION]) ** (t / 12)
        return v.pols_if * per_policy + v.premiums * tb.assumptions[EXPENSE_PCT_PREMIUM]

    @m.var(total=True)
    def net_cf():
        return v.premiums - v.claims - v.expenses

    @m.var
    def v_start():
        return (1 + tb.assumptions[VALUATION_RATE]) ** (-t / 12)

    @m.var
    def v_end():
        return (1 + tb.assumptions[VALUATION_RATE]) ** (-(t + 1) / 12)

    @m.var(total=True, policy_sum=True)
    def pv_net_cf():
        """Discounted net cash flow; summed over time it is the PV of future profits."""
        return (v.premiums - v.expenses) * v.v_start - v.claims * v.v_end

    return m


def default_tables() -> dict[str, np.ndarray]:
    ages = np.arange(121)
    qx = np.minimum(1.0, 0.0005 * np.exp(0.085 * (ages - 30)))  # Gompertz-style illustration
    lapse = np.array([0.10, 0.08, 0.07, 0.06, 0.05] + [0.04] * 45)
    assumptions = np.array([60.0, 0.025, 0.03, 0.04])
    return {"mort_qx": qx, "lapse_rate": lapse, "assumptions": assumptions}


def synthetic_portfolio(n: int, seed: int = 0) -> dict[str, np.ndarray]:
    """Random in-force term portfolio (one model point per policy)."""
    rng = np.random.default_rng(seed)
    term_m = rng.choice([120, 180, 240, 300], size=n).astype(float)
    duration_m = np.floor(rng.uniform(0, 1, size=n) * term_m)
    age_at_entry = rng.integers(20, 61, size=n).astype(float)
    sum_assured = np.round(rng.lognormal(np.log(250_000), 0.6, size=n), -3)
    # Level premium rate per unit SA: the illustrative qx at the mid-term age plus a 50% loading.
    mid_age = age_at_entry + term_m / 24
    rate = 1.5 * np.minimum(1.0, 0.0005 * np.exp(0.085 * (mid_age - 30)))
    return {
        "policy_count": np.ones(n),
        "age_at_entry": age_at_entry,
        "term_m": term_m,
        "duration_m": duration_m,
        "sum_assured": sum_assured,
        "annual_premium": np.round(sum_assured * rate, 2),
    }
