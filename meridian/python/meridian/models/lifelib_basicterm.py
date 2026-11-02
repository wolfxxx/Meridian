"""lifelib BasicTerm_S / BasicTerm_M, re-implemented in Meridian.

A monthly projection of new-business level term assurance, with select-and-ultimate
mortality (attained age x duration, select period 5 years), duration-based lapses, expenses
with inflation, first-year commission and a premium set at 150% of the net premium.

Each Meridian variable below corresponds one-to-one to a lifelib formula of the same name
(lifelib ``basiclife`` 0.17.2, ``BasicTerm_S/Projection``). The results are reconciled
policy by policy against lifelib's own output in ``tests/test_lifelib_basicterm.py``.

The premium needs the present values of the whole projection
(``premium_pp = round(1.5 * pv_claims / pv_pols_if, 2)``), so the model runs twice — first to
set the premium basis, then to project with that premium. A Prophet user would recognise
this as a chained run.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..dsl import Model, floor, maximum, minimum, t, where
from ..runner import Results, run
from ..tables import Table

DATA_DIR = Path(__file__).resolve().parent / "data" / "lifelib_basicterm"

# Scalar assumptions, as in lifelib.
EXPENSE_ACQ = 300.0      # expense_acq()
EXPENSE_MAINT = 60.0     # expense_maint(), per annum
INFLATION_RATE = 0.01    # inflation_rate()
LOADING_PREM = 0.5       # loading_prem()
SELECT_PERIOD = 5        # mort_table columns "0".."5"


def build(max_policy_term: int = 20) -> Model:
    """Projection model. ``t`` runs 0 .. 12 * max_policy_term (inclusive), as lifelib's proj_len."""
    m = Model("lifelib_basicterm", n_steps=12 * max_policy_term + 1)
    v, mp, tb = m.v, m.mp, m.tables

    @m.var
    def duration():
        """Policy duration in whole years (new business: t // 12)."""
        return floor(t / 12)

    @m.var
    def age():
        return mp.age_at_entry + v.duration

    @m.var
    def mort_rate():
        """Annual select & ultimate rate: mort_table[min(5, duration)][age]."""
        return tb.mort_table[v.age, minimum(v.duration, SELECT_PERIOD)]

    @m.var
    def mort_rate_mth():
        return 1 - (1 - v.mort_rate) ** (1 / 12)

    @m.var
    def lapse_rate():
        return maximum(0.1 - 0.02 * v.duration, 0.02)

    @m.var
    def pols_maturity():
        """Policies maturing at t (all survivors, at t = 12 * policy_term)."""
        return where(t == mp.policy_term * 12,
                     v.pols_if.lag(1) - v.pols_lapse.lag(1) - v.pols_death.lag(1), 0.0)

    @m.var(total=True)
    def pols_if():
        """Policies in force at time t (1 at t = 0, per model point)."""
        return where(t == 0, 1.0,
                     where(t > mp.policy_term * 12, 0.0,
                           v.pols_if.lag(1) - v.pols_lapse.lag(1) - v.pols_death.lag(1)
                           - v.pols_maturity))

    @m.var(total=True)
    def pols_death():
        return v.pols_if * v.mort_rate_mth

    @m.var(total=True)
    def pols_lapse():
        return (v.pols_if - v.pols_death) * (1 - (1 - v.lapse_rate) ** (1 / 12))

    @m.var(total=True)
    def claims():
        return mp.sum_assured * v.pols_death

    @m.var(total=True)
    def premiums():
        return mp.premium_pp * v.pols_if

    @m.var(total=True)
    def commissions():
        return where(v.duration == 0, v.premiums, 0.0)

    @m.var
    def inflation_factor():
        return (1 + INFLATION_RATE) ** (t / 12)

    @m.var(total=True)
    def expenses():
        return (where(t == 0, EXPENSE_ACQ, 0.0)
                + v.pols_if * EXPENSE_MAINT / 12 * v.inflation_factor)

    @m.var(total=True)
    def net_cf():
        return v.premiums - v.claims - v.expenses - v.commissions

    @m.var
    def disc_rate_mth():
        """Monthly rate from the annual spot rate of the projection year."""
        return (1 + tb.disc_rate_ann[floor(t / 12)]) ** (1 / 12) - 1

    @m.var
    def disc_factor():
        """lifelib's disc_factors()[t] = (1 + disc_rate_mth[t]) ** (-t)."""
        return (1 + v.disc_rate_mth) ** (-t)

    # Present values: discounted flows summed over the projection, per policy.
    @m.var(policy_sum=True)
    def pv_pols_if():
        return v.pols_if * v.disc_factor

    @m.var(policy_sum=True)
    def pv_claims():
        return v.claims * v.disc_factor

    @m.var(policy_sum=True)
    def pv_premiums():
        return v.premiums * v.disc_factor

    @m.var(policy_sum=True)
    def pv_expenses():
        return v.expenses * v.disc_factor

    @m.var(policy_sum=True)
    def pv_commissions():
        return v.commissions * v.disc_factor

    @m.var(policy_sum=True)
    def pv_net_cf():
        return v.net_cf * v.disc_factor

    return m


