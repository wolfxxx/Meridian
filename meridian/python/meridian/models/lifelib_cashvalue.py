"""lifelib CashValue_ME (savings library), re-implemented in Meridian.

A universal-life / unit-linked style savings product with an account value (AV):
* single or level premiums, a premium loading, 5% commission;
* monthly maintenance fee (1% p.a. of AV) and cost of insurance (110% of mortality on the
  net amount at risk);
* death benefit max(sum assured, AV); surrender value AV less a surrender charge by
  duration; maturity at the policy term (or age 115 for whole life);
* stochastic monthly fund returns: lognormal with mu = 2%, sigma = 3%, driven by lifelib's
  table of standard normal draws (10 scenarios);
* new business and in-force business (duration and AV at the valuation date).

Mapping from lifelib: ``pols_if_at(t, timing)`` and ``av_pp_at(t, timing)`` become one
variable per timing (``pols_if_bef_mat``, ``av_pp_bef_fee``, ...). lifelib's two references to
``t+1`` (next month's in-force and AV, in ``inv_income`` and ``av_change``) are algebraically
equal to quantities known at ``t`` (``pols_if_next``, ``av_pp_next``), so no look-ahead is
needed. Product parameters (lifelib's ``product_spec_table``) are category tables keyed by
``spec_id`` — Prophet's parameter tables.

Unlike lifelib, which runs one scenario per call (``scen_id``), Meridian runs all scenarios
in one pass (lanes = scenarios x policies).
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from ..dsl import Model, exp, floor, maximum, minimum, t, where
from ..runner import Results, run
from ..tables import Table

DATA_DIR = Path(__file__).resolve().parent / "data" / "lifelib_cashvalue"

# Fund return model (lifelib inv_return_table): exp((mu - sigma^2/2) dt + sigma sqrt(dt) Z) - 1
MU, SIGMA, DT = 0.02, 0.03, 1 / 12
DRIFT = (MU - 0.5 * SIGMA ** 2) * DT
VOL = SIGMA * DT ** 0.5

EXPENSE_ACQ, EXPENSE_MAINT, INFLATION_RATE = 5000.0, 500.0, 0.01
MAINT_FEE_RATE = 0.01 / 12
COI_LOADING = 1.1
COMMISSION_RATE = 0.05
SELECT_PERIOD = 5


def build(n_steps: int, last_age: int = 115, surr_charge_max_dur: int = 10) -> Model:
    m = Model("lifelib_cashvalue", n_steps=n_steps)
    v, mp, tb, scen = m.v, m.mp, m.tables, m.scen

    # ---- time, product and policy attributes ------------------------------------------------
    @m.var
    def duration_mth():
        return mp.duration_mth + t

    @m.var
    def duration():
        return floor(v.duration_mth / 12)

    @m.var
    def age():
        return mp.age_at_entry + v.duration

    @m.var
    def is_wl():
        return tb.is_wl[mp.spec_id]

    @m.var
    def policy_term():
        """Years; whole life runs to the mortality table's last age."""
        return where(v.is_wl, last_age - mp.age_at_entry, mp.policy_term)

    # ---- decrements ------------------------------------------------------------------------------
    @m.var
    def mort_rate():
        return tb.mort_table[v.age, minimum(v.duration, SELECT_PERIOD)]

    @m.var
    def mort_rate_mth():
        return 1 - (1 - v.mort_rate) ** (1 / 12)

    @m.var
    def lapse_rate():
        return maximum(0.1 - 0.02 * v.duration, 0.02)

    @m.var(total=True)
    def pols_new_biz():
        return where(v.duration_mth == 0, mp.policy_count, 0.0)

    @m.var(total=True)
    def pols_if_bef_mat():
        """lifelib pols_if_at(t, "BEF_MAT") = pols_if(t)."""
        return where(t == 0,
                     where(mp.duration_mth > 0, mp.policy_count, 0.0),
                     v.pols_if_next.lag(1))

    @m.var(total=True)
    def pols_maturity():
        return where(v.duration_mth == v.policy_term * 12, v.pols_if_bef_mat, 0.0)

    @m.var
    def pols_if_bef_nb():
        return v.pols_if_bef_mat - v.pols_maturity

    @m.var(total=True)
    def pols_if_bef_decr():
        return v.pols_if_bef_nb + v.pols_new_biz

    @m.var(total=True)
    def pols_death():
        return v.pols_if_bef_decr * v.mort_rate_mth

    @m.var(total=True)
    def pols_lapse():
        return (v.pols_if_bef_decr - v.pols_death) * (1 - (1 - v.lapse_rate) ** (1 / 12))

    @m.var
    def pols_if_next():
        """lifelib pols_if_at(t+1, "BEF_MAT"), known at t."""
        return v.pols_if_bef_decr - v.pols_lapse - v.pols_death

    # ---- premiums and account value per policy ----------------------------------------------------
    @m.var
    def premium_pp():
        single = where((tb.single_premium[mp.spec_id] == 1) & (v.duration_mth == 0), mp.premium_pp, 0.0)
        level = where((tb.single_premium[mp.spec_id] == 0) & (v.duration_mth < 12 * v.policy_term),
                      mp.premium_pp, 0.0)
        return single + level

    @m.var
    def prem_to_av_pp():
        return (1 - tb.load_prem_rate[mp.spec_id]) * v.premium_pp

    @m.var
    def av_pp_bef_prem():
        return where(t == 0, mp.av_pp_init, v.av_pp_next.lag(1))

    @m.var
    def av_pp_bef_fee():
        return v.av_pp_bef_prem + v.prem_to_av_pp

    @m.var
    def maint_fee_pp():
        return MAINT_FEE_RATE * v.av_pp_bef_fee

    @m.var
    def net_amt_at_risk():
        return maximum(mp.sum_assured - v.av_pp_bef_fee, 0.0)

    @m.var
    def coi_pp():
        return COI_LOADING * v.mort_rate_mth * v.net_amt_at_risk

    @m.var
    def av_pp_bef_inv():
        return v.av_pp_bef_fee - v.maint_fee_pp - v.coi_pp

    @m.var
    def inv_return_mth():
        """Stochastic monthly fund return for the lane's scenario."""
        return exp(DRIFT + VOL * scen.std_norm_rand) - 1

    @m.var
    def inv_income_pp():
        return v.inv_return_mth * v.av_pp_bef_inv

    @m.var
    def av_pp_mid_mth():
        return v.av_pp_bef_inv + 0.5 * v.inv_income_pp

    @m.var
    def av_pp_next():
        """lifelib av_pp_at(t+1, "BEF_PREM"), known at t."""
        return v.av_pp_bef_inv + v.inv_income_pp

    # ---- cash flows ------------------------------------------------------------------------------
    @m.var(total=True)
    def premiums():
        return v.premium_pp * v.pols_if_bef_decr

    @m.var(total=True)
    def inv_income():
        return (v.inv_income_pp * v.pols_if_next
                + 0.5 * v.inv_income_pp * (v.pols_death + v.pols_lapse))

    @m.var(total=True)
    def claims_death():
        return maximum(mp.sum_assured, v.av_pp_mid_mth) * v.pols_death

    @m.var
    def surr_charge():
        rate = where(tb.has_surr_charge[mp.spec_id] == 1,
                     tb.surr_charge[mp.spec_id, minimum(v.duration, surr_charge_max_dur)], 0.0)
        return rate * v.av_pp_mid_mth * v.pols_lapse

    @m.var(total=True)
    def claims_lapse():
        return v.av_pp_mid_mth * v.pols_lapse - v.surr_charge

    @m.var(total=True)
    def claims_maturity():
        return v.av_pp_bef_prem * v.pols_maturity

    @m.var(total=True)
    def claims():
        return v.claims_death + v.claims_lapse + v.claims_maturity

    @m.var(total=True)
    def commissions():
        return COMMISSION_RATE * v.premiums

    @m.var(total=True)
    def expenses():
        return (EXPENSE_ACQ * v.pols_new_biz
                + v.pols_if_bef_decr * EXPENSE_MAINT / 12 * (1 + INFLATION_RATE) ** (t / 12))

    @m.var(total=True)
    def av_change():
        """Change in total AV: av_at(t+1, BEF_MAT) - av_at(t, BEF_MAT)."""
        return v.av_pp_next * v.pols_if_next - v.av_pp_bef_prem * v.pols_if_bef_mat

    @m.var(total=True)
    def net_cf():
        return (v.premiums + v.inv_income - v.claims - v.expenses - v.commissions
                - v.av_change)

    @m.var(total=True)
    def pols_if():
        return v.pols_if_bef_mat

    # ---- discounting and present values ------------------------------------------------------
    @m.var
    def disc_factor():
        return (1 + ((1 + tb.disc_rate_ann[floor(t / 12)]) ** (1 / 12) - 1)) ** (-t)

    for name, flow in [("pv_premiums", "premiums"), ("pv_claims_death", "claims_death"),
                       ("pv_claims_lapse", "claims_lapse"), ("pv_claims_maturity", "claims_maturity"),
                       ("pv_expenses", "expenses"), ("pv_commissions", "commissions"),
                       ("pv_inv_income", "inv_income"), ("pv_av_change", "av_change"),
                       ("pv_net_cf", "net_cf"), ("pv_pols_if", "pols_if_bef_decr")]:
        def pv(flow=flow):
            return getattr(v, flow) * v.disc_factor
        pv.__name__ = name
        pv.__doc__ = f"Discounted {flow}; summed over time it is the present value per policy."
        m.var(pv, policy_sum=True)

    return m


