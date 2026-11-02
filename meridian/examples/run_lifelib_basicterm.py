"""Showcase: lifelib's BasicTerm model re-built in Meridian, reconciled and scaled up.

    python examples/run_lifelib_basicterm.py            # 10,000 lifelib policies, then 1m
    python examples/run_lifelib_basicterm.py --scale 0  # skip the scale-up run
"""

import argparse
import csv
import json
from pathlib import Path

import numpy as np

import meridian as mr
from meridian.models import lifelib_basicterm as bt

REF = Path(mr.__file__).resolve().parent / "validation_data" / "lifelib_basicterm"


def read_ref(name):
    with open(REF / name, newline="") as f:
        rows = list(csv.DictReader(f))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=int, default=100,
                    help="replicate the 10,000 policies this many times for the speed run (0 = skip)")
    a = ap.parse_args()

    meta = json.loads((REF / "meta.json").read_text())
    mp, tables = bt.load_model_points(), bt.load_tables()
    print(f"lifelib {meta['lifelib_version']} BasicTerm: {len(mp['policy_term']):,} policies, "
          f"{meta['n_steps']} monthly steps\n")

    # Warm-up, then the timed two-pass run (pricing pass + projection pass).
    bt.run_basicterm({k: v[:10] for k, v in mp.items()}, tables)
    res = bt.run_basicterm(mp, tables)
    ref = read_ref("lifelib_M_per_policy.csv")

    # 1. Reconciliation
    print("1. Reconciliation with lifelib, policy by policy")
    exact = int(np.sum(res.premium_pp == ref["premium_pp"]))
    print(f"   premium per policy        {exact:,} / {len(ref['premium_pp']):,} identical to the cent")
    for k in ["pv_premiums", "pv_claims", "pv_expenses", "pv_commissions", "pv_net_cf"]:
        ours = res.projection.policy_sums[k][0]
        worst = float(np.max(np.abs(ours - ref[k]) / np.maximum(1.0, np.abs(ref[k]))))
        print(f"   {k:<25} worst relative difference {worst:.1e}")
    ours_total = res.projection.policy_sums["pv_net_cf"].sum()
    print(f"   portfolio PV of net cash flow: Meridian {ours_total:,.6f} | "
          f"lifelib {meta['portfolio_pv_net_cf']:,.6f}\n")

    # 2. lifelib-style result_pv
    print("2. Present values (portfolio), as lifelib's result_pv()")
    pvs = {name: res.projection.policy_sums[k].sum() for name, k in
           [("Premiums", "pv_premiums"), ("Claims", "pv_claims"), ("Expenses", "pv_expenses"),
            ("Commissions", "pv_commissions"), ("Net Cashflow", "pv_net_cf")]}
    for name, val in pvs.items():
        print(f"   {name:<13} {val:>18,.2f}   {val / pvs['Premiums']:>7.1%} of premium")
    print()

    # 3. Speed
    print("3. Speed (both passes: pricing + projection)")
    print(f"   lifelib BasicTerm_M (NumPy, vectorised), 10,000 policies: {meta['basicterm_m_seconds_all_policies']:.3f}s "
          "(from the reference run)")
    print(f"   Meridian, 10,000 policies:                               {res.seconds:.3f}s")
    if a.scale:
        big = {k: np.tile(v, a.scale) for k, v in mp.items()}
        n = len(big["policy_term"])
        big_res = bt.run_basicterm(big, tables)
        months = n * meta["n_steps"] * 2
        print(f"   Meridian, {n:,} policies:                          {big_res.seconds:.2f}s "
              f"({months / big_res.seconds / 1e6:.0f}m policy-months/s)")
        same = np.allclose(big_res.projection.policy_sums["pv_net_cf"][0][:len(mp['policy_term'])],
                           res.projection.policy_sums["pv_net_cf"][0], rtol=0, atol=0)
        print(f"   (first 10,000 of the scaled run identical to the base run: {same})")
    print()

    # 4. Explain one number
    print("4. Explain one number: policy 1, month 84 (attained age 54, duration 7 -> ultimate)")
    m = bt.build(int(np.max(mp["policy_term"])))
    one = {k: v[:1] for k, v in mp.items()}
    one["premium_pp"] = res.premium_pp[:1]
    tr = mr.trace(m, one, tables)
    print(tr.table(["duration", "age", "mort_rate", "pols_if", "pols_death", "claims", "net_cf"],
                   steps=[0, 12, 60, 84, 119, 120]))
    print()
    print(tr.explain("mort_rate", 84))
    print(tr.explain("pols_death", 84))


if __name__ == "__main__":
    main()
