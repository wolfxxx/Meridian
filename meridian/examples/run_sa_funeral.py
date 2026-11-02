"""Showcase: South African family funeral cover on a SAM-style basis.

    python examples/run_sa_funeral.py --policies 20000

All assumptions are illustrative (see meridian/models/sa_funeral.py).
"""

import argparse
import time

import numpy as np

import meridian as mr
from meridian.models import sa_funeral as f

from meridian.models import sa_funeral_check as ind  # noqa: E402


def rand(x):
    return f"R {x:,.0f}".replace(",", " ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policies", type=int, default=20_000)
    a = ap.parse_args()

    start = time.perf_counter()
    rows = f.synthetic_lives(a.policies)
    mp = f.model_points(rows)
    n_lives = len(rows["policy_id"])
    print(f"Portfolio: {a.policies:,} family funeral policies, {n_lives:,} lives "
          f"({n_lives / a.policies:.2f} per policy), built in {time.perf_counter() - start:.1f}s")
    roles, counts = np.unique(rows["role"], return_counts=True)
    print("  lives by role: " + ", ".join(f"{r} {c:,}" for r, c in zip(roles, counts)))
    print()

    r = f.value(mp)
    base = r.base
    print(f"1. SAM valuation: {r.runs} runs x {len(mp['policy_id']):,} lanes x {base.n_steps} months "
          f"in {r.seconds:.2f}s")
    pv_p = base.policy_sums["pv_premiums"].sum()
    pv_c = base.policy_sums["pv_claims"].sum()
    print(f"   PV premiums {rand(pv_p)} | PV claims {rand(pv_c)} ({pv_c / pv_p:.0%} of premiums)")
    print(f"   BEL (base)            {rand(r.bel['base']):>16}   ({r.bel['base'] / a.policies:,.0f} per policy)")
    for k, label in f.STRESS_LABELS.items():
        print(f"   BEL {label:<44} {rand(r.bel[k]):>16}   change {rand(r.bel[k] - r.bel['base'])}")
    print()
    print("2. Life underwriting SCR (standard-formula style aggregation)")
    for k in f.LIFE_RISKS:
        print(f"   {k:<12} {rand(r.scr[k]):>14}")
    undiversified = sum(r.scr[k] for k in f.LIFE_RISKS)
    print(f"   SCR life     {rand(r.scr['life']):>14}   (diversification {1 - r.scr['life'] / undiversified:.0%})")
    print(f"   Risk margin  {rand(r.risk_margin):>14}   (6% cost of capital, SCR projected with policies in force)")
    print(f"   Technical provisions = BEL + RM = {rand(r.technical_provisions)}")
    print()

    print("3. Independent check: plain-Python loop implementation, 25 policies x 7 bases")
    sub_ids = list(dict.fromkeys(rows["policy_id"]))[:25]
    sub = {k: v[np.isin(rows["policy_id"], sub_ids)] for k, v in rows.items()}
    sub_mp = f.model_points(sub)
    worst = 0.0
    for basis in f.BASES:
        res = mr.run(f.build(), sub_mp, f.tables(basis))
        ours = res.policy_sums["bel"][0].reshape(-1, f.LIVES).sum(axis=1)
        ref = np.array([ind.check_policy(sub, pid, basis) for pid in sub_ids])
        worst = max(worst, float((np.abs(ours - ref) / np.maximum(1, np.abs(ref))).max()))
    print(f"   worst relative difference in BEL per policy: {worst:.1e}")
    print()

    print("4. Explain one number: a family policy, spouse's expected claim in month 30")
    fam = next(pid for pid in dict.fromkeys(rows["policy_id"])
               if {"spouse", "child", "extended"} <= set(rows["role"][rows["policy_id"] == pid]))
    p = list(dict.fromkeys(rows["policy_id"])).index(fam)
    members = [(rows["role"][i], rows["sex"][i], int(rows["age"][i]), int(rows["cover"][i]))
               for i in np.where(rows["policy_id"] == fam)[0]]
    print(f"   {fam}: " + "; ".join(f"{r_} {s} {g} (cover R{c:,})" for r_, s, g, c in members))
    model = f.build()
    spouse_slot = [m[0] for m in members].index("spouse")
    tr = mr.trace(model, mp, f.tables(), policy=p, life=spouse_slot)
    print(tr.table(["age", "q_month", "main_q_month", "policy_if", "life_if", "deaths", "claims"],
                   steps=[0, 12, 24, 30, 36]))
    print()
    print(tr.explain("claims", 30))
    print(tr.explain("policy_if", 30))


if __name__ == "__main__":
    main()