# ---- data ---------------------------------------------------------------------------------------

def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


TEXT_COLUMNS = ("spec_id", "sex")


def load_model_points(name: str = "model_point_10000.csv") -> dict[str, np.ndarray]:
    rows = _read_csv(DATA_DIR / name)
    out = {}
    for k in rows[0]:
        vals = [r[k] for r in rows]
        out[k] = np.array(vals) if k in TEXT_COLUMNS else np.array(vals, dtype=float)
    return out


def load_tables() -> dict[str, Table]:
    spec = _read_csv(DATA_DIR / "product_spec_table.csv")
    ids = [r["spec_id"] for r in spec]
    truth = {"True": 1.0, "False": 0.0}
    surr = _read_csv(DATA_DIR / "surr_charge_table.csv")
    durations = [int(r["duration"]) for r in surr]
    assert durations == list(range(len(durations)))
    # Surrender charge by product and duration (zero for products without a charge type).
    surr_by_spec = np.array([
        [float(r[s["surr_charge_id"]]) if s["surr_charge_id"] else 0.0 for r in surr] for s in spec
    ])

    mort = list(csv.reader(open(DATA_DIR / "mort_table.csv", newline="", encoding="utf-8")))
    ages = [int(r[0]) for r in mort[1:]]
    q = np.array([[float(x) for x in r[1:]] for r in mort[1:]])
    disc = _read_csv(DATA_DIR / "disc_rate_ann.csv")

    return {
        "is_wl": Table([truth[s["is_wl"]] for s in spec], dims=[ids]),
        "single_premium": Table([1.0 if s["premium_type"] == "SINGLE" else 0.0 for s in spec], dims=[ids]),
        "load_prem_rate": Table([float(s["load_prem_rate"]) for s in spec], dims=[ids]),
        "has_surr_charge": Table([truth[s["has_surr_charge"]] for s in spec], dims=[ids]),
        "surr_charge": Table(surr_by_spec, dims=[ids, 0]),
        # Ages outside the table (only reached after maturity, where no policies remain)
        # give q = 0, as lifelib's reindex(..., fill_value=0).
        "mort_table": Table(q, dims=[ages[0], 0], fill=0.0),
        "disc_rate_ann": Table([float(r["zero_spot"]) for r in disc], dims=[0]),
    }


