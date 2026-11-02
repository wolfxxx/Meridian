"""With-profits (C2) demo: company-level bonus feedback over stochastic scenarios.

    python examples/run_with_profits.py --policies 20000 --scenarios 200 --years 20
"""

import argparse

import numpy as np

import meridian as mr
from meridian.models import with_profits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policies", type=int, default=20_000)
    ap.add_argument("--scenarios", type=int, default=200)
    ap.add_argument("--years", type=int, default=20)
    args = ap.parse_args()

    model = with_profits.build(n_years=args.years)
    tables = with_profits.default_tables()
    info = mr.inspect(model)
    c2 = [k for k, c in info["classes"].items() if c == "C2"]
    print(f"C2 (aggregate-feedback) variables: {', '.join(c2)}\n")

    # Reconcile on a small case first.
    mp_s = with_profits.synthetic_portfolio(500)
    sc_s = with_profits.scenarios(20, model.n_steps)
    rust = mr.run(model, mp_s, tables, sc_s)
    ref = mr.run(model, mp_s, tables, sc_s, engine="numpy")
    worst = max(
        float(np.max(np.abs(rust.totals[k] - ref.totals[k]) / np.maximum(np.abs(ref.totals[k]), 1.0)))
        for k in rust.totals
    )
    print(f"reconciliation (500 policies x 20 scenarios): worst relative diff {worst:.2e}; "
          f"NumPy {ref.seconds:.2f}s vs Rust {rust.seconds:.3f}s\n")

    mp = with_profits.synthetic_portfolio(args.policies)
    sc = with_profits.scenarios(args.scenarios, model.n_steps)
    res = mr.run(model, mp, tables, sc)
    lanes = args.policies * args.scenarios
    print(f"Rust run: {args.policies:,} policies x {args.scenarios} scenarios x {model.n_steps} months "
          f"({lanes * model.n_steps / 1e6:.0f}m lane-months) in {res.seconds:.2f}s")

    pv = res.policy_sums["pv_guarantee_cost"].sum(axis=1)  # per scenario
    order = np.sort(pv)
    cte70 = order[int(0.7 * len(order)):].mean()
    print(f"  PV cost of guarantees: mean {pv.mean():,.0f} | 95th pct {np.percentile(pv, 95):,.0f} "
          f"| CTE70 {cte70:,.0f}")


if __name__ == "__main__":
    main()