# ---- data -----------------------------------------------------------------------------------

def load_model_points(path: Path | None = None) -> dict[str, np.ndarray]:
    path = path or DATA_DIR / "model_point_table.csv"
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cols = {k: [r[k] for r in rows] for k in rows[0]}
    out = {k: np.array(v, dtype=float) for k, v in cols.items() if k != "sex"}
    out["sex"] = np.array(cols["sex"])  # text column: encoded as a category
    return out


def load_tables(data_dir: Path | None = None) -> dict[str, Table]:
    d = data_dir or DATA_DIR
    with open(d / "mort_table.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header, body = rows[0], rows[1:]
    ages = [int(r[0]) for r in body]
    durations = [int(h) for h in header[1:]]
    assert ages == list(range(ages[0], ages[0] + len(ages))), "ages must be consecutive"
    assert durations == list(range(len(durations))), "durations must be 0..n"
    q = np.array([[float(x) for x in r[1:]] for r in body])
    with open(d / "disc_rate_ann.csv", newline="", encoding="utf-8") as f:
        drows = list(csv.reader(f))[1:]
    years = [int(r[0]) for r in drows]
    assert years == list(range(len(years))), "discount years must be 0..n"
    rates = np.array([float(r[1]) for r in drows])
    return {
        "mort_table": Table(q, dims=[ages[0], 0]),   # attained age x duration (select 5y)
        "disc_rate_ann": Table(rates, dims=[0]),     # by projection year
    }


# ---- the two-pass run ------------------------------------------------------------------------

@dataclass
class BasicTermResult:
    premium_pp: np.ndarray       # per policy
    net_premium_pp: np.ndarray   # per policy
    projection: Results          # second (pricing-basis) pass
    pricing: Results             # first pass, used to set the premium
    seconds: float


def run_basicterm(model_points: dict | None = None, tables: dict | None = None, *,
                  model: Model | None = None, engine: str = "rust") -> BasicTermResult:
    """Price (pass 1) then project (pass 2), as lifelib's premium_pp -> projection."""
    mp = dict(model_points if model_points is not None else load_model_points())
    tb = tables if tables is not None else load_tables()
    m = model or build(int(np.max(mp["policy_term"])))

    # Pass 1: present values of claims and in-force (premium not needed: set to 0).
    mp["premium_pp"] = np.zeros(len(mp["policy_term"]))
    pricing = run(m, mp, tb, engine=engine)
    net = pricing.policy_sums["pv_claims"][0] / pricing.policy_sums["pv_pols_if"][0]
    premium_pp = np.around((1 + LOADING_PREM) * net, 2)  # lifelib BasicTerm_M: np.around(.., 2)

    # Pass 2: projection with the premium.
    mp["premium_pp"] = premium_pp
    projection = run(m, mp, tb, engine=engine)
    return BasicTermResult(premium_pp, net, projection, pricing,
                           pricing.seconds + projection.seconds)