def mort_table_last_age(tables: dict[str, Table]) -> int:
    """First age at which every select/ultimate rate is 1 (lifelib mort_table_last_age)."""
    mt = tables["mort_table"]
    start = int(mt.dims[0][1])
    for i, row in enumerate(mt.values):
        if np.all(row == 1.0):
            return start + i
    return start + len(mt.values) - 1


def load_scenarios(n_steps: int, scenarios: list[int] | None = None) -> dict[str, np.ndarray]:
    rows = _read_csv(DATA_DIR / "std_norm_rand.csv")
    ids = sorted({int(r["scen_id"]) for r in rows})
    n_t = max(int(r["t"]) for r in rows) + 1
    z = np.zeros((len(ids), n_t))
    for r in rows:
        z[ids.index(int(r["scen_id"])), int(r["t"])] = float(r["std_norm_rand"])
    pick = [ids.index(s) for s in (scenarios or ids)]
    return {"std_norm_rand": z[pick, :n_steps]}


def projection_length(mp: dict, tables: dict, last_age: int) -> int:
    """lifelib max_proj_len: max over policies of 12 * term - duration_mth + 1."""
    wl = {lab: tables["is_wl"].values[i] for i, lab in enumerate(tables["is_wl"].dims[0][1])}
    is_wl = np.array([wl[s] for s in mp["spec_id"]])
    term = np.where(is_wl == 1, last_age - mp["age_at_entry"], mp["policy_term"])
    return int(np.max(np.maximum(12 * term - mp["duration_mth"] + 1, 0)))


def run_cashvalue(model_points: dict | None = None, *, scenarios: list[int] | None = None,
                  engine: str = "rust", tables: dict | None = None,
                  generated_scenarios: int | None = None, seed: int = 1, customize=None, **kw) -> Results:
    """Run CashValue_ME. ``tables`` overrides the default assumption tables (what-if runs);
    ``generated_scenarios`` replaces lifelib's 10 scenarios with that many fresh draws."""
    mp = model_points if model_points is not None else load_model_points()
    tables = {**load_tables(), **(tables or {})}
    last_age = mort_table_last_age(tables)
    n_steps = projection_length(mp, tables, last_age)
    model = build(n_steps, last_age=last_age, surr_charge_max_dur=tables["surr_charge"].values.shape[1] - 1)
    if customize is not None:  # e.g. formulas edited in the app
        model = customize(model)
    if generated_scenarios:
        z = np.random.default_rng(seed).standard_normal((generated_scenarios, n_steps))
        scen = {"std_norm_rand": z}
    else:
        scen = load_scenarios(n_steps, scenarios)
    return run(model, mp, tables, scen, engine=engine, **kw)
