"""Showcase: lifelib's stochastic CashValue_ME savings model in Meridian, reconciled.

    python examples/run_lifelib_cashvalue.py
    python examples/run_lifelib_cashvalue.py --extra-scenarios 200   # also a 200-scenario run
"""

import argparse
import json
from pathlib import Path

import numpy as np

import meridian as mr
from meridian.models import lifelib_cashvalue as cv

REF = Path(mr.__file__).resolve().parent / "validation_data" / "lifelib_cashvalue"
GROSS = ["pv_premiums", "pv_inv_income", "pv_claims_death", "pv_claims_lapse",
         "pv_claims_maturity", "pv_expenses", "pv_commissions", "pv_av_change"]


def reconcile(label, mpfile, ref_file, scenarios):
    ref = np.load(REF / ref_file)
    meta = json.loads((REF / "meta.json").read_text())[label]
    mp = cv.load_model_points(mpfile)
    cv.run_cashvalue({k: v[:5] for k, v in mp.items()}, scenarios=scenarios)  # warm-up
    res = cv.run_cashvalue(mp, scenarios=scenarios)
    n_pol, n_scen = res.n_policies, res.n_scenarios
    print(f"  {label}: {n_pol:,} policies x {n_scen} scenarios x {res.n_steps:,} months "
          f"= {n_pol * n_scen * res.n_steps / 1e6:,.0f}m policy-scenario-months")
    worst_gross = max(float((np.abs(res.policy_sums[k] - ref[k]) / np.maximum(1, np.abs(ref[k]))).max())
                      for k in GROSS)
    gross = sum(np.abs(ref[k]) for k in GROSS)
    worst_net = float((np.abs(res.policy_sums["pv_net_cf"] - ref["pv_net_cf"]) / np.maximum(gross, 1)).max())
    print(f"    worst relative difference, gross PV items (8 items x every policy x scenario): {worst_gross:.1e}")
    print(f"    worst PV net cash flow difference, relative to gross flows:              {worst_net:.1e}")
    ours = res.policy_sums["pv_net_cf"].sum(axis=1)
    print("    portfolio PV of net cash flow by scenario (Meridian | lifelib):")
    for s in range(min(n_scen, 3)):
        print(f"      scenario {s + 1}: {ours[s]:>22,.4f} | {meta['pv_net_cf_by_scenario'][s]:>22,.4f}")
    print(f"    time: Meridian {res.seconds:.2f}s for all {n_scen} scenarios | lifelib "
          f"{sum(meta['lifelib_seconds_per_scenario']):.0f}s ({np.mean(meta['lifelib_seconds_per_scenario']):.1f}s per scenario)")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extra-scenarios", type=int, default=0,
                    help="also run this many generated scenarios (not reconcilable; shows capacity)")
    a = ap.parse_args()

    print("1. Reconciliation with lifelib CashValue_ME (stochastic, per policy and scenario)")
    port = reconcile("portfolio", "model_point_10000.csv", "portfolio.npz", None)
    reconcile("inforce", "model_point_inforce_1000.csv", "inforce.npz", [1, 2, 3])
    print()

    print("2. Stochastic results across lifelib's 10 scenarios (new-business portfolio)")
    pv = port.policy_sums["pv_net_cf"].sum(axis=1)
    order = np.sort(pv)
    print(f"   PV net cash flow: mean {pv.mean():,.0f} | min {pv.min():,.0f} | max {pv.max():,.0f} "
          f"| CTE70 of the 3 worst {order[:3].mean():,.0f}")
    by_spec = {}
    spec = cv.load_model_points()["spec_id"]
    for s_id, desc in [("A", "single premium endowment"), ("B", "single premium + surrender charge"),
                       ("C", "level premium whole life"), ("D", "level premium WL + surrender charge")]:
        sel = spec == s_id
        by_spec[s_id] = port.policy_sums["pv_net_cf"][:, sel].sum(axis=1).mean()
        print(f"   product {s_id} ({desc:<34}) mean PV net cash flow {by_spec[s_id]:>16,.0f}")
    print()

    if a.extra_scenarios:
        n = a.extra_scenarios
        mp = cv.load_model_points()
        tables = cv.load_tables()
        last_age = cv.mort_table_last_age(tables)
        steps = cv.projection_length(mp, tables, last_age)
        model = cv.build(steps, last_age=last_age)
        z = np.random.default_rng(1).standard_normal((n, steps))
        res = mr.run(model, mp, tables, {"std_norm_rand": z})
        pvn = res.policy_sums["pv_net_cf"].sum(axis=1)
        tail = np.sort(pvn)[: int(np.ceil(0.3 * n))].mean()
        print(f"3. Capacity: {n} generated scenarios x 10,000 policies x {steps:,} months "
              f"({n * 10_000 * steps / 1e9:.1f}bn) in {res.seconds:.1f}s")
        print(f"   PV net cash flow: mean {pvn.mean():,.0f} | 5th pct {np.percentile(pvn, 5):,.0f} | "
              f"CTE70 (worst 30%) {tail:,.0f}")
        print()

    print("4. Explain one number: in-force policy 6 (whole life, duration 629 months), month 1")
    mp = cv.load_model_points("model_point_inforce_1000.csv")
    one = {k: v[5:6] for k, v in mp.items()}
    tables = cv.load_tables()
    last_age = cv.mort_table_last_age(tables)
    steps = cv.projection_length(one, tables, last_age)
    model = cv.build(steps, last_age=last_age)
    tr = mr.trace(model, one, tables, cv.load_scenarios(steps, [1]))
    print(tr.table(["duration_mth", "age", "av_pp_bef_prem", "coi_pp", "inv_return_mth",
                    "av_pp_next", "pols_if_bef_decr", "claims_lapse", "net_cf"], steps=range(0, 4)))
    print()
    print(tr.explain("av_pp_bef_inv", 1))
    print(tr.explain("coi_pp", 1))


if __name__ == "__main__":
    main()
