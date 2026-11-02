"""Term life (C1) demo: run on Rust and NumPy, reconcile, benchmark, and trace one policy.

    python examples/run_term_life.py --policies 100000 --years 30
"""

import argparse

import numpy as np

import meridian as mr
from meridian.models import term_life


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policies", type=int, default=100_000)
    ap.add_argument("--years", type=int, default=30)
    ap.add_argument("--reference-policies", type=int, default=20_000,
                    help="portfolio size for the NumPy reconciliation run")
    args = ap.parse_args()

    model = term_life.build(n_years=args.years)
    tables = term_life.default_tables()
    print(model.describe(), "\n")
    info = mr.inspect(model)
    print("evaluation order:", " -> ".join(info["order"]))
    print("dependency classes:", sorted(set(info["classes"].values())), "\n")

    # 1. Reconcile Rust against the independent NumPy implementation.
    mp_small = term_life.synthetic_portfolio(args.reference_policies)
    rust = mr.run(model, mp_small, tables)
    ref = mr.run(model, mp_small, tables, engine="numpy")
    worst = max(
        float(np.max(np.abs(rust.totals[k] - ref.totals[k]) / np.maximum(np.abs(ref.totals[k]), 1.0)))
        for k in rust.totals
    )
    print(f"reconciliation on {args.reference_policies:,} policies: worst relative diff {worst:.2e}")
    print(f"  NumPy reference {ref.seconds:.2f}s | Rust {rust.seconds:.3f}s "
          f"| speed-up x{ref.seconds / rust.seconds:.1f}\n")

    # 2. Full-size run.
    mp = term_life.synthetic_portfolio(args.policies)
    res = mr.run(model, mp, tables)
    cells = args.policies * model.n_steps
    print(f"Rust run: {args.policies:,} policies x {model.n_steps} months = {cells / 1e6:.0f}m "
          f"policy-months in {res.seconds:.2f}s ({cells / res.seconds / 1e6:.0f}m policy-months/s)")
    pvfp = res.policy_sums["pv_net_cf"].sum()
    print(f"  PV of future profits: {pvfp:,.0f}")
    print(f"  year-1 premiums {res.totals['premiums'][0, :12].sum():,.0f}, "
          f"claims {res.totals['claims'][0, :12].sum():,.0f}\n")

    # 3. Single-policy trace and explanation (spec DX-3).
    tr = mr.trace(model, mp, tables, policy=0)
    print(tr.table(["dur_m", "age", "pols_if", "q_month", "deaths", "premiums", "claims", "net_cf"],
                   steps=range(0, 6)))
    print()
    print(tr.explain("deaths", 3))


if __name__ == "__main__":
    main()
